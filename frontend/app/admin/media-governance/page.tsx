"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import RoleGuard from "@/components/auth/role-guard";
import { toast } from "sonner";
import { Search, ShieldCheck, Loader2, Play } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  fetchGovernanceColleges,
  dispatchMediaIngestion,
  dispatchBulkMediaIngestion,
  fetchMediaIngestionStatus,
  triageMediaCandidate,
  GovernanceCollege,
  GovernanceMediaType,
  GovernanceTriageAction,
  TriageTarget 
} from "@/lib/media-governance-api";

import { GovernanceTable } from "./components/governance-table";
import { TriageModal } from "./components/triage-modal";

export default function MediaGovernancePage() {
  const [data, setData] = useState<GovernanceCollege[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [skip, setSkip] = useState(0);
  const [limit] = useState(50);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  type FilterState = "ALL" | "PENDING" | "ACCEPTED" | "EXHAUSTED" | "GRAVEYARD" | "EMPTY";
  const [activeFilter, setActiveFilter] = useState<FilterState>("ALL");

  const [isLoading, setIsLoading] = useState(true);
  const [isMutating, setIsMutating] = useState(false);
  const [triageTarget, setTriageTarget] = useState<TriageTarget | null>(null);

  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isGlobalIngesting, setIsGlobalIngesting] = useState(false);
  const [activeTasks, setActiveTasks] = useState(0);
  const prevIngestingState = useRef(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setSkip(0); 
      setSelectedIds([]); 
    }, 500);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const loadData = useCallback(async (currentSkip: number) => {
    try {
      setIsLoading(true);
      const res = await fetchGovernanceColleges(currentSkip, limit, debouncedSearch);

      if (res.data.length === 0 && currentSkip > 0 && res.total_count > 0) {
        const safeSkip = Math.max(0, currentSkip - limit);
        setSkip(safeSkip);
        const fallbackRes = await fetchGovernanceColleges(safeSkip, limit, debouncedSearch);
        setData(fallbackRes.data);
        setTotalCount(fallbackRes.total_count);
      } else {
        setData(res.data);
        setTotalCount(res.total_count);
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to load governance payload.");
    } finally {
      setIsLoading(false);
    }
  }, [limit, debouncedSearch]);

  useEffect(() => {
    loadData(skip);
  }, [skip, loadData]);

  useEffect(() => {
    let timeoutId: NodeJS.Timeout;

    const checkStatus = async () => {
      try {
        const status = await fetchMediaIngestionStatus();
        setIsGlobalIngesting(status.is_ingesting);
        setActiveTasks(status.active_tasks);

        if (prevIngestingState.current === true && status.is_ingesting === false) {
          toast.success("Background ingestion batch completed!");
          loadData(skip); 
        }
        prevIngestingState.current = status.is_ingesting;

        const nextDelay = status.is_ingesting ? 3000 : 15000;
        timeoutId = setTimeout(checkStatus, nextDelay);
      } catch (e) {
        timeoutId = setTimeout(checkStatus, 15000); 
      }
    };

    checkStatus();
    return () => clearTimeout(timeoutId);
  }, [skip, loadData]);

  const handleSelectRow = (id: string) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  const handleSelectAll = () => {
    if (selectedIds.length === displayData.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(displayData.map(c => c.college_id));
    }
  };

  const handleBulkDispatch = async (force: boolean) => {
    if (selectedIds.length === 0) return;
    try {
      setIsMutating(true);
      const summary = await dispatchBulkMediaIngestion(selectedIds, force);
      
      toast.success(
        <div className="flex flex-col gap-1">
          <span className="font-bold">Bulk Dispatch Initiated</span>
          <span className="text-xs">Queued: {summary.queued}</span>
          <span className="text-xs">Skipped (Locked): {summary.skipped_locked}</span>
          <span className="text-xs">Skipped (Exhausted): {summary.skipped_exhausted}</span>
        </div>
      );
      
      setSelectedIds([]); 
      await loadData(skip); 
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to dispatch bulk payload.");
    } finally {
      setIsMutating(false);
    }
  };

  const handleDispatch = async (collegeId: string, mediaType: GovernanceMediaType, force: boolean = false) => {
    try {
      setIsMutating(true);
      await dispatchMediaIngestion(collegeId, mediaType, force);
      toast.success(`Ingestion Dispatched: ${mediaType}`);
      await loadData(skip); 
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to acquire dispatch lock.");
    } finally {
      setIsMutating(false);
    }
  };

  const handleTriageAction = async (action: GovernanceTriageAction) => {
    if (!triageTarget) return;

    try {
      setIsMutating(true);
      await triageMediaCandidate(triageTarget.collegeId, triageTarget.mediaId, action);
      toast.success(`Media transition successful: ${action}`);
      setTriageTarget(null); 
      await loadData(skip); 
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Transaction failed. Database may be locked.");
    } finally {
      setIsMutating(false);
    }
  };

  const displayData = useMemo(() => {
    if (activeFilter === "ALL") return data;
    return data.filter(college => college.derived_state === activeFilter);
  }, [data, activeFilter]);

  const filters: { label: string; value: FilterState }[] = [
    { label: "All Entities", value: "ALL" },
    { label: "Pending Triage", value: "PENDING" },
    { label: "Accepted", value: "ACCEPTED" },
    { label: "Exhausted", value: "EXHAUSTED" },
    { label: "Graveyard", value: "GRAVEYARD" },
    { label: "Awaiting Ingestion", value: "EMPTY" },
  ];

  return (
    <RoleGuard requiredRole="EDITOR">
      <div className="p-8 max-w-[1600px] mx-auto space-y-6">
        
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <ShieldCheck className="w-6 h-6 text-indigo-600" />
              <h1 className="text-3xl font-bold tracking-tight text-slate-900">Media Governance</h1>
            </div>
            <p className="text-slate-500 font-medium">Control plane for media ingestion, exhaustion resets, and lifecycle triage.</p>
          </div>

          {isGlobalIngesting && (
            <div className="flex items-center gap-3 bg-white px-4 py-2 rounded-lg border border-indigo-100 shadow-sm animate-in fade-in zoom-in duration-300">
              <Loader2 className="w-5 h-5 text-indigo-600 animate-spin" />
              <div>
                <p className="text-sm font-bold text-indigo-900">Background Ingestion Active</p>
                <p className="text-xs font-medium text-indigo-600/80">{activeTasks} tasks currently computing</p>
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 bg-white p-2 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-1.5 overflow-x-auto pb-2 xl:pb-0 px-2 scrollbar-hide">
            {filters.map((filter) => (
              <button
                key={filter.value}
                onClick={() => {
                  setActiveFilter(filter.value);
                  setSelectedIds([]); 
                }}
                disabled={isMutating}
                className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all whitespace-nowrap ${
                  activeFilter === filter.value 
                    ? "bg-slate-900 text-white shadow-md ring-2 ring-slate-900/10 ring-offset-1" 
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 hover:text-slate-900"
                } disabled:opacity-50`}
              >
                {filter.label}
              </button>
            ))}
          </div>

          <div className="relative w-full xl:w-80 px-2 xl:px-0">
            <Search className="absolute left-4 xl:left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input 
              placeholder="Search registry index..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              disabled={isMutating}
              className="pl-10 h-10 border-slate-200 bg-slate-50 focus-visible:ring-indigo-500 rounded-lg"
            />
          </div>
        </div>

        {selectedIds.length > 0 && (
          <div className="bg-indigo-50 border border-indigo-200 p-3 rounded-xl flex items-center justify-between shadow-sm animate-in slide-in-from-top-2 fade-in">
            <div className="flex items-center gap-3 pl-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-600 text-white text-xs font-bold shadow-sm">
                {selectedIds.length}
              </span>
              <span className="text-indigo-900 font-semibold text-sm">Entities Selected</span>
            </div>
            <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setSelectedIds([])} className="bg-white hover:bg-indigo-100 border-indigo-200 text-indigo-700">
                  Cancel
                </Button>
                <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm" disabled={isMutating} onClick={() => handleBulkDispatch(false)}>
                    <Play className="w-4 h-4 mr-2" /> Bulk Ingest All
                </Button>
            </div>
          </div>
        )}

        <GovernanceTable
          data={displayData}
          isLoading={isLoading}
          isMutating={isMutating}
          skip={skip}
          limit={limit}
          totalCount={totalCount}
          selectedIds={selectedIds}
          onSelect={handleSelectRow}
          onSelectAll={handleSelectAll}
          onNext={() => { setSkip((s) => (s + limit < totalCount ? s + limit : s)); setSelectedIds([]); }}
          onPrev={() => { setSkip((s) => Math.max(0, s - limit)); setSelectedIds([]); }}
          onDispatch={handleDispatch}
          onOpenTriage={setTriageTarget}
        />

        {activeFilter !== "ALL" && (
          <div className="text-center text-xs text-slate-500 font-medium pb-4">
            Showing {displayData.length} items matching "{filters.find(f => f.value === activeFilter)?.label}" on the current page. <br/>
            <span className="text-slate-400">(Navigate pages to find more matching candidates)</span>
          </div>
        )}

        <TriageModal
          isOpen={!!triageTarget}
          onClose={() => !isMutating && setTriageTarget(null)}
          target={triageTarget}
          isMutating={isMutating}
          onAction={handleTriageAction}
        />
      </div>
    </RoleGuard>
  );
}