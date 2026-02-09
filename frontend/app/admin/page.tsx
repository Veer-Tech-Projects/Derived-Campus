"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  DashboardStats, ExamConfig, 
  fetchDashboardStats, fetchExamConfigs, updateExamMode 
} from "@/lib/admin-api";
import { 
  LayoutDashboard, ShieldAlert, FileText, Database, 
  Settings, AlertTriangle, ArrowRight, Scale // [NEW] Added Scale icon
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

export default function AdminDashboard() {
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
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center gap-3 border-b pb-6">
        <div className="p-3 bg-indigo-600 rounded-lg text-white">
          <LayoutDashboard className="w-6 h-6" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Admin Command Center</h1>
          <p className="text-gray-500">System Overview & Governance Control</p>
        </div>
      </div>

      {/* KPI Cards - [UPDATED LAYOUT] */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        
        {/* 1. AIRLOCK */}
        <Link href="/admin/airlock" className="block group">
          <Card className="hover:shadow-md transition-shadow border-l-4 border-l-blue-500 h-full">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-500 uppercase tracking-wider flex items-center gap-2">
                <FileText className="w-4 h-4" /> Airlock
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold text-gray-900">
                {stats?.airlock_pending ?? "-"}
              </div>
              <p className="text-sm text-gray-500 mt-1 flex items-center group-hover:text-blue-600">
                Pending Artifacts <ArrowRight className="w-4 h-4 ml-1 opacity-0 group-hover:opacity-100 transition-opacity"/>
              </p>
            </CardContent>
          </Card>
        </Link>

        {/* 2. IDENTITY TRIAGE */}
        <Link href="/admin/triage" className="block group">
          <Card className="hover:shadow-md transition-shadow border-l-4 border-l-amber-500 h-full">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-500 uppercase tracking-wider flex items-center gap-2">
                <ShieldAlert className="w-4 h-4" /> Identity Triage
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold text-gray-900">
                {stats?.triage_pending ?? "-"}
              </div>
              <p className="text-sm text-gray-500 mt-1 flex items-center group-hover:text-amber-600">
                Unresolved Identities <ArrowRight className="w-4 h-4 ml-1 opacity-0 group-hover:opacity-100 transition-opacity"/>
              </p>
            </CardContent>
          </Card>
        </Link>

        {/* 3. SEAT POLICY TRIAGE [NEW CARD] */}
        <Link href="/admin/triage/seat-policy" className="block group">
          <Card className="hover:shadow-md transition-shadow border-l-4 border-l-purple-500 h-full">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-500 uppercase tracking-wider flex items-center gap-2">
                <Scale className="w-4 h-4" /> Seat Policy
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold text-gray-900">
                {stats?.seat_policy_pending ?? "-"}
              </div>
              <p className="text-sm text-gray-500 mt-1 flex items-center group-hover:text-purple-600">
                Policy Violations <ArrowRight className="w-4 h-4 ml-1 opacity-0 group-hover:opacity-100 transition-opacity"/>
              </p>
            </CardContent>
          </Card>
        </Link>

        {/* 4. REGISTRY */}
        <Link href="/admin/registry" className="block group">
          <Card className="hover:shadow-md transition-shadow border-l-4 border-l-green-500 h-full">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-500 uppercase tracking-wider flex items-center gap-2">
                <Database className="w-4 h-4" /> Registry
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold text-gray-900">
                {stats?.registry_total ?? "-"}
              </div>
              <p className="text-sm text-gray-500 mt-1 flex items-center group-hover:text-green-600">
                Official Colleges <ArrowRight className="w-4 h-4 ml-1 opacity-0 group-hover:opacity-100 transition-opacity"/>
              </p>
            </CardContent>
          </Card>
        </Link>

      </div>

      {/* Governance Section */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Settings className="w-5 h-5 text-gray-600" /> Exam Configuration
        </h2>
        
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-gray-50 border-b text-gray-500">
              <tr>
                <th className="px-6 py-3 font-semibold">Exam Code</th>
                <th className="px-6 py-3 font-semibold">Status</th>
                <th className="px-6 py-3 font-semibold text-center">Ingestion Strategy</th>
                <th className="px-6 py-3 font-semibold text-right">Last Updated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {exams.map(exam => (
                <tr key={exam.exam_code}>
                  <td className="px-6 py-4 font-mono font-medium text-gray-900 uppercase">
                    {exam.exam_code}
                  </td>
                  <td className="px-6 py-4">
                    <Badge variant={exam.is_active ? "default" : "secondary"}>
                      {exam.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 text-center">
                    <div className="inline-flex bg-gray-100 p-1 rounded-lg">
                      <button
                        onClick={() => confirmChange(exam, "BOOTSTRAP")}
                        className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                          exam.ingestion_mode === "BOOTSTRAP"
                            ? "bg-white text-indigo-600 shadow-sm"
                            : "text-gray-500 hover:text-gray-700"
                        }`}
                      >
                        Bootstrap
                      </button>
                      <button
                        onClick={() => confirmChange(exam, "CONTINUOUS")}
                        className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                          exam.ingestion_mode === "CONTINUOUS"
                            ? "bg-white text-green-600 shadow-sm"
                            : "text-gray-500 hover:text-gray-700"
                        }`}
                      >
                        Continuous
                      </button>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right text-gray-400 text-xs">
                    {new Date(exam.last_updated).toLocaleDateString()}
                  </td>
                </tr>
              ))}
              {exams.length === 0 && (
                <tr>
                  <td colSpan={4} className="p-8 text-center text-gray-400 italic">
                    No exams configured yet. They will appear here once ingested.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confirmation Modal */}
      <Dialog open={!!targetExam} onOpenChange={(open) => !open && setTargetExam(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-amber-600">
              <AlertTriangle className="w-5 h-5" /> Change Ingestion Mode?
            </DialogTitle>
            
            <DialogDescription className="pt-2 space-y-2" asChild>
              <div className="text-sm text-muted-foreground">
                <p>
                  You are switching <strong>{targetExam?.exam_code}</strong> to <span className="font-bold text-gray-900">{targetMode}</span> mode.
                </p>
                {targetMode === "BOOTSTRAP" && (
                  <div className="bg-red-50 text-red-800 p-3 rounded text-xs border border-red-100">
                    <strong>Warning:</strong> Bootstrap mode is destructive. It enables &quot;Wipe & Replace&quot; for ingestion runs to ensure a clean slate. Use only during initial setup.
                  </div>
                )}
                {targetMode === "CONTINUOUS" && (
                  <div className="bg-green-50 text-green-800 p-3 rounded text-xs border border-green-100">
                    <strong>Safe:</strong> Continuous mode preserves existing data and only appends new rounds or updates.
                  </div>
                )}
              </div>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTargetExam(null)}>Cancel</Button>
            <Button onClick={handleModeChange}>Confirm Change</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}