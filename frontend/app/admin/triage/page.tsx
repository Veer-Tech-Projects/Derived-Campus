"use client";

import { useEffect, useState, useMemo } from "react";
import { Candidate, fetchCandidates, fetchRegistry, RegistryCollege, linkCandidate, promoteNewCollege } from "@/lib/admin-api";
import { Link as LinkIcon, PlusCircle, AlertCircle, Layers, Search, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { useAuth } from "@/components/providers/auth-provider"; 

interface CandidateGroup {
  raw_name: string;
  reason_flagged: string;
  ids: number[];
  sources: string[];
}

export default function TriagePage() {
  const { hasRole } = useAuth(); 
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [registry, setRegistry] = useState<RegistryCollege[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  
  const [mainSearch, setMainSearch] = useState("");
  const [registrySearch, setRegistrySearch] = useState("");
  
  const [isLinkOpen, setIsLinkOpen] = useState(false);
  const [isPromoteOpen, setIsPromoteOpen] = useState(false);
  const [successModal, setSuccessModal] = useState<{ title: string; message: string } | null>(null);

  const [targetCollegeId, setTargetCollegeId] = useState("");
  const [newCollegeName, setNewCollegeName] = useState("");

  const canEdit = hasRole("EDITOR");

  const loadData = async () => {
    try {
      const [cData, rData] = await Promise.all([fetchCandidates(), fetchRegistry()]);
      setCandidates(cData);
      setRegistry(rData);
      setSelectedIds([]); 
    } catch (e) {
      console.error("Failed to load triage data", e);
    }
  };

  useEffect(() => { loadData(); }, []);

  const groupedCandidates = useMemo(() => {
    const groups: Record<string, CandidateGroup> = {};
    const searchLower = mainSearch.toLowerCase();

    candidates.forEach(c => {
      if (mainSearch && !c.raw_name.toLowerCase().includes(searchLower)) return;

      if (!groups[c.raw_name]) {
        groups[c.raw_name] = {
          raw_name: c.raw_name,
          reason_flagged: c.reason_flagged,
          ids: [],
          sources: []
        };
      }
      groups[c.raw_name].ids.push(c.candidate_id);
      if (!groups[c.raw_name].sources.includes(c.source_document)) {
        groups[c.raw_name].sources.push(c.source_document);
      }
    });

    return Object.values(groups);
  }, [candidates, mainSearch]);

  const filteredRegistry = useMemo(() => {
    if (!registrySearch) return registry;
    return registry.filter(r => r.canonical_name.toLowerCase().includes(registrySearch.toLowerCase()));
  }, [registry, registrySearch]);

  const toggleGroup = (group: CandidateGroup) => {
    const allSelected = group.ids.every(id => selectedIds.includes(id));
    if (allSelected) {
      setSelectedIds(prev => prev.filter(id => !group.ids.includes(id)));
    } else {
      const newIds = [...selectedIds];
      group.ids.forEach(id => {
        if (!newIds.includes(id)) newIds.push(id);
      });
      setSelectedIds(newIds);
    }
  };

  const handleLink = async () => {
    try {
      // [FIX] Removed admin@localhost
      await linkCandidate(selectedIds, targetCollegeId);
      setIsLinkOpen(false);
      setSuccessModal({
        title: "Link Successful",
        message: `Successfully resolved ${selectedIds.length} candidates by linking them to an existing registry entry.`
      });
      loadData();
    } catch (e) { alert("Link Failed"); }
  };

  const handlePromote = async () => {
    try {
      // [FIX] Removed admin@localhost
      await promoteNewCollege(selectedIds, newCollegeName);
      setIsPromoteOpen(false);
      setSuccessModal({
        title: "Promotion Successful",
        message: `Created new college "${newCollegeName}" and linked ${selectedIds.length} candidates.`
      });
      loadData();
    } catch (e) { alert("Promotion Failed"); }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 bg-slate-50/50 min-h-screen">
      <div className="flex justify-between items-center pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Identity Triage</h1>
          <p className="text-slate-500 mt-1">Resolve unknown college names found in PDFs.</p>
        </div>
        <div className="flex gap-2">
          <div className="relative w-64 mr-2">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-400" />
            <Input 
              placeholder="Search candidates..." 
              className="pl-8 bg-white"
              value={mainSearch}
              onChange={(e) => setMainSearch(e.target.value)}
            />
          </div>

          {canEdit && (
            <>
              <Button 
                variant="outline" 
                className="bg-white hover:bg-slate-50"
                disabled={selectedIds.length === 0}
                onClick={() => { setRegistrySearch(""); setIsLinkOpen(true); }}
              >
                <LinkIcon className="w-4 h-4 mr-2" /> Link Selected ({selectedIds.length})
              </Button>
              <Button 
                disabled={selectedIds.length === 0}
                className="bg-slate-900 hover:bg-slate-800 text-white"
                onClick={() => {
                  if (selectedIds.length > 0) setNewCollegeName(groupedCandidates.find(g => g.ids.includes(selectedIds[0]))?.raw_name || "");
                  setIsPromoteOpen(true);
                }}
              >
                <PlusCircle className="w-4 h-4 mr-2" /> Promote New
              </Button>
            </>
          )}
        </div>
      </div>

      <div className="bg-white border rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-sm text-left">
          <thead className="bg-slate-50 border-b text-slate-500">
            <tr>
              <th className="px-4 py-3 w-12 text-center"></th>
              <th className="px-4 py-3 font-semibold">Unknown College Name</th>
              <th className="px-4 py-3 font-semibold text-center">Count</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Sources</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {groupedCandidates.map(group => {
              const isSelected = group.ids.every(id => selectedIds.includes(id));
              const isPartiallySelected = !isSelected && group.ids.some(id => selectedIds.includes(id));

              return (
                <tr key={group.raw_name} className={`transition-colors ${isSelected ? 'bg-indigo-50/40' : 'hover:bg-slate-50'}`}>
                  <td className="px-4 py-3 text-center">
                    <input 
                      type="checkbox" 
                      checked={isSelected}
                      disabled={!canEdit} 
                      ref={input => { if (input) input.indeterminate = isPartiallySelected; }}
                      onChange={() => toggleGroup(group)}
                      className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer disabled:cursor-not-allowed"
                    />
                  </td>
                  <td className="px-4 py-3 font-medium text-slate-900">
                    {group.raw_name}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Badge variant="secondary" className="font-mono bg-slate-100">{group.ids.length}</Badge>
                  </td>
                  <td className="px-4 py-3 flex items-center gap-2 font-medium text-amber-600">
                    <AlertCircle className="w-4 h-4" /> {group.reason_flagged}
                  </td>
                  <td className="px-4 py-3 text-slate-400 font-mono text-xs">
                    {group.sources.length === 1 ? (
                      <span className="flex items-center gap-1"><Layers className="w-3 h-3"/> 1 PDF</span>
                    ) : (
                      <span className="flex items-center gap-1 text-indigo-600 font-bold"><Layers className="w-3 h-3"/> {group.sources.length} PDFs</span>
                    )}
                  </td>
                </tr>
              );
            })}
            {groupedCandidates.length === 0 && (
              <tr><td colSpan={5} className="p-12 text-center text-slate-400 italic">No candidates found matching your criteria.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <Dialog open={isLinkOpen} onOpenChange={setIsLinkOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Link to Existing College</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-slate-500">
              Select the official college that matches these <strong>{selectedIds.length} occurrences</strong>.
            </p>
            <Input 
              placeholder="Filter list..." 
              value={registrySearch} 
              onChange={(e) => setRegistrySearch(e.target.value)} 
              className="mb-2"
            />
            <select 
              className="w-full p-2 border rounded-md text-sm bg-slate-50 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              onChange={(e) => setTargetCollegeId(e.target.value)}
              size={5}
            >
              {filteredRegistry.map(r => (
                <option key={r.college_id} value={r.college_id} className="p-2 cursor-pointer hover:bg-indigo-50">{r.canonical_name}</option>
              ))}
              {filteredRegistry.length === 0 && <option disabled>No matches found</option>}
            </select>
          </div>
          <DialogFooter>
            <Button onClick={handleLink} disabled={!targetCollegeId}>Confirm Link</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isPromoteOpen} onOpenChange={setIsPromoteOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Promote to New Registry Entry</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-slate-500">
              Create a brand new Master Registry entry for these <strong>{selectedIds.length} candidates</strong>.
            </p>
            <Input 
              placeholder="Official College Name (Canonical)"
              value={newCollegeName}
              onChange={(e) => setNewCollegeName(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button onClick={handlePromote} disabled={!newCollegeName}>Create & Link</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!successModal} onOpenChange={(open) => !open && setSuccessModal(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-emerald-600">
              <CheckCircle2 className="w-5 h-5" /> {successModal?.title}
            </DialogTitle>
            <DialogDescription className="pt-2">
              {successModal?.message}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button onClick={() => setSuccessModal(null)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}