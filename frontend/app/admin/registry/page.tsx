"use client";

import { useEffect, useState } from "react";
import { fetchRegistry, RegistryCollege, updateCanonicalName } from "@/lib/admin-api";
import { Building2, ChevronRight, ChevronDown, ArrowUpCircle, CornerDownRight, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

export default function RegistryPage() {
  const [colleges, setColleges] = useState<RegistryCollege[]>([]);
  const [filtered, setFiltered] = useState<RegistryCollege[]>([]);
  const [search, setSearch] = useState("");
  
  // State for expanded rows
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  // --- NEW: MODAL STATE ---
  const [promoteTarget, setPromoteTarget] = useState<{
    id: string;
    currentName: string;
    aliasToPromote: string;
  } | null>(null);

  const loadData = async () => {
    try {
      const data = await fetchRegistry();
      setColleges(data);
      setFiltered(data);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { loadData(); }, []);

  // Filter Logic
  useEffect(() => {
    const term = search.toLowerCase();
    setFiltered(colleges.filter(c => 
      c.canonical_name.toLowerCase().includes(term) || 
      c.aliases.some(a => a.toLowerCase().includes(term))
    ));
  }, [search, colleges]);

  const toggleRow = (id: string) => {
    const next = new Set(expanded);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setExpanded(next);
  };

  // Step 1: User clicks button -> Open Modal
  const requestPromotion = (college: RegistryCollege, alias: string) => {
    setPromoteTarget({
      id: college.college_id,
      currentName: college.canonical_name,
      aliasToPromote: alias
    });
  };

  // Step 2: User confirms in Modal -> Execute API
  const executePromotion = async () => {
    if (!promoteTarget) return;

    try {
      await updateCanonicalName(promoteTarget.id, promoteTarget.aliasToPromote);
      setPromoteTarget(null); // Close Modal
      loadData(); // Refresh Tree
    } catch (e) { 
      alert("Promotion Failed"); // Fallback for API errors
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex justify-between items-center pb-4 border-b">
        <div>
          <h1 className="text-3xl font-bold">Master Registry</h1>
          <p className="text-gray-500">Hierarchy of Official Names and their known Aliases.</p>
        </div>
        <div className="w-72">
          <Input 
            placeholder="Search colleges or aliases..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-12 gap-4 px-6 py-3 bg-gray-50 border-b text-sm font-semibold text-gray-500">
          <div className="col-span-8">Entity Name</div>
          <div className="col-span-2">State</div>
          <div className="col-span-2 text-right">Aliases</div>
        </div>

        {/* Tree Rows */}
        <div className="divide-y divide-gray-100">
          {filtered.slice(0, 100).map(c => {
            const isOpen = expanded.has(c.college_id);
            const hasAliases = c.aliases.length > 0;

            return (
              <div key={c.college_id} className="group">
                {/* PARENT ROW */}
                <div 
                  className={`grid grid-cols-12 gap-4 px-6 py-4 items-center cursor-pointer transition-colors
                    ${isOpen ? 'bg-indigo-50/50' : 'hover:bg-gray-50'}`}
                  onClick={() => hasAliases && toggleRow(c.college_id)}
                >
                  <div className="col-span-8 flex items-center gap-3">
                    <button 
                      className={`p-1 rounded hover:bg-gray-200 text-gray-400 ${!hasAliases && 'invisible'}`}
                      onClick={(e) => { e.stopPropagation(); toggleRow(c.college_id); }}
                    >
                      {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    </button>
                    
                    <div className="p-2 bg-white border rounded-md text-indigo-600 shadow-sm">
                      <Building2 className="w-5 h-5" />
                    </div>
                    
                    <div>
                      <div className="font-semibold text-gray-900">{c.canonical_name}</div>
                      <div className="text-xs text-gray-400 font-mono">{c.college_id.slice(0, 8)}...</div>
                    </div>
                  </div>

                  <div className="col-span-2 text-sm text-gray-500">
                    <Badge variant="outline">{c.state_code}</Badge>
                  </div>

                  <div className="col-span-2 text-right text-sm text-gray-400">
                    {c.aliases.length} known
                  </div>
                </div>

                {/* CHILDREN ROWS (Aliases) */}
                {isOpen && (
                  <div className="bg-gray-50/50 border-t border-gray-100">
                    {c.aliases.map((alias, idx) => (
                      <div key={idx} className="grid grid-cols-12 gap-4 px-6 py-3 items-center hover:bg-white transition-colors border-b border-gray-50 last:border-0">
                        <div className="col-span-8 flex items-center gap-3 pl-12">
                          <CornerDownRight className="w-4 h-4 text-gray-300" />
                          <span className="text-sm text-gray-600 font-medium">{alias}</span>
                        </div>
                        
                        <div className="col-span-4 text-right">
                          <Button 
                            size="sm" variant="ghost" 
                            className="text-xs text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50 h-7"
                            onClick={() => requestPromotion(c, alias)}
                          >
                            <ArrowUpCircle className="w-3 h-3 mr-1.5" />
                            Make Canonical
                          </Button>
                        </div>
                      </div>
                    ))}
                    {c.aliases.length === 0 && (
                      <div className="px-6 py-3 pl-14 text-sm text-gray-400 italic">No aliases recorded.</div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* --- CONFIRMATION DIALOG --- */}
      <Dialog open={!!promoteTarget} onOpenChange={(open) => !open && setPromoteTarget(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-amber-600">
              <AlertTriangle className="w-5 h-5" /> Confirm Name Change
            </DialogTitle>
            
            {/* FIX: Add 'asChild' and wrap content in a single <div> */}
            <DialogDescription className="pt-2 space-y-2" asChild>
              <div className="text-sm text-muted-foreground">
                <p>
                  You are about to promote <strong>&quot;{promoteTarget?.aliasToPromote}&quot;</strong> to be the Official Canonical Name.
                </p>
                <div className="bg-gray-50 p-3 rounded-md text-sm border">
                  <div className="flex justify-between mb-1">
                    <span className="text-gray-500">New Official Name:</span>
                    <span className="font-semibold text-green-700">{promoteTarget?.aliasToPromote}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Becomes Alias:</span>
                    <span className="font-medium text-gray-700">{promoteTarget?.currentName}</span>
                  </div>
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  This change will be reflected across all reports and dashboards immediately.
                </p>
              </div>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" onClick={() => setPromoteTarget(null)}>
              Cancel
            </Button>
            <Button onClick={executePromotion}>
              Confirm Promotion
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}