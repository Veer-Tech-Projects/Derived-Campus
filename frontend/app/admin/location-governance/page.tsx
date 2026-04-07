"use client";

import { useState, useEffect, useRef } from "react";
import useSWR from "swr";
import { 
  fetchLocationColleges, dispatchLocationIngestion, triageLocationCandidate, 
  dispatchBulkLocationIngestion, fetchLocationIngestionStatus,
  GovernanceLocation, LocationTriageAction 
} from "@/lib/location-governance-api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, Loader2, MapPin, RefreshCw, Layers, Filter } from "lucide-react";
import { toast } from "sonner";
import { LocationTriageModal } from "./components/location-triage-modal";

export default function LocationGovernancePage() {
  const [colleges, setColleges] = useState<GovernanceLocation[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL"); // [NEW] Status State
  const limit = 50;

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [modalCollege, setModalCollege] = useState<GovernanceLocation | null>(null);

  const fetchSequence = useRef(0);

  const { data: telemetry, error: telemetryError } = useSWR(
    "location-status", 
    fetchLocationIngestionStatus, 
    { refreshInterval: 3000 }
  );

  useEffect(() => {
    if (telemetryError) {
      toast.error("Telemetry disconnected. Live status unavailable.", { id: "telemetry-err" });
    }
  }, [telemetryError]);

  const loadColleges = async (resetPage = false) => {
    const currentSequence = ++fetchSequence.current;
    
    try {
      setIsLoading(true);
      const targetPage = resetPage ? 0 : page;
      if (resetPage) setPage(0);
      
      const res = await fetchLocationColleges(targetPage * limit, limit, search, statusFilter);
      
      if (currentSequence !== fetchSequence.current) return;
      
      setColleges(res.data);
      setTotal(res.total_count);
      setSelectedIds(new Set()); // Reset selections on new query
    } catch (e) {
      if (currentSequence !== fetchSequence.current) return;
      toast.error("Failed to load governance matrix.");
    } finally {
      if (currentSequence === fetchSequence.current) {
        setIsLoading(false);
      }
    }
  };

  // [NEW] Trigger fetch on search or status change
  useEffect(() => {
    const timer = setTimeout(() => {
      loadColleges(true);
    }, 500);
    return () => clearTimeout(timer);
  }, [search, statusFilter]);

  useEffect(() => {
    loadColleges();
  }, [page]);

  const toggleSelection = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  };

  const currentPageIds = colleges.map(c => c.college_id);
  const isAllCurrentPageSelected = currentPageIds.length > 0 && currentPageIds.every(id => selectedIds.has(id));

  const toggleSelectAll = (checked: boolean) => {
    const next = new Set(selectedIds);
    if (checked) {
      currentPageIds.forEach(id => next.add(id));
    } else {
      currentPageIds.forEach(id => next.delete(id));
    }
    setSelectedIds(next);
  };

  const handleBulkDispatch = async (force: boolean) => {
    if (selectedIds.size === 0) return;
    if (selectedIds.size > 200) {
      toast.error("Maximum 200 colleges allowed per bulk dispatch.");
      return;
    }

    try {
      const summary = await dispatchBulkLocationIngestion(Array.from(selectedIds), force);
      toast.success(`Queued: ${summary.queued}. Skipped Locked: ${summary.skipped_locked}. Skipped Exhausted: ${summary.skipped_exhausted}.`);
      setSelectedIds(new Set());
      loadColleges();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Bulk dispatch failed.");
    }
  };

  const handleTriage = async (
    collegeId: string, 
    action: LocationTriageAction, 
    candidateId?: string | null, 
    overrides?: { city?: string; district?: string; state_code?: string; pincode?: string }
  ) => {
    try {
      await triageLocationCandidate(collegeId, action, candidateId, overrides);
      toast.success(`Successfully recorded action: ${action}`);
      setModalCollege(null);
      loadColleges();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Triage execution failed.");
    }
  };

  const getStateBadge = (state: string) => {
    switch(state) {
      case "ACCEPTED": return <Badge className="bg-emerald-100 text-emerald-800 border-emerald-200 hover:bg-emerald-100">ACCEPTED</Badge>;
      case "PENDING": return <Badge className="bg-amber-100 text-amber-800 border-amber-200 hover:bg-amber-100">PENDING</Badge>;
      case "EXHAUSTED": return <Badge className="bg-rose-100 text-rose-800 border-rose-200 hover:bg-rose-100">EXHAUSTED</Badge>;
      default: return <Badge className="bg-slate-100 text-slate-500 border-slate-200 hover:bg-slate-100">EMPTY</Badge>;
    }
  };

  return (
    <div className="max-w-[1600px] mx-auto p-6 space-y-6">
      
      <div className="flex flex-col xl:flex-row justify-between items-start xl:items-center gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-teal-50 text-teal-600 rounded-lg">
            <MapPin className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">Location Governance</h1>
            <p className="text-sm text-slate-500 font-medium">Coordinate resolution and geographic integrity mapping.</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          {telemetry?.is_ingesting && (
            <div className="flex items-center gap-2 px-4 py-2 bg-indigo-50 border border-indigo-100 rounded-full text-indigo-700 text-sm font-semibold">
              <Loader2 className="w-4 h-4 animate-spin" />
              {telemetry.active_tasks} Active Workers
            </div>
          )}
          
          {/* [NEW] Status Filter Dropdown */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="pl-9 pr-8 h-10 w-40 rounded-md border border-slate-200 bg-slate-50 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-700 font-medium appearance-none cursor-pointer"
            >
              <option value="ALL">All States</option>
              <option value="PENDING">Pending Triage</option>
              <option value="EMPTY">Empty</option>
              <option value="EXHAUSTED">Exhausted</option>
              <option value="ACCEPTED">Accepted</option>
            </select>
          </div>

          <div className="relative w-72">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input 
              placeholder="Search canonical name..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 bg-slate-50 border-slate-200"
            />
          </div>
        </div>
      </div>

      {selectedIds.size > 0 && (
        <div className="flex items-center justify-between p-4 bg-indigo-900 text-white rounded-xl shadow-lg animate-in slide-in-from-bottom-2">
          <div className="flex items-center gap-3">
            <Layers className="w-5 h-5 text-indigo-300" />
            <span className="font-semibold">{selectedIds.size} Colleges Selected</span>
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={() => handleBulkDispatch(false)} className="bg-white/10 hover:bg-white/20 text-white border-none">
              <RefreshCw className="w-4 h-4 mr-2" /> Dispatch Search
            </Button>
            <Button size="sm" variant="destructive" onClick={() => handleBulkDispatch(true)} className="bg-rose-500 hover:bg-rose-600 text-white">
              Force Retry (Exhausted)
            </Button>
          </div>
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500">
              <tr>
                <th className="px-6 py-4 w-12 text-center">
                  <input 
                    type="checkbox" 
                    aria-label="Select all colleges on page"
                    onChange={(e) => toggleSelectAll(e.target.checked)}
                    checked={isAllCurrentPageSelected}
                    className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-600"
                  />
                </th>
                <th className="px-6 py-4 font-semibold uppercase tracking-wider text-xs">College Identity</th>
                <th className="px-6 py-4 font-semibold uppercase tracking-wider text-xs text-center">Derived State</th>
                <th className="px-6 py-4 font-semibold uppercase tracking-wider text-xs">Canonical Geo-Hash</th>
                <th className="px-6 py-4 font-semibold uppercase tracking-wider text-xs text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center">
                    <Loader2 className="w-6 h-6 animate-spin text-slate-400 mx-auto" />
                  </td>
                </tr>
              ) : colleges.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-500 italic">
                    No results found for current filter criteria.
                  </td>
                </tr>
              ) : (
                colleges.map((col) => (
                  <tr key={col.college_id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-6 py-4 text-center">
                      <input 
                        type="checkbox" 
                        aria-label={`Select ${col.canonical_name}`}
                        checked={selectedIds.has(col.college_id)}
                        onChange={() => toggleSelection(col.college_id)}
                        className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-600"
                      />
                    </td>
                    <td className="px-6 py-4">
                      <div className="font-bold text-slate-900">{col.canonical_name}</div>
                      <div className="text-xs text-slate-500 font-medium">Registry: {col.registry_city || "Unknown"}, {col.registry_state_code || "Unknown"}</div>
                    </td>
                    <td className="px-6 py-4 text-center">
                      {getStateBadge(col.derived_state)}
                    </td>
                    <td className="px-6 py-4 text-slate-600 text-xs font-mono max-w-xs truncate">
                      {col.canonical_address || "Awaiting Resolution"}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {col.derived_state === "PENDING" && (
                        <Button 
                          size="sm" 
                          onClick={() => setModalCollege(col)}
                          className="bg-teal-50 text-teal-700 hover:bg-teal-100 hover:text-teal-800 border-teal-200 shadow-none"
                        >
                          Review Candidate
                        </Button>
                      )}
                      {(col.derived_state === "EMPTY" || col.derived_state === "ACCEPTED") && (
                        <Button 
                          size="sm" variant="outline" 
                          onClick={() => setModalCollege(col)}
                          className="text-slate-500"
                        >
                          Manage Record
                        </Button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 bg-slate-50/50">
          <div className="text-sm text-slate-500 font-medium">
            Showing <span className="text-slate-900 font-bold">{total === 0 ? 0 : (page * limit) + 1}</span> to <span className="text-slate-900 font-bold">{Math.min((page + 1) * limit, total)}</span> of <span className="text-slate-900 font-bold">{total}</span>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page === 0 || isLoading} onClick={() => setPage(p => p - 1)}>
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={(page + 1) * limit >= total || isLoading} onClick={() => setPage(p => p + 1)}>
              Next
            </Button>
          </div>
        </div>
      </div>

      <LocationTriageModal 
        isOpen={!!modalCollege}
        college={modalCollege}
        onClose={() => setModalCollege(null)}
        onConfirm={handleTriage}
      />
    </div>
  );
}