"use client";

import { useEffect, useState, useMemo } from "react";
import { Artifact, fetchArtifacts, triggerDirtyIngestion, approveBatchArtifacts, fetchIngestionStatus } from "@/lib/admin-api";
import { RefreshCw, PlayCircle, FileText, AlertTriangle, CheckCircle, XCircle, Copy, Search, Filter, Hash, CheckSquare, Square, MinusSquare, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/components/providers/auth-provider"; // <--- Auth

// ... StatusBadge Component (Keep as is) ...
function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    INGESTED: "bg-emerald-100 text-emerald-700 border-emerald-200",
    APPROVED: "bg-blue-100 text-blue-700 border-blue-200",
    PENDING: "bg-slate-100 text-slate-700 border-slate-200",
    FAILED: "bg-red-100 text-red-700 border-red-200",
  };
  const icons: Record<string, any> = { INGESTED: CheckCircle, FAILED: XCircle };
  const Icon = icons[status] || AlertTriangle; 

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${styles[status] || styles.PENDING}`}>
      {Icon && <Icon className="w-3 h-3 mr-1.5" />}
      {status}
    </span>
  );
}

export default function AirlockPage() {
  const { hasRole } = useAuth(); // <--- Auth Hook
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  
  const [serverIngesting, setServerIngesting] = useState(false);
  const [startingIngestion, setStartingIngestion] = useState(false);
  
  const isLocked = serverIngesting || startingIngestion;

  const [search, setSearch] = useState("");
  const [filterExam, setFilterExam] = useState("ALL");
  const [filterYear, setFilterYear] = useState("ALL");
  const [filterRound, setFilterRound] = useState("ALL");
  const [filterStatus, setFilterStatus] = useState("ALL");

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchArtifacts();
      setArtifacts(data);
      setSelectedIds(new Set());
    } catch (e) {
      console.error(e);
      toast.error("Failed to connect to backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const { is_ingesting } = await fetchIngestionStatus();
        setServerIngesting(prev => {
          if (prev && !is_ingesting) {
            toast.success("Ingestion Cycle Complete");
            loadData();
          }
          return is_ingesting;
        });
      } catch (e) { }
    };
    const interval = setInterval(checkStatus, 3000);
    checkStatus();
    return () => clearInterval(interval);
  }, []);

  useEffect(() => { loadData(); }, []);

  const uniqueExams = useMemo(() => Array.from(new Set(artifacts.map(a => a.exam_code))), [artifacts]);
  const uniqueYears = useMemo(() => Array.from(new Set(artifacts.map(a => a.year))).sort().reverse(), [artifacts]);
  const uniqueStatuses = useMemo(() => Array.from(new Set(artifacts.map(a => a.status))), [artifacts]);
  const uniqueRounds = useMemo(() => {
    const rounds = new Set<number>();
    artifacts.forEach(a => { if (a.round_number) rounds.add(a.round_number); });
    return Array.from(rounds).sort((a, b) => a - b);
  }, [artifacts]);

  const filteredArtifacts = useMemo(() => {
    return artifacts.filter(art => {
      const matchesSearch = art.round_name.toLowerCase().includes(search.toLowerCase()) || art.pdf_path.toLowerCase().includes(search.toLowerCase());
      const matchesExam = filterExam === "ALL" || art.exam_code === filterExam;
      const matchesYear = filterYear === "ALL" || art.year.toString() === filterYear;
      const matchesStatus = filterStatus === "ALL" || art.status === filterStatus;
      const matchesRound = filterRound === "ALL" || (art.round_number && art.round_number.toString() === filterRound);
      return matchesSearch && matchesExam && matchesYear && matchesStatus && matchesRound;
    });
  }, [artifacts, search, filterExam, filterYear, filterStatus, filterRound]);

  const toggleSelection = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSelectedIds(next);
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredArtifacts.length && filteredArtifacts.length > 0) setSelectedIds(new Set());
    else setSelectedIds(new Set(filteredArtifacts.map(a => a.id)));
  };

  const getMasterCheckboxIcon = () => {
    if (selectedIds.size === 0) return <Square className="w-5 h-5 text-slate-400" />;
    if (selectedIds.size === filteredArtifacts.length) return <CheckSquare className="w-5 h-5 text-indigo-600" />;
    return <MinusSquare className="w-5 h-5 text-indigo-600" />;
  };

  const startGracePeriod = () => {
    setStartingIngestion(true);
    setTimeout(() => setStartingIngestion(false), 4000);
  };

  const handleBatchApprove = async () => {
    if (selectedIds.size === 0) return;
    startGracePeriod(); 
    try {
      await approveBatchArtifacts(Array.from(selectedIds));
      toast.success(`Queued ${selectedIds.size} artifacts`);
      setArtifacts(prev => prev.map(a => 
        selectedIds.has(a.id) ? { ...a, status: "APPROVED", requires_reprocessing: true } : a
      ));
      setSelectedIds(new Set());
    } catch (e) {
      toast.error("Batch approval failed");
      setStartingIngestion(false);
    }
  };

  const handleApplyDirty = async () => {
    startGracePeriod();
    try {
      await triggerDirtyIngestion();
      toast.success("System Update Queued");
    } catch (e) {
      toast.error("Failed to start ingestion");
      setStartingIngestion(false);
    }
  };

  const copyToClipboard = (text: string) => { navigator.clipboard.writeText(text); toast.success("ID Copied"); };
  const dirtyCount = artifacts.filter(a => a.requires_reprocessing).length;

  // RBAC Permission Check
  const canEdit = hasRole("EDITOR");

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 relative min-h-screen bg-slate-50/50">
      
      {/* --- HEADER --- */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center border-b border-slate-200 pb-5 gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Data Airlock</h1>
          <p className="text-slate-500 mt-1">Manage ingestion lifecycle and reprocessing.</p>
        </div>
        <div className="flex gap-3">
          <button 
            onClick={loadData} 
            disabled={loading || isLocked}
            className="flex items-center px-4 py-2 border bg-white rounded-md hover:bg-slate-50 disabled:opacity-50 text-sm font-medium transition-colors"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          
          {/* RBAC CHECK: Only Editor can trigger ingestion */}
          {canEdit && (
            <button 
              onClick={handleApplyDirty} 
              disabled={isLocked || dirtyCount === 0}
              className={`flex items-center px-4 py-2 rounded-md text-white text-sm font-medium transition-all shadow-sm
                ${dirtyCount > 0 && !isLocked 
                  ? 'bg-amber-600 hover:bg-amber-700 hover:shadow-md' 
                  : 'bg-slate-300 cursor-not-allowed text-slate-500'}`}
            >
              {isLocked ? (
                 <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Ingesting...</>
              ) : (
                 <><PlayCircle className="w-4 h-4 mr-2" /> Apply Updates ({dirtyCount})</>
              )}
            </button>
          )}
        </div>
      </div>

      {/* --- FILTER BAR --- */}
      <div className="grid grid-cols-1 md:grid-cols-6 gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="relative md:col-span-2">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search filenames..." 
            className="w-full pl-9 pr-4 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            disabled={isLocked}
          />
        </div>
        {/* Filters remain the same, just keeping concise */}
        <select className="px-3 py-2 border rounded-md text-sm bg-white" value={filterExam} onChange={(e) => setFilterExam(e.target.value)}>
          <option value="ALL">All Exams</option>
          {uniqueExams.map(e => <option key={e} value={e}>{e.toUpperCase()}</option>)}
        </select>
        <select className="px-3 py-2 border rounded-md text-sm bg-white" value={filterYear} onChange={(e) => setFilterYear(e.target.value)}>
          <option value="ALL">All Years</option>
          {uniqueYears.map(y => <option key={y} value={y}>{y}</option>)}
        </select>
        <select className="px-3 py-2 border rounded-md text-sm bg-white" value={filterRound} onChange={(e) => setFilterRound(e.target.value)}>
          <option value="ALL">All Rounds</option>
          {uniqueRounds.map(r => <option key={r} value={r.toString()}>Round {r}</option>)}
        </select>
        <select className="px-3 py-2 border rounded-md text-sm bg-white" value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
          <option value="ALL">All Statuses</option>
          {uniqueStatuses.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {/* --- BATCH ACTION FLOATING BAR (RBAC PROTECTED) --- */}
      {selectedIds.size > 0 && canEdit && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 bg-slate-900 text-white px-6 py-3 rounded-full shadow-2xl flex items-center gap-6 border border-slate-700 animate-in fade-in slide-in-from-bottom-4">
          <div className="flex items-center gap-2">
            <span className="bg-slate-700 px-2 py-0.5 rounded text-xs font-mono font-bold">{selectedIds.size}</span>
            <span className="text-sm font-medium">Selected</span>
          </div>
          <div className="h-4 w-px bg-slate-700"></div>
          <button 
            onClick={handleBatchApprove}
            disabled={isLocked}
            className="flex items-center gap-2 text-sm font-bold text-emerald-400 hover:text-emerald-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLocked ? <Loader2 className="w-4 h-4 animate-spin"/> : <PlayCircle className="w-4 h-4" />}
            Approve & Ingest
          </button>
          <button 
            onClick={() => setSelectedIds(new Set())}
            disabled={isLocked}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <XCircle className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* --- GRID --- */}
      <div className="bg-white border rounded-xl shadow-sm overflow-hidden mb-20">
        <table className="w-full text-sm text-left">
          <thead className="bg-slate-50 text-slate-500 border-b">
            <tr>
              <th className="w-12 px-4 py-3 text-center">
                {/* RBAC: Disable master checkbox if viewer */}
                <button 
                  onClick={toggleSelectAll} 
                  disabled={isLocked || !canEdit}
                  className="hover:text-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {getMasterCheckboxIcon()}
                </button>
              </th>
              <th className="px-4 py-3 font-semibold w-16 text-center">#</th>
              <th className="px-6 py-3 font-semibold">Artifact Source</th>
              <th className="px-6 py-3 font-semibold">Exam & Round</th>
              <th className="px-6 py-3 font-semibold">Status</th>
              <th className="px-6 py-3 font-semibold text-right">System ID</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredArtifacts.map((art, index) => {
              const isSelected = selectedIds.has(art.id);
              return (
                <tr key={art.id} className={`transition-colors ${isSelected ? 'bg-indigo-50/30' : 'hover:bg-slate-50'}`}>
                  <td className="px-4 py-4 text-center">
                    <button 
                      onClick={() => toggleSelection(art.id)} 
                      disabled={isLocked || !canEdit}
                      className="text-slate-300 hover:text-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isSelected ? <CheckSquare className="w-5 h-5 text-indigo-600" /> : <Square className="w-5 h-5" />}
                    </button>
                  </td>
                  <td className="px-4 py-4 text-center text-slate-400 font-mono text-xs">
                    {index + 1}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-indigo-50 rounded-lg text-indigo-600">
                        <FileText className="w-5 h-5" />
                      </div>
                      <div className="max-w-[300px]">
                        <div className="font-medium text-slate-900 truncate" title={art.pdf_path}>
                          {art.pdf_path.split('/').pop()}
                        </div>
                        {art.requires_reprocessing && (
                          <span className="flex items-center text-xs text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full mt-1 w-fit font-medium">
                            <AlertTriangle className="w-3 h-3 mr-1" /> Requires Update
                          </span>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-col gap-1">
                      <div className="flex gap-2">
                          <span className="font-bold text-slate-900 text-[10px] uppercase tracking-wider bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                           {art.exam_code} {art.year}
                         </span>
                         {art.round_number ? (
                           <span className="flex items-center font-bold text-indigo-700 text-[10px] uppercase tracking-wider bg-indigo-50 border border-indigo-100 px-2 py-0.5 rounded">
                             <Hash className="w-3 h-3 mr-1 opacity-50"/> Round {art.round_number}
                           </span>
                         ) : (
                           <span className="text-slate-400 text-xs px-2 py-0.5">--</span>
                         )}
                      </div>
                      <span className="text-slate-500 font-medium text-xs mt-0.5 truncate max-w-[250px]" title={art.round_name}>
                        {art.round_name}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <StatusBadge status={art.status} />
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2 group">
                      <span className="text-slate-400 font-mono text-xs">{art.id.slice(0, 8)}...</span>
                      <button 
                        onClick={() => copyToClipboard(art.id)}
                        className="text-slate-300 hover:text-indigo-600 transition-colors p-1 rounded hover:bg-indigo-50"
                        title="Copy Full ID"
                      >
                        <Copy className="w-3 h-3" />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {filteredArtifacts.length === 0 && !loading && (
              <tr>
                <td colSpan={6} className="text-center py-16 text-slate-400">
                  <div className="flex flex-col items-center justify-center gap-3">
                    <div className="bg-slate-100 p-4 rounded-full">
                        <Filter className="w-8 h-8 text-slate-300" />
                    </div>
                    <p>No artifacts found matching your filters.</p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      
      {/* Footer Info */}
      <div className="text-xs text-slate-400 text-right font-medium">
        Showing {filteredArtifacts.length} of {artifacts.length} artifacts
      </div>
    </div>
  );
}