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
import { useAuth } from "@/components/providers/auth-provider"; // <--- Auth

export default function RegistryPage() {
  const { hasRole } = useAuth(); // <--- Auth Hook
  const [colleges, setColleges] = useState<RegistryCollege[]>([]);
  const [filtered, setFiltered] = useState<RegistryCollege[]>([]);
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const [promoteTarget, setPromoteTarget] = useState<{
    id: string;
    currentName: string;
    aliasToPromote: string;
  } | null>(null);

  const canEdit = hasRole("EDITOR");

  const loadData = async () => {
    try {
      const data = await fetchRegistry();
      setColleges(data);
      setFiltered(data);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { loadData(); }, []);

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

  const requestPromotion = (college: RegistryCollege, alias: string) => {
    setPromoteTarget({
      id: college.college_id,
      currentName: college.canonical_name,
      aliasToPromote: alias
    });
  };

  const executePromotion = async () => {
    if (!promoteTarget) return;
    try {
      await updateCanonicalName(promoteTarget.id, promoteTarget.aliasToPromote);
      setPromoteTarget(null);
      loadData();
    } catch (e) { alert("Promotion Failed"); }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 bg-slate-50/50 min-h-screen">
      <div className="flex justify-between items-center pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Master Registry</h1>
          <p className="text-slate-500 mt-1">Hierarchy of Official Names and their known Aliases.</p>
        </div>
        <div className="w-72">
          <Input 
            placeholder="Search colleges or aliases..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-white"
          />
        </div>
      </div>

      <div className="bg-white border rounded-xl shadow-sm overflow-hidden">
        <div className="grid grid-cols-12 gap-4 px-6 py-3 bg-slate-50 border-b text-sm font-semibold text-slate-500">
          <div className="col-span-8">Entity Name</div>
          <div className="col-span-2">State</div>
          <div className="col-span-2 text-right">Aliases</div>
        </div>

        <div className="divide-y divide-slate-100">
          {filtered.slice(0, 100).map(c => {
            const isOpen = expanded.has(c.college_id);
            const hasAliases = c.aliases.length > 0;

            return (
              <div key={c.college_id} className="group">
                {/* PARENT ROW */}
                <div 
                  className={`grid grid-cols-12 gap-4 px-6 py-4 items-center cursor-pointer transition-colors
                    ${isOpen ? 'bg-indigo-50/50' : 'hover:bg-slate-50'}`}
                  onClick={() => hasAliases && toggleRow(c.college_id)}
                >
                  <div className="col-span-8 flex items-center gap-3">
                    <button 
                      className={`p-1 rounded hover:bg-slate-200 text-slate-400 ${!hasAliases && 'invisible'}`}
                      onClick={(e) => { e.stopPropagation(); toggleRow(c.college_id); }}
                    >
                      {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    </button>
                    
                    <div className="p-2 bg-white border rounded-lg text-indigo-600 shadow-sm">
                      <Building2 className="w-5 h-5" />
                    </div>
                    
                    <div>
                      <div className="font-semibold text-slate-900">{c.canonical_name}</div>
                      <div className="text-xs text-slate-400 font-mono">{c.college_id.slice(0, 8)}...</div>
                    </div>
                  </div>

                  <div className="col-span-2 text-sm text-slate-500">
                    <Badge variant="outline" className="text-xs font-mono bg-white">{c.state_code}</Badge>
                  </div>

                  <div className="col-span-2 text-right text-sm text-slate-400 font-medium">
                    {c.aliases.length} known
                  </div>
                </div>

                {/* ALIASES ROWS */}
                {isOpen && (
                  <div className="bg-slate-50/50 border-t border-slate-100 shadow-inner">
                    {c.aliases.map((alias, idx) => (
                      <div key={idx} className="grid grid-cols-12 gap-4 px-6 py-3 items-center hover:bg-white transition-colors border-b border-slate-100 last:border-0">
                        <div className="col-span-8 flex items-center gap-3 pl-12">
                          <CornerDownRight className="w-4 h-4 text-slate-300" />
                          <span className="text-sm text-slate-600 font-medium">{alias}</span>
                        </div>
                        
                        <div className="col-span-4 text-right">
                          {/* RBAC CHECK */}
                          {canEdit && (
                            <Button 
                              size="sm" variant="ghost" 
                              className="text-xs text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50 h-7"
                              onClick={() => requestPromotion(c, alias)}
                            >
                              <ArrowUpCircle className="w-3 h-3 mr-1.5" />
                              Make Canonical
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                    {c.aliases.length === 0 && (
                      <div className="px-6 py-3 pl-14 text-sm text-slate-400 italic">No aliases recorded.</div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <Dialog open={!!promoteTarget} onOpenChange={(open) => !open && setPromoteTarget(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-amber-600">
              <AlertTriangle className="w-5 h-5" /> Confirm Name Change
            </DialogTitle>
            <DialogDescription className="pt-2 space-y-2" asChild>
              <div className="text-sm text-muted-foreground">
                <p>
                  You are about to promote <strong>&quot;{promoteTarget?.aliasToPromote}&quot;</strong> to be the Official Canonical Name.
                </p>
                <div className="bg-slate-50 p-3 rounded-md text-sm border border-slate-200">
                  <div className="flex justify-between mb-1">
                    <span className="text-slate-500">New Official Name:</span>
                    <span className="font-semibold text-emerald-700">{promoteTarget?.aliasToPromote}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Becomes Alias:</span>
                    <span className="font-medium text-slate-700">{promoteTarget?.currentName}</span>
                  </div>
                </div>
                <p className="text-xs text-slate-400 mt-2">
                  This change will be reflected across all reports and dashboards immediately.
                </p>
              </div>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPromoteTarget(null)}>Cancel</Button>
            <Button onClick={executePromotion}>Confirm Promotion</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}