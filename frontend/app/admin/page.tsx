"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  DashboardStats, ExamConfig, 
  fetchDashboardStats, fetchExamConfigs, updateExamMode 
} from "@/lib/admin-api";
import { 
  FileText, Database, ShieldAlert, Scale,
  Settings, AlertTriangle, ArrowRight, LogOut, User, Command, Activity, Users
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { useAuth } from "@/components/providers/auth-provider";

export default function AdminDashboard() {
  const { user, logout, hasRole } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [exams, setExams] = useState<ExamConfig[]>([]);
  
  // Mode Switching State
  const [targetExam, setTargetExam] = useState<ExamConfig | null>(null);
  const [targetMode, setTargetMode] = useState<"BOOTSTRAP" | "CONTINUOUS" | null>(null);

  const loadData = async () => {
    try {
      const [sData, eData] = await Promise.all([fetchDashboardStats(), fetchExamConfigs()]);
      setStats(sData);
      setExams(eData);
    } catch (e) { console.error("Dashboard Load Failed", e); }
  };

  useEffect(() => { loadData(); }, []);

  const handleModeChange = async () => {
    if (!targetExam || !targetMode) return;
    try {
      await updateExamMode(targetExam.exam_code, targetMode);
      setTargetExam(null);
      setTargetMode(null);
      loadData();
    } catch (e) { alert("Failed to update mode"); }
  };

  const confirmChange = (exam: ExamConfig, mode: "BOOTSTRAP" | "CONTINUOUS") => {
    setTargetExam(exam);
    setTargetMode(mode);
  };

  return (
    <div className="min-h-screen bg-[#FAFAFA] selection:bg-indigo-100 selection:text-indigo-900">
      
      {/* --- TOP NAVIGATION BAR --- */}
      <header className="sticky top-0 z-40 w-full border-b border-zinc-200 bg-white/80 backdrop-blur-xl h-20">
        <div className="max-w-7xl mx-auto px-6 h-full flex items-center justify-between">
          
          {/* Logo / Brand */}
          <div className="flex items-center gap-4">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-tr from-zinc-900 to-zinc-700 text-white shadow-lg shadow-zinc-200 ring-1 ring-black/5">
              <Command className="w-5 h-5" />
            </div>
            <div className="flex flex-col justify-center">
              <h1 className="text-sm font-bold text-zinc-900 leading-none tracking-tight">Derived Campus</h1>
              <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest mt-1">Governance Plane</span>
            </div>
          </div>

          {/* Right Actions */}
          <div className="flex items-center gap-6">
            <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-white rounded-full border border-zinc-200 shadow-sm">
              <div className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </div>
              <span className="text-xs font-medium text-zinc-600">Operational</span>
            </div>
            
            <div className="h-8 w-px bg-zinc-200"></div>

            <div className="flex items-center gap-3">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-semibold text-zinc-900">{user?.username || "Admin"}</p>
                <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">{user?.role}</p>
              </div>
              <div className="h-10 w-10 rounded-full bg-zinc-100 border border-zinc-200 flex items-center justify-center text-zinc-500">
                <User className="w-5 h-5" />
              </div>
              <Button 
                variant="ghost" 
                size="icon"
                onClick={() => logout()}
                className="text-zinc-400 hover:text-red-600 hover:bg-red-50 rounded-full w-10 h-10 transition-colors"
                title="Sign Out"
              >
                <LogOut className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        
        {/* --- WELCOME HEADER --- */}
        <section className="flex flex-col gap-1">
          <h2 className="text-2xl font-bold text-zinc-900 tracking-tight">
            Welcome back, <span className="text-zinc-600">{user?.username}</span>
          </h2>
          <p className="text-zinc-500 text-sm font-medium">
            Here is your daily governance overview.
          </p>
        </section>

        {/* --- KPI GRID --- */}
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          
          {/* AIRLOCK CARD */}
          <Link href="/admin/airlock" className="group">
            <Card className="h-full border-zinc-200/60 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative overflow-hidden bg-white">
              <div className="absolute top-0 right-0 p-4 opacity-[0.03] group-hover:opacity-10 transition-opacity">
                <FileText className="w-24 h-24 text-indigo-600 rotate-12" />
              </div>
              <CardHeader className="pb-2">
                <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform duration-300 border border-indigo-100">
                  <FileText className="w-5 h-5 text-indigo-600" />
                </div>
                <CardTitle className="text-xs font-bold text-zinc-400 uppercase tracking-widest">Airlock</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-zinc-900 tracking-tight">{stats?.airlock_pending ?? "-"}</div>
                <div className="flex items-center mt-2 text-xs font-semibold text-indigo-600 group-hover:translate-x-1 transition-transform">
                  Pending Artifacts <ArrowRight className="w-3 h-3 ml-1" />
                </div>
              </CardContent>
            </Card>
          </Link>

          {/* IDENTITY CARD */}
          <Link href="/admin/triage" className="group">
            <Card className="h-full border-zinc-200/60 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative overflow-hidden bg-white">
              <div className="absolute top-0 right-0 p-4 opacity-[0.03] group-hover:opacity-10 transition-opacity">
                <ShieldAlert className="w-24 h-24 text-amber-500 -rotate-12" />
              </div>
              <CardHeader className="pb-2">
                <div className="w-10 h-10 rounded-lg bg-amber-50 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform duration-300 border border-amber-100">
                  <ShieldAlert className="w-5 h-5 text-amber-600" />
                </div>
                <CardTitle className="text-xs font-bold text-zinc-400 uppercase tracking-widest">Identity Triage</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-zinc-900 tracking-tight">{stats?.triage_pending ?? "-"}</div>
                <div className="flex items-center mt-2 text-xs font-semibold text-amber-600 group-hover:translate-x-1 transition-transform">
                  Unresolved Candidates <ArrowRight className="w-3 h-3 ml-1" />
                </div>
              </CardContent>
            </Card>
          </Link>

          {/* POLICY CARD */}
          <Link href="/admin/triage/seat-policy" className="group">
            <Card className="h-full border-zinc-200/60 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative overflow-hidden bg-white">
              <div className="absolute top-0 right-0 p-4 opacity-[0.03] group-hover:opacity-10 transition-opacity">
                <Scale className="w-24 h-24 text-rose-500 rotate-6" />
              </div>
              <CardHeader className="pb-2">
                <div className="w-10 h-10 rounded-lg bg-rose-50 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform duration-300 border border-rose-100">
                  <Scale className="w-5 h-5 text-rose-600" />
                </div>
                <CardTitle className="text-xs font-bold text-zinc-400 uppercase tracking-widest">Seat Policy</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-zinc-900 tracking-tight">{stats?.seat_policy_pending ?? "-"}</div>
                <div className="flex items-center mt-2 text-xs font-semibold text-rose-600 group-hover:translate-x-1 transition-transform">
                  Active Violations <ArrowRight className="w-3 h-3 ml-1" />
                </div>
              </CardContent>
            </Card>
          </Link>

          {/* REGISTRY CARD */}
          <Link href="/admin/registry" className="group">
            <Card className="h-full border-zinc-200/60 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative overflow-hidden bg-white">
              <div className="absolute top-0 right-0 p-4 opacity-[0.03] group-hover:opacity-10 transition-opacity">
                <Database className="w-24 h-24 text-emerald-500 -rotate-6" />
              </div>
              <CardHeader className="pb-2">
                <div className="w-10 h-10 rounded-lg bg-emerald-50 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform duration-300 border border-emerald-100">
                  <Database className="w-5 h-5 text-emerald-600" />
                </div>
                <CardTitle className="text-xs font-bold text-zinc-400 uppercase tracking-widest">Master Registry</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-zinc-900 tracking-tight">{stats?.registry_total ?? "-"}</div>
                <div className="flex items-center mt-2 text-xs font-semibold text-emerald-600 group-hover:translate-x-1 transition-transform">
                  Official Colleges <ArrowRight className="w-3 h-3 ml-1" />
                </div>
              </CardContent>
            </Card>
          </Link>
        </section>

        {/* --- GOVERNANCE SECTION --- */}
        <section>
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-white rounded-lg border border-zinc-200 shadow-sm">
              <Settings className="w-5 h-5 text-zinc-600" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-zinc-900">System Configuration</h3>
              <p className="text-xs text-zinc-500 font-medium">Manage ingestion strategies and active pipelines.</p>
            </div>
          </div>
          
          <div className="bg-white border border-zinc-200 rounded-xl shadow-sm overflow-hidden">
            <table className="w-full text-sm text-left">
              <thead className="bg-zinc-50/50 border-b border-zinc-100">
                <tr>
                  <th className="px-6 py-4 font-semibold text-zinc-500 w-1/4">Exam Pipeline</th>
                  <th className="px-6 py-4 font-semibold text-zinc-500">Status</th>
                  <th className="px-6 py-4 font-semibold text-zinc-500 text-center">Ingestion Mode</th>
                  <th className="px-6 py-4 font-semibold text-zinc-500 text-right">Last Sync</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {exams.map(exam => (
                  <tr key={exam.exam_code} className="hover:bg-zinc-50/50 transition-colors">
                    <td className="px-6 py-5">
                      <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-lg bg-zinc-100 flex items-center justify-center text-xs font-bold text-zinc-600 border border-zinc-200">
                          {exam.exam_code.substring(0,2)}
                        </div>
                        <div>
                          <div className="font-bold text-zinc-900">{exam.exam_code}</div>
                          <div className="text-xs text-zinc-400 font-medium">Standard Pipeline</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-5">
                      {exam.is_active ? (
                        <Badge className="bg-emerald-50 text-emerald-700 hover:bg-emerald-50 border-emerald-200 shadow-none px-2.5 py-0.5 rounded-md font-semibold">
                          <Activity className="w-3 h-3 mr-1.5" /> Active
                        </Badge>
                      ) : (
                        <Badge variant="secondary" className="px-3 py-1 font-medium">Inactive</Badge>
                      )}
                    </td>
                    <td className="px-6 py-5 text-center">
                      <div className="inline-flex bg-zinc-100/50 p-1 rounded-lg border border-zinc-200/50">
                        {hasRole("SUPERADMIN") ? (
                          <>
                            <button
                              onClick={() => confirmChange(exam, "BOOTSTRAP")}
                              className={`px-4 py-1.5 rounded-md text-xs font-bold transition-all ${
                                exam.ingestion_mode === "BOOTSTRAP"
                                  ? "bg-white text-indigo-600 shadow-sm ring-1 ring-black/5"
                                  : "text-zinc-400 hover:text-zinc-600 hover:bg-zinc-200/50"
                              }`}
                            >
                              Bootstrap
                            </button>
                            <button
                              onClick={() => confirmChange(exam, "CONTINUOUS")}
                              className={`px-4 py-1.5 rounded-md text-xs font-bold transition-all ${
                                exam.ingestion_mode === "CONTINUOUS"
                                  ? "bg-white text-emerald-600 shadow-sm ring-1 ring-black/5"
                                  : "text-zinc-400 hover:text-zinc-600 hover:bg-zinc-200/50"
                              }`}
                            >
                              Continuous
                            </button>
                          </>
                        ) : (
                          <span className={`px-4 py-1.5 rounded-md text-xs font-bold bg-white shadow-sm ring-1 ring-black/5 ${
                            exam.ingestion_mode === "BOOTSTRAP" ? "text-indigo-600" : "text-emerald-600"
                          }`}>
                            {exam.ingestion_mode} Mode
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-5 text-right">
                      <span className="text-zinc-400 font-medium text-xs">
                        {new Date(exam.last_updated).toLocaleDateString(undefined, { 
                          year: 'numeric', month: 'short', day: 'numeric' 
                        })}
                      </span>
                    </td>
                  </tr>
                ))}
                {exams.length === 0 && (
                  <tr>
                    <td colSpan={4} className="p-12 text-center text-zinc-400 italic">
                      No exams configured. System waiting for initialization.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* --- SYSTEM ADMINISTRATION (SUPER ADMIN ONLY) --- */}
        {hasRole("SUPERADMIN") && (
          <section>
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-white rounded-lg border border-zinc-200 shadow-sm">
                <Users className="w-5 h-5 text-zinc-600" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-zinc-900">System Administration</h3>
                <p className="text-xs text-zinc-500 font-medium">Manage team access and audit logs.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Link href="/admin/users" className="group">
                <Card className="h-full border-zinc-200/60 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative overflow-hidden bg-white">
                   <div className="absolute top-0 right-0 p-4 opacity-[0.03] group-hover:opacity-10 transition-opacity">
                    <Users className="w-24 h-24 text-indigo-600 rotate-12" />
                  </div>
                  <CardContent className="p-6 flex items-center justify-between h-full">
                    <div className="flex items-center gap-4">
                      <div className="h-12 w-12 rounded-full bg-indigo-50 flex items-center justify-center text-indigo-600 group-hover:scale-110 transition-transform border border-indigo-100">
                        <Users className="w-6 h-6" />
                      </div>
                      <div>
                        <h4 className="font-bold text-zinc-900">Team Management</h4>
                        <p className="text-xs text-zinc-500 mt-1">Invite and manage administrators.</p>
                      </div>
                    </div>
                    <ArrowRight className="w-5 h-5 text-zinc-300 group-hover:text-indigo-600 transition-colors" />
                  </CardContent>
                </Card>
              </Link>

              <Link href="/admin/audit" className="group">
                <Card className="h-full border-zinc-200/60 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative overflow-hidden bg-white">
                   <div className="absolute top-0 right-0 p-4 opacity-[0.03] group-hover:opacity-10 transition-opacity">
                    <Activity className="w-24 h-24 text-emerald-600 -rotate-12" />
                  </div>
                  <CardContent className="p-6 flex items-center justify-between h-full">
                    <div className="flex items-center gap-4">
                      <div className="h-12 w-12 rounded-full bg-emerald-50 flex items-center justify-center text-emerald-600 group-hover:scale-110 transition-transform border border-emerald-100">
                        <Activity className="w-6 h-6" />
                      </div>
                      <div>
                        <h4 className="font-bold text-zinc-900">Audit Logs</h4>
                        <p className="text-xs text-zinc-500 mt-1">View security and action history.</p>
                      </div>
                    </div>
                    <ArrowRight className="w-5 h-5 text-zinc-300 group-hover:text-emerald-600 transition-colors" />
                  </CardContent>
                </Card>
              </Link>
            </div>
          </section>
        )}

        {/* Confirmation Modal */}
        <Dialog open={!!targetExam} onOpenChange={(open) => !open && setTargetExam(null)}>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <div className="mx-auto w-12 h-12 rounded-full bg-amber-50 flex items-center justify-center mb-3 border border-amber-100">
                <AlertTriangle className="w-6 h-6 text-amber-600" />
              </div>
              <DialogTitle className="text-center text-lg font-bold text-zinc-900">
                Confirm Mode Change
              </DialogTitle>
              <DialogDescription className="text-center pt-1">
                You are switching <strong>{targetExam?.exam_code}</strong> to <span className="font-bold text-zinc-900 underline decoration-zinc-300 underline-offset-4">{targetMode}</span> mode.
              </DialogDescription>
            </DialogHeader>
            
            <div className="py-2">
              {targetMode === "BOOTSTRAP" && (
                <div className="bg-red-50 text-red-900 p-4 rounded-xl text-xs border border-red-100 flex gap-3 items-start leading-relaxed">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-red-600 mt-0.5" />
                  <div>
                    <strong className="block mb-1 font-bold text-red-700">Critical Warning</strong>
                    Bootstrap mode enables "Wipe & Replace". Starting ingestion will <span className="font-bold underline">permanently delete</span> existing data.
                  </div>
                </div>
              )}
              {targetMode === "CONTINUOUS" && (
                <div className="bg-emerald-50 text-emerald-900 p-4 rounded-xl text-xs border border-emerald-100 flex gap-3 items-start leading-relaxed">
                  <Database className="w-4 h-4 shrink-0 text-emerald-600 mt-0.5" />
                  <div>
                    <strong className="block mb-1 font-bold text-emerald-700">Safe Operation</strong>
                    Continuous mode preserves records. Data will be appended or updated incrementally without data loss.
                  </div>
                </div>
              )}
            </div>

            <DialogFooter className="sm:justify-center gap-2 pt-2">
              <Button variant="outline" onClick={() => setTargetExam(null)} className="rounded-lg h-10 px-6">Cancel</Button>
              <Button 
                variant={targetMode === "BOOTSTRAP" ? "destructive" : "default"} 
                onClick={handleModeChange}
                className="rounded-lg h-10 px-8 font-semibold shadow-md"
              >
                Confirm Update
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </main>
    </div>
  );
}