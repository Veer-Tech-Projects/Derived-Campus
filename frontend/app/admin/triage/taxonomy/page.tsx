"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { 
  fetchBranchQueue, fetchBranchRegistry, promoteBranch, linkBranch, rejectBranch, 
  fetchCourseTypeQueue, fetchCourseTypeRegistry, promoteCourseType, linkCourseType, rejectCourseType,
  TaxonomyCandidate, TaxonomyRegistryItem,
  fetchExamConfigs, ExamConfig // [NEW] Added dynamic config fetcher
} from "@/lib/admin-api";
import { Link as LinkIcon, PlusCircle, Search, CheckCircle2, Ban, Network, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { useAuth } from "@/components/providers/auth-provider"; 
import { toast } from "sonner";

type TaxonomyDomain = "BRANCH" | "COURSE";

export default function TaxonomyTriagePage() {
  const { hasRole } = useAuth(); 
  const canEdit = hasRole("EDITOR");

  const [activeTab, setActiveTab] = useState<TaxonomyDomain>("BRANCH");
  
  // [FIX] Dynamic Exam State
  const [exams, setExams] = useState<ExamConfig[]>([]);
  const [examCode, setExamCode] = useState<string>(""); 
  
  const [isLoadingData, setIsLoadingData] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [candidates, setCandidates] = useState<TaxonomyCandidate[]>([]);
  const [registry, setRegistry] = useState<TaxonomyRegistryItem[]>([]);
  
  const [selectedCandidate, setSelectedCandidate] = useState<TaxonomyCandidate | null>(null);
  const [isLinkOpen, setIsLinkOpen] = useState(false);
  const [isPromoteOpen, setIsPromoteOpen] = useState(false);

  // Form State
  const [mainSearch, setMainSearch] = useState("");
  const [registrySearch, setRegistrySearch] = useState("");
  const [targetRegistryId, setTargetRegistryId] = useState("");
  const [promoName, setPromoName] = useState(""); 
  const [promoVariant, setPromoVariant] = useState(""); 

  // [NEW] Fetch exams on component mount
  useEffect(() => {
    const initExams = async () => {
      try {
        const examData = await fetchExamConfigs();
        setExams(examData);
        if (examData.length > 0) {
          // Default to the first active exam slug (e.g., 'kcet')
          setExamCode(examData[0].exam_code);
        }
      } catch (e) {
        toast.error("Failed to load exam configurations");
      }
    };
    initExams();
  }, []);

  const loadData = useCallback(async () => {
    if (!examCode) return; // Prevent fetch until exam code is loaded

    setIsLoadingData(true);
    try {
      if (activeTab === "BRANCH") {
        const [cData, rData] = await Promise.all([fetchBranchQueue(examCode), fetchBranchRegistry(examCode)]);
        setCandidates(cData);
        setRegistry(rData);
      } else {
        const [cData, rData] = await Promise.all([fetchCourseTypeQueue(examCode), fetchCourseTypeRegistry(examCode)]);
        setCandidates(cData);
        setRegistry(rData);
      }
    } catch (e) {
      toast.error(`Failed to load taxonomy data for ${examCode}`);
    } finally {
      setIsLoadingData(false);
    }
  }, [activeTab, examCode]);

  useEffect(() => {
    if (examCode) {
      setMainSearch("");
      setRegistrySearch("");
      setTargetRegistryId("");
      setSelectedCandidate(null);
      loadData();
    }
  }, [loadData, examCode]); // Triggers when dynamic examCode becomes available

  const filteredCandidates = useMemo(() => {
    if (!mainSearch) return candidates;
    return candidates.filter(c => c.raw_name.toLowerCase().includes(mainSearch.toLowerCase()));
  }, [candidates, mainSearch]);

  const filteredRegistry = useMemo(() => {
    if (!registrySearch) return registry;
    return registry.filter(r => r.name.toLowerCase().includes(registrySearch.toLowerCase()));
  }, [registry, registrySearch]);

  const closeLinkModal = () => {
    setIsLinkOpen(false);
    setTargetRegistryId("");
    setRegistrySearch("");
  };

  const closePromoteModal = () => {
    setIsPromoteOpen(false);
    setPromoName("");
    setPromoVariant("");
  };

  const handleLink = async () => {
    if (!selectedCandidate || !targetRegistryId) return;
    setIsSubmitting(true);
    try {
      if (activeTab === "BRANCH") await linkBranch(selectedCandidate.id, targetRegistryId);
      else await linkCourseType(selectedCandidate.id, targetRegistryId);
      
      toast.success(`Mapped "${selectedCandidate.raw_name}" successfully.`);
      setCandidates(prev => prev.filter(c => c.id !== selectedCandidate.id));
      closeLinkModal();
    } catch (e: any) { 
      toast.error(e.response?.data?.detail || "Link Failed"); 
      loadData(); 
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePromote = async () => {
    if (!selectedCandidate || !promoName) return;
    setIsSubmitting(true);
    try {
      if (activeTab === "BRANCH") await promoteBranch(selectedCandidate.id, promoName, promoVariant);
      else await promoteCourseType(selectedCandidate.id, promoName);
      
      toast.success(`Canonical entity created successfully.`);
      setCandidates(prev => prev.filter(c => c.id !== selectedCandidate.id));
      closePromoteModal();
      loadData(); 
    } catch (e: any) { 
      toast.error(e.response?.data?.detail || "Promotion Failed"); 
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async (candidate: TaxonomyCandidate) => {
    if (!confirm(`Permanently suppress "${candidate.raw_name}"?`)) return;
    setIsSubmitting(true);
    try {
      if (activeTab === "BRANCH") await rejectBranch(candidate.id);
      else await rejectCourseType(candidate.id);
      
      toast.success(`String suppressed.`);
      setCandidates(prev => prev.filter(c => c.id !== candidate.id));
    } catch (e: any) { 
      toast.error(e.response?.data?.detail || "Rejection Failed"); 
      loadData();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 bg-slate-50/50 min-h-screen">
      <div className="flex justify-between items-end pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-2">
            <Network className="w-8 h-8 text-indigo-600" /> Taxonomy Triage
          </h1>
          <p className="text-slate-500 mt-1">Resolve unknown program and degree names isolated by the Gatekeeper.</p>
        </div>
        
        <div className="flex gap-4 items-center">
          <div className="flex bg-slate-200/50 p-1 rounded-lg">
            <button 
              onClick={() => setActiveTab("BRANCH")}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${activeTab === "BRANCH" ? "bg-white shadow-sm text-indigo-600" : "text-slate-500 hover:text-slate-700"}`}
            >
              Branches
            </button>
            <button 
              onClick={() => setActiveTab("COURSE")}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${activeTab === "COURSE" ? "bg-white shadow-sm text-indigo-600" : "text-slate-500 hover:text-slate-700"}`}
            >
              Course Types
            </button>
          </div>

          {/* [FIX] Dynamic Database-Driven Dropdown */}
          <select 
            value={examCode} 
            onChange={(e) => setExamCode(e.target.value)}
            className="p-2 border rounded-md bg-white focus:ring-2 focus:ring-indigo-500 text-sm font-medium uppercase min-w-[120px]"
            disabled={exams.length === 0}
          >
            {exams.map(ex => (
              <option key={ex.exam_code} value={ex.exam_code}>
                {ex.exam_code.replace('_', ' ')}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex justify-between items-center">
        <div className="relative w-72">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-400" />
          <Input 
            placeholder={`Search unknown ${activeTab.toLowerCase()}s...`} 
            className="pl-8 bg-white"
            value={mainSearch}
            onChange={(e) => setMainSearch(e.target.value)}
          />
        </div>
        {isLoadingData && <span className="text-sm text-indigo-600 flex items-center font-medium"><Loader2 className="w-4 h-4 mr-2 animate-spin"/> Syncing Airlock...</span>}
      </div>

      <div className="bg-white border rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-sm text-left">
          <thead className="bg-slate-50 border-b text-slate-500">
            <tr>
              <th className="px-4 py-3 font-semibold">Raw PDF String</th>
              <th className="px-4 py-3 font-semibold text-center">Normalized Trace</th>
              <th className="px-4 py-3 font-semibold text-right">Resolution Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredCandidates.map(c => (
              <tr key={c.id} className="hover:bg-slate-50 transition-colors">
                <td className="px-4 py-4 font-medium text-slate-900 w-1/3">
                  {c.raw_name}
                </td>
                <td className="px-4 py-4 text-center w-1/3">
                  <Badge variant="secondary" className="font-mono text-[11px] bg-slate-100 text-slate-600 font-normal py-1">
                    {c.normalized_name}
                  </Badge>
                </td>
                <td className="px-4 py-4 text-right space-x-2 w-1/3">
                  {canEdit && (
                    <>
                      <Button 
                        variant="outline" size="sm" className="text-indigo-600 hover:text-indigo-700 bg-white"
                        onClick={() => { setSelectedCandidate(c); setRegistrySearch(""); setIsLinkOpen(true); }}
                        disabled={isSubmitting}
                      >
                        <LinkIcon className="w-3 h-3 mr-1" /> Link Alias
                      </Button>
                      <Button 
                        variant="default" size="sm" className="bg-slate-900 hover:bg-slate-800"
                        onClick={() => { 
                          setSelectedCandidate(c); 
                          setPromoName(c.normalized_name); 
                          setPromoVariant(""); 
                          setIsPromoteOpen(true); 
                        }}
                        disabled={isSubmitting}
                      >
                        <PlusCircle className="w-3 h-3 mr-1" /> Promote Canonical
                      </Button>
                      <Button 
                        variant="ghost" size="sm" className="text-red-400 hover:text-red-600 hover:bg-red-50 px-2"
                        onClick={() => handleReject(c)}
                        disabled={isSubmitting}
                        title="Permanent Suppression"
                      >
                        <Ban className="w-4 h-4" />
                      </Button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {filteredCandidates.length === 0 && !isLoadingData && examCode && (
              <tr>
                <td colSpan={3} className="p-16 text-center text-slate-400">
                  <div className="flex flex-col items-center justify-center gap-2">
                    <CheckCircle2 className="w-8 h-8 text-emerald-400 opacity-50" />
                    <p className="font-medium text-slate-500">The Airlock is empty.</p>
                    <p className="text-xs uppercase tracking-widest">All {activeTab.toLowerCase()} strings in {examCode.replace('_', ' ')} are recognized.</p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* LINK MODAL */}
      <Dialog open={isLinkOpen} onOpenChange={(open) => !open && closeLinkModal()}>
        <DialogContent>
          <DialogHeader><DialogTitle>Link to Existing {activeTab === "BRANCH" ? "Branch" : "Course"}</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="p-3 bg-slate-50 rounded-md border border-slate-100">
              <p className="text-xs text-slate-500 uppercase font-semibold mb-1">Target Raw String</p>
              <p className="text-sm font-medium text-slate-900 font-mono">{selectedCandidate?.raw_name}</p>
            </div>
            <Input 
              placeholder="Search registry..." value={registrySearch} onChange={(e) => setRegistrySearch(e.target.value)} 
            />
            {registry.length === 0 ? (
               <p className="text-sm text-amber-600 p-4 bg-amber-50 rounded-md text-center uppercase tracking-widest font-semibold">Registry is currently empty for {examCode.replace('_', ' ')}.</p>
            ) : (
              <select 
                className="w-full p-2 border rounded-md text-sm bg-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                onChange={(e) => setTargetRegistryId(e.target.value)} size={6}
              >
                {filteredRegistry.map(r => (
                  <option key={r.id} value={r.id} className="p-2 cursor-pointer hover:bg-indigo-50">{r.name}</option>
                ))}
                {filteredRegistry.length === 0 && <option disabled>No matches found in Registry</option>}
              </select>
            )}
          </div>
          <DialogFooter>
            <Button onClick={handleLink} disabled={!targetRegistryId || isSubmitting}>
              {isSubmitting ? "Linking..." : "Confirm Link"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* PROMOTE MODAL */}
      <Dialog open={isPromoteOpen} onOpenChange={(open) => !open && closePromoteModal()}>
        <DialogContent>
          <DialogHeader><DialogTitle>Promote to Canonical {activeTab === "BRANCH" ? "Branch" : "Course"}</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="p-3 bg-slate-50 rounded-md border border-slate-100">
              <p className="text-xs text-slate-500 uppercase font-semibold mb-1">Incoming String</p>
              <p className="text-sm font-medium text-slate-900 font-mono">{selectedCandidate?.raw_name}</p>
            </div>
            
            {activeTab === "COURSE" ? (
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Canonical Name</label>
                <Input value={promoName} onChange={(e) => setPromoName(e.target.value)} />
              </div>
            ) : (
              <>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Discipline (Required)</label>
                  <Input value={promoName} onChange={(e) => setPromoName(e.target.value)} />
                  <p className="text-[10px] text-slate-400 mt-1">e.g. "Computer Science", "Mechanical"</p>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Variant (Optional)</label>
                  <Input value={promoVariant} onChange={(e) => setPromoVariant(e.target.value)} />
                  <p className="text-[10px] text-slate-400 mt-1">e.g. "Artificial Intelligence", "Shift 2"</p>
                </div>
              </>
            )}
          </div>
          <DialogFooter>
            <Button onClick={handlePromote} disabled={!promoName || isSubmitting}>
               {isSubmitting ? "Promoting..." : "Create Canonical"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}