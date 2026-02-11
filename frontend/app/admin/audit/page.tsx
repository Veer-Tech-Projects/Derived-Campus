"use client";

import { useEffect, useState } from "react";
import { fetchAuditLogs, AuditLog } from "@/lib/admin-api";
import { Activity, Search, Shield, User, Terminal, Database } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import RoleGuard from "@/components/auth/role-guard"; // <--- NEW IMPORT

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchAuditLogs();
      setLogs(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const getActionColor = (action: string) => {
    if (action.includes("DELETE")) return "bg-red-50 text-red-700 border-red-200";
    if (action.includes("CREATE")) return "bg-emerald-50 text-emerald-700 border-emerald-200";
    if (action.includes("UPDATE")) return "bg-amber-50 text-amber-700 border-amber-200";
    if (action.includes("LOGIN")) return "bg-blue-50 text-blue-700 border-blue-200";
    return "bg-slate-50 text-slate-700 border-slate-200";
  };

  const getIcon = (action: string) => {
    if (action.includes("LOGIN")) return <User className="w-3 h-3" />;
    if (action.includes("INGESTION")) return <Database className="w-3 h-3" />;
    return <Terminal className="w-3 h-3" />;
  };

  return (
    <RoleGuard requiredRole="SUPERADMIN">
      <div className="p-8 max-w-7xl mx-auto space-y-6 min-h-screen bg-slate-50/50">
        <div className="flex justify-between items-center pb-6 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white border border-slate-200 rounded-lg shadow-sm">
              <Activity className="w-6 h-6 text-indigo-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Audit Logs</h1>
              <p className="text-slate-500 text-sm">Immutable record of all administrative actions.</p>
            </div>
          </div>
        </div>

        <Card className="border-slate-200 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-100 bg-white flex justify-between items-center">
            <div className="relative w-72">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
              <Input placeholder="Search logs..." className="pl-9 bg-slate-50 border-slate-200" disabled />
            </div>
            <div className="text-xs text-slate-400 font-mono">
              LIVE FEED • READ ONLY
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200 font-medium">
                <tr>
                  <th className="px-6 py-3 w-48">Timestamp</th>
                  <th className="px-6 py-3">Actor</th>
                  <th className="px-6 py-3">Action</th>
                  <th className="px-6 py-3">Target</th>
                  <th className="px-6 py-3 w-96">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {logs.map((log) => {
                  const detailString = JSON.stringify(log.details);
                  return (
                    <tr key={log.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="px-6 py-3 font-mono text-xs text-slate-500 whitespace-nowrap">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-3 font-medium text-slate-900">
                        {log.admin_username}
                      </td>
                      <td className="px-6 py-3">
                        <Badge variant="outline" className={`rounded-sm font-mono text-[10px] uppercase ${getActionColor(log.action)}`}>
                          <span className="mr-1.5 opacity-50">{getIcon(log.action)}</span>
                          {log.action}
                        </Badge>
                      </td>
                      <td className="px-6 py-3 text-slate-600 font-mono text-xs">
                        {log.target_resource || "-"}
                      </td>
                      {/* [FIX] Truncation Logic */}
                      <td className="px-6 py-3 text-slate-500 text-xs font-mono" title={detailString}>
                        {detailString.length > 120 
                          ? detailString.slice(0, 120) + "..." 
                          : detailString}
                      </td>
                    </tr>
                  );
                })}
                {loading && (
                  <tr><td colSpan={5} className="p-12 text-center text-slate-400">Loading records...</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </RoleGuard>
  );
}