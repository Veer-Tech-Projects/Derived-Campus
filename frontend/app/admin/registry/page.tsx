"use client";

import React, { useEffect, useState, useMemo, useCallback } from "react";
import { 
  fetchRegistry, RegistryCollege, updateCanonicalName,
  fetchBranchRegistry, fetchCourseTypeRegistry, TaxonomyRegistryItem,
  promoteBranchAlias, promoteCourseTypeAlias,
  fetchExamConfigs, ExamConfig
} from "@/lib/admin-api";
import { Building2, ChevronRight, ChevronDown, ArrowUpCircle, CornerDownRight, Network, BookOpen, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { useAuth } from "@/components/providers/auth-provider"; 
import { toast } from "sonner";

type RegistryTab = "COLLEGES" | "BRANCHES" | "COURSES";

interface UnifiedRegistryItem {
  id: string;
  primary_name: string;
  subtitle: string; 
  aliases: string[];
}

export default function MasterRegistryPage() {
  const { hasRole } = useAuth(); 
  const canEdit = hasRole("EDITOR");

  const [activeTab, setActiveTab] = useState<RegistryTab>("COLLEGES");
  
  const [exams, setExams] = useState<ExamConfig[]>([]);
  const [examCode, setExamCode] = useState<string>("");

  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const [colleges, setColleges] = useState<RegistryCollege[]>([]);
  const [taxonomyData, setTaxonomyData] = useState<TaxonomyRegistryItem[]>([]);

  const [promoteTarget, setPromoteTarget] = useState<{
    id: string;
    currentName: string;
    aliasToPromote: string;
  } | null>(null);

  useEffect(() => {
    const initExams = async () => {
      try {
        const examData = await fetchExamConfigs();
        setExams(examData);
        if (examData.length > 0) {
          setExamCode(examData[0].exam_code);
        }
      } catch (e) {
        toast.error("Failed to load exam configurations");
      }
    };
    initExams();
  }, []);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      if (activeTab === "COLLEGES") {
        const data = await fetchRegistry();
        setColleges(data);
      } else if (activeTab === "BRANCHES" && examCode) {
        const data = await fetchBranchRegistry(examCode);
        setTaxonomyData(data);
      } else if (activeTab === "COURSES" && examCode) {
        const data = await fetchCourseTypeRegistry(examCode);
        setTaxonomyData(data);
      }
    } catch (e) { 
      toast.error("Failed to load registry data.");
    } finally {
      setIsLoading(false);
    }
  }, [activeTab, examCode]);

  useEffect(() => {
    loadData();
    setExpanded(new Set());
    setSearch("");
  }, [loadData, activeTab, examCode]);

  const unifiedData: UnifiedRegistryItem[] = useMemo(() => {
    if (activeTab === "COLLEGES") {
      return colleges.map(c => ({
        id: c.college_id,
        primary_name: c.canonical_name,
        subtitle: c.state_code || 'Unknown',
        aliases: c.aliases || []
      }));
    } else {
      return taxonomyData.map(t => ({
        id: t.id,
        primary_name: t.name,
        subtitle: examCode.toUpperCase(),
        aliases: t.aliases || []
      }));
    }
  }, [activeTab, colleges, taxonomyData, examCode]);

  const filteredData = useMemo(() => {
    if (!search) return unifiedData;
    return unifiedData.filter(item => 
      item.primary_name.toLowerCase().includes(search.toLowerCase()) || 
      item.aliases.some(a => a.toLowerCase().includes(search.toLowerCase()))
    );
  }, [unifiedData, search]);

  const toggleExpand = (id: string) => {
    const next = new Set(expanded);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setExpanded(next);
  };

  // [NEW] Dynamic execution router based on active tab
  const executePromotion = async () => {
    if (!promoteTarget) return;
    try {
      if (activeTab === "COLLEGES") {
        await updateCanonicalName(promoteTarget.id, promoteTarget.aliasToPromote);
      } else if (activeTab === "BRANCHES") {
        await promoteBranchAlias(promoteTarget.id, promoteTarget.aliasToPromote);
      } else if (activeTab === "COURSES") {
        await promoteCourseTypeAlias(promoteTarget.id, promoteTarget.aliasToPromote);
      }
      toast.success("Alias promoted to Canonical successfully.");
      setPromoteTarget(null);
      loadData();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Promotion failed.");
    }
  };

  const getEntityIcon = (id: string) => {
    const isExpanded = expanded.has(id);
    if (activeTab === "COLLEGES") return <Building2 className="w-5 h-5 text-indigo-600" />;
    if (activeTab === "BRANCHES") return <Network className="w-5 h-5 text-indigo-600" />;
    return <BookOpen className="w-5 h-5 text-indigo-600" />;
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      
      {/* Header aligned with your screenshot */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center pb-4 border-b border-slate-200 gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Master Registry</h1>
          <p className="text-slate-500 mt-1 text-sm">Hierarchy of Official Names and their known Aliases.</p>
        </div>

        <div className="flex items-center gap-4">
          {/* Tab Switcher */}
          <div className="flex bg-slate-100 p-1 rounded-lg">
            <button 
              onClick={() => setActiveTab("COLLEGES")}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${activeTab === "COLLEGES" ? "bg-white shadow-sm text-slate-900" : "text-slate-500 hover:text-slate-700"}`}
            >
              Colleges
            </button>
            <button 
              onClick={() => setActiveTab("BRANCHES")}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${activeTab === "BRANCHES" ? "bg-white shadow-sm text-slate-900" : "text-slate-500 hover:text-slate-700"}`}
            >
              Branches
            </button>
            <button 
              onClick={() => setActiveTab("COURSES")}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${activeTab === "COURSES" ? "bg-white shadow-sm text-slate-900" : "text-slate-500 hover:text-slate-700"}`}
            >
              Courses
            </button>
          </div>

          <div className="relative w-64">
            <Input 
              placeholder="Search colleges or aliases..." 
              className="bg-white border-slate-200 text-sm"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>
      </div>

      {activeTab !== "COLLEGES" && (
        <div className="flex items-center gap-2 bg-slate-50 p-3 rounded-lg border border-slate-200 animate-in fade-in">
          <span className="text-sm font-semibold text-slate-600">Select Exam Context:</span>
          <select 
            value={examCode} 
            onChange={(e) => setExamCode(e.target.value)}
            className="p-1.5 border border-slate-300 rounded bg-white focus:ring-2 focus:ring-indigo-500 text-sm font-medium uppercase shadow-sm"
            disabled={exams.length === 0}
          >
            {exams.map(ex => (
              <option key={ex.exam_code} value={ex.exam_code}>
                {ex.exam_code.replace('_', ' ')}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Main Table perfectly matched to screenshot */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        {isLoading ? (
           <div className="p-12 flex justify-center items-center">
             <Loader2 className="w-8 h-8 text-slate-300 animate-spin" />
           </div>
        ) : (
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold text-[13px]">
              <tr>
                <th className="px-6 py-4 w-3/5">Entity Name</th>
                <th className="px-6 py-4 w-1/5">{activeTab === "COLLEGES" ? "State" : "Exam"}</th>
                <th className="px-6 py-4 w-1/5 text-right">Aliases</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredData.map(item => {
                const isExpanded = expanded.has(item.id);
                return (
                  <React.Fragment key={item.id}>
                    <tr 
                      className={`hover:bg-slate-50/50 transition-colors cursor-pointer ${isExpanded ? "bg-slate-50/50" : ""}`}
                      onClick={() => toggleExpand(item.id)}
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-4">
                          <button className="text-slate-400 hover:text-slate-600">
                            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                          </button>
                          <div className="flex items-center justify-center w-10 h-10 rounded-xl border border-slate-200 bg-white shadow-sm shrink-0">
                            {getEntityIcon(item.id)}
                          </div>
                          <div>
                            <div className="font-bold text-slate-900 text-sm">{item.primary_name}</div>
                            <div className="text-[11px] text-slate-400 font-mono mt-0.5">{item.id.substring(0, 8)}...</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-slate-500 font-medium">
                        {item.subtitle}
                      </td>
                      <td className="px-6 py-4 text-right text-slate-500 font-medium">
                        {item.aliases.length} known
                      </td>
                    </tr>
                    
                    {isExpanded && item.aliases.length > 0 && (
                      <tr className="bg-slate-50/50">
                        <td colSpan={3} className="px-0 py-0 border-t border-slate-100">
                          <div className="pl-24 pr-6 py-3 space-y-1">
                            {item.aliases.map((alias, idx) => (
                              <div key={idx} className="flex items-center justify-between py-2 group">
                                <div className="flex items-center text-sm font-medium text-slate-600">
                                  <CornerDownRight className="w-4 h-4 text-slate-300 mr-3" />
                                  {alias}
                                </div>
                                
                                {/* "Make Canonical" available for ALL tabs if user is EDITOR */}
                                {canEdit && (
                                  <Button 
                                    variant="ghost" 
                                    size="sm" 
                                    className="h-8 text-xs font-semibold text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setPromoteTarget({ id: item.id, currentName: item.primary_name, aliasToPromote: alias });
                                    }}
                                  >
                                    <ArrowUpCircle className="w-3.5 h-3.5 mr-1.5" />
                                    Make Canonical
                                  </Button>
                                )}
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
              {filteredData.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-6 py-12 text-center text-slate-500 italic">
                    No registry entities found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* Unified Promotion Modal */}
      <Dialog open={!!promoteTarget} onOpenChange={(open) => !open && setPromoteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Canonical Swap</DialogTitle>
            <DialogDescription className="pt-2 space-y-2" asChild>
              <div className="text-sm text-slate-500">
                <p>
                  You are about to promote <strong>&quot;{promoteTarget?.aliasToPromote}&quot;</strong> to be the Official Canonical Name.
                </p>
                <div className="bg-slate-50 p-3 rounded-md text-sm border border-slate-200 mt-2">
                  <div className="flex justify-between mb-1">
                    <span className="text-slate-500 font-semibold">New Official Name:</span>
                    <span className="font-bold text-indigo-700">{promoteTarget?.aliasToPromote}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500 font-semibold">Demoted to Alias:</span>
                    <span className="font-medium text-slate-700">{promoteTarget?.currentName}</span>
                  </div>
                </div>
                <p className="text-[11px] font-semibold text-amber-600 bg-amber-50 p-2 rounded mt-3">
                  This change propagates instantly across the entire platform.
                </p>
              </div>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPromoteTarget(null)}>Cancel</Button>
            <Button className="bg-indigo-600 hover:bg-indigo-700 text-white" onClick={executePromotion}>Confirm Swap</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}