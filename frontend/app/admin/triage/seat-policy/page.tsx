'use client';

import React, { useEffect, useState } from 'react';
import { 
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow 
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  Card, CardContent, CardHeader, CardTitle, CardFooter
} from "@/components/ui/card";
import { 
  CheckCircle, XCircle, RefreshCw, ShieldAlert, ChevronLeft, ChevronRight, Layers, Tag
} from 'lucide-react';
import { toast } from 'sonner'; 
import { fetchPendingSeatViolations, promoteSeatBucket, ignoreSeatBucket } from '@/lib/admin-api';
import { useAuth } from '@/components/providers/auth-provider'; // <--- Auth

interface ViolationGroup {
  id: string;
  seat_bucket_code: string;
  exam_code: string;
  source_year: number;
  count: number;
}

const PAGE_SIZE = 50;

export default function SeatPolicyTriagePage() {
  const { hasRole } = useAuth(); // <--- Auth Hook
  const [groups, setGroups] = useState<ViolationGroup[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const canEdit = hasRole("EDITOR");

  const loadData = async () => {
    setIsLoading(true);
    try {
      const skip = (page - 1) * PAGE_SIZE;
      const data: any = await fetchPendingSeatViolations(skip, PAGE_SIZE);
      setGroups(data);
      setHasMore(data.length === PAGE_SIZE);
    } catch (error) {
      toast.error("Could not load pending violations.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [page]);

  const handlePromote = async (id: string) => {
    setProcessingId(id);
    try {
      await promoteSeatBucket(id);
      toast.success("Bucket Type Approved", { description: "Master taxonomy updated and reprocessing triggered." });
      setGroups(prev => prev.filter(g => g.id !== id));
    } catch (error) {
      toast.error("Promotion Failed");
    } finally {
      setProcessingId(null);
    }
  };

  const handleIgnore = async (id: string) => {
    setProcessingId(id);
    try {
      await ignoreSeatBucket(id);
      toast.info("Bucket Type Ignored");
      setGroups(prev => prev.filter(g => g.id !== id));
    } catch (error) {
      toast.error("Action Failed");
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-screen">
      <div className="flex flex-col md:flex-row justify-between md:items-center gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">Seat Policy Triage</h1>
            <Badge variant="outline" className="text-amber-600 bg-amber-50 border-amber-200">Page {page}</Badge>
          </div>
          <p className="text-slate-500 mt-2 max-w-2xl">
            Unknown <strong>Seat Bucket Types</strong> detected. Approving a bucket type fixes it for all colleges and files globally.
          </p>
        </div>
        <Button onClick={loadData} variant="outline" size="sm" className="gap-2 bg-white">
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} /> Refresh
        </Button>
      </div>

      <Card className="border-slate-200 shadow-sm flex flex-col min-h-[600px]">
        <CardHeader className="border-b bg-white pb-4 rounded-t-xl">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-500" />
            <CardTitle className="text-lg text-slate-800">Unknown Bucket Types</CardTitle>
          </div>
        </CardHeader>
        
        <CardContent className="p-0 flex-grow bg-white">
          {isLoading ? (
             <div className="p-20 text-center text-slate-400 animate-pulse">Analyzing types...</div>
          ) : groups.length === 0 ? (
             <div className="p-20 text-center flex flex-col items-center gap-4">
               <div className="bg-emerald-100 p-4 rounded-full"><CheckCircle className="w-10 h-10 text-emerald-600" /></div>
               <h3 className="text-lg font-semibold text-slate-900">Taxonomy Synced</h3>
               <p className="text-slate-500">No unknown bucket types found.</p>
             </div>
          ) : (
            <div className="relative overflow-x-auto">
              <Table>
                <TableHeader className="bg-slate-50/75">
                  <TableRow>
                    <TableHead className="w-[400px]">Bucket Code (Slug)</TableHead>
                    <TableHead>Context</TableHead>
                    <TableHead>Impact</TableHead>
                    <TableHead className="text-right">Governance</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {groups.map((group) => (
                    <TableRow key={group.id} className="group hover:bg-slate-50/50">
                      <TableCell className="align-middle py-4">
                        <div className="flex items-center gap-3">
                          <Tag className="w-4 h-4 text-slate-400" />
                          <code className="text-sm font-mono bg-slate-50 px-2 py-1 rounded border border-slate-200 text-slate-700 font-bold">
                            {group.seat_bucket_code}
                          </code>
                        </div>
                      </TableCell>
                      <TableCell className="align-middle py-4">
                          <div className="flex flex-col">
                            <Badge variant="outline" className="w-fit mb-1 uppercase font-bold text-[10px] tracking-wider">{group.exam_code}</Badge>
                            <span className="text-xs text-slate-500 font-medium">Year: {group.source_year}</span>
                          </div>
                      </TableCell>
                      <TableCell className="align-middle py-4">
                        <Badge variant="secondary" className="bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-100">
                          <Layers className="w-3 h-3 mr-1.5" /> {group.count} Violations
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right align-middle py-4">
                        {canEdit && (
                          <div className="flex justify-end gap-2">
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              onClick={() => handleIgnore(group.id)} 
                              disabled={processingId === group.id} 
                              className="text-slate-500 hover:text-red-600 hover:bg-red-50"
                            >
                              <XCircle className="w-4 h-4 mr-1" /> Ignore
                            </Button>
                            <Button 
                              size="sm" 
                              onClick={() => handlePromote(group.id)} 
                              disabled={processingId === group.id} 
                              className="bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm"
                            >
                              {processingId === group.id ? <RefreshCw className="w-4 h-4 animate-spin" /> : <><CheckCircle className="w-4 h-4 mr-1" /> Approve Type</>}
                            </Button>
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
        <CardFooter className="border-t bg-slate-50/50 p-4 flex justify-between items-center rounded-b-xl">
            <div className="text-xs text-slate-500 font-medium">Showing page {page}</div>
            <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1 || isLoading} className="bg-white"><ChevronLeft className="w-4 h-4 mr-1" /> Previous</Button>
                <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={!hasMore || isLoading} className="bg-white">Next <ChevronRight className="w-4 h-4 ml-1" /></Button>
            </div>
        </CardFooter>
      </Card>
    </div>
  );
}