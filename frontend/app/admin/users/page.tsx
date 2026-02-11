"use client";

import { useEffect, useState } from "react";
import { fetchAdmins, createAdmin, updateAdmin, deleteAdmin, AdminUser } from "@/lib/admin-api";
import { 
  Shield, ShieldCheck, Eye, MoreHorizontal, 
  Plus, Trash2, RotateCcw, Ban, CheckCircle, Lock 
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, 
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, 
  DialogDescription, DialogFooter
} from "@/components/ui/dialog";
import { toast } from "sonner";
import RoleGuard from "@/components/auth/role-guard"; // <--- NEW IMPORT

export default function TeamPage() {
  const [admins, setAdmins] = useState<AdminUser[]>([]);
  
  // Dialog States
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [resetTarget, setResetTarget] = useState<AdminUser | null>(null);
  
  // Form Data
  const [formData, setFormData] = useState({ username: "", email: "", password: "", role: "VIEWER" });
  const [newPassword, setNewPassword] = useState("");

  const loadData = async () => {
    try {
      const data = await fetchAdmins();
      setAdmins(data);
    } catch (e) { toast.error("Failed to load team"); }
  };

  useEffect(() => { loadData(); }, []);

  const handleCreate = async () => {
    try {
      await createAdmin(formData);
      toast.success("Operative Onboarded");
      setIsInviteOpen(false);
      setFormData({ username: "", email: "", password: "", role: "VIEWER" });
      loadData();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Failed to create admin");
    }
  };

  const handleStatusToggle = async (admin: AdminUser) => {
    try {
      await updateAdmin(admin.id, { is_active: !admin.is_active });
      toast.success(`User ${admin.is_active ? "Disabled" : "Enabled"}`);
      loadData();
    } catch (e: any) { toast.error(e.response?.data?.detail); }
  };

  const handlePasswordReset = async () => {
    if (!resetTarget || !newPassword) return;
    if (newPassword.length < 8) {
      toast.error("Password must be at least 8 characters");
      return;
    }
    try {
      await updateAdmin(resetTarget.id, { password: newPassword });
      toast.success("Password Reset Successfully");
      setResetTarget(null);
      setNewPassword("");
    } catch (e: any) { toast.error(e.response?.data?.detail); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure? This action is irreversible.")) return;
    try {
      await deleteAdmin(id);
      toast.success("User Deleted");
      loadData();
    } catch (e: any) { toast.error(e.response?.data?.detail); }
  };

  const getRoleIcon = (role: string) => {
    switch (role) {
      case "SUPERADMIN": return <ShieldCheck className="w-4 h-4 text-violet-600" />;
      case "EDITOR": return <Shield className="w-4 h-4 text-emerald-600" />;
      default: return <Eye className="w-4 h-4 text-slate-500" />;
    }
  };

  return (
    <RoleGuard requiredRole="SUPERADMIN">
      <div className="p-8 max-w-7xl mx-auto space-y-8 min-h-screen bg-slate-50/50">
        <div className="flex justify-between items-center pb-6 border-b border-slate-200">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Team Management</h1>
            <p className="text-slate-500 mt-1">Manage access control and operational roles.</p>
          </div>
          <Button onClick={() => setIsInviteOpen(true)} className="bg-slate-900 text-white hover:bg-slate-800">
            <Plus className="w-4 h-4 mr-2" /> Invite Admin
          </Button>
        </div>

        <div className="bg-white border rounded-xl shadow-sm overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-50 border-b text-slate-500 font-medium">
              <tr>
                <th className="px-6 py-4">User Identity</th>
                <th className="px-6 py-4">Role</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Last Active</th>
                <th className="w-12 px-6 py-4"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {admins.map((admin) => (
                <tr key={admin.id} className="hover:bg-slate-50/50 transition-colors group">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 font-bold border border-slate-200">
                        {/* [FIX] Defensive coding for username */}
                        {admin.username?.[0]?.toUpperCase() ?? "?"}
                      </div>
                      <div>
                        <div className="font-semibold text-slate-900">{admin.username}</div>
                        <div className="text-xs text-slate-500">{admin.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 w-fit px-2 py-1 rounded-md">
                      {getRoleIcon(admin.role)}
                      <span className="text-xs font-bold text-slate-700">{admin.role}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    {admin.is_active ? (
                      <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 border-emerald-200 shadow-none">Active</Badge>
                    ) : (
                      <Badge variant="secondary" className="text-slate-500 bg-slate-100">Disabled</Badge>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right text-slate-400 text-xs font-mono">
                    {admin.last_login_at ? new Date(admin.last_login_at).toLocaleString() : "Never"}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-slate-600">
                          <MoreHorizontal className="w-4 h-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuLabel>Actions</DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={() => handleStatusToggle(admin)}>
                          {admin.is_active ? <><Ban className="mr-2 h-4 w-4" /> Disable Account</> : <><CheckCircle className="mr-2 h-4 w-4" /> Enable Account</>}
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => setResetTarget(admin)}>
                          <RotateCcw className="mr-2 h-4 w-4" /> Reset Password
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem className="text-red-600 focus:text-red-600 focus:bg-red-50" onClick={() => handleDelete(admin.id)}>
                          <Trash2 className="mr-2 h-4 w-4" /> Delete User
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* INVITE DIALOG */}
        <Dialog open={isInviteOpen} onOpenChange={setIsInviteOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Invite New Administrator</DialogTitle>
              <DialogDescription>Create credentials for a new team member.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-500">Username</label>
                  <Input value={formData.username} onChange={e => setFormData({...formData, username: e.target.value})} placeholder="e.g. jdoe" />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-500">Role</label>
                  <select 
                    className="w-full flex h-9 w-full rounded-md border border-slate-200 bg-transparent px-3 py-1 text-sm shadow-sm"
                    value={formData.role}
                    onChange={e => setFormData({...formData, role: e.target.value})}
                  >
                    <option value="VIEWER">Viewer (Read Only)</option>
                    <option value="EDITOR">Editor (Can Ingest)</option>
                    <option value="SUPERADMIN">Super Admin (God Mode)</option>
                  </select>
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-500">Email Address</label>
                <Input type="email" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} placeholder="user@derivedcampus.com" />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-500">Temporary Password</label>
                <Input type="password" value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} placeholder="••••••••" />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsInviteOpen(false)}>Cancel</Button>
              <Button onClick={handleCreate}>Create Account</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* PASSWORD RESET DIALOG */}
        <Dialog open={!!resetTarget} onOpenChange={(open) => !open && setResetTarget(null)}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Lock className="w-5 h-5 text-amber-500" /> Reset Password
              </DialogTitle>
              <DialogDescription>
                Set a new password for <strong>{resetTarget?.username}</strong>. This will invalidate their active sessions.
              </DialogDescription>
            </DialogHeader>
            <div className="py-4">
              <label className="text-xs font-semibold text-slate-500 mb-2 block">New Password</label>
              <Input 
                type="password" 
                placeholder="Minimum 8 characters" 
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setResetTarget(null)}>Cancel</Button>
              <Button onClick={handlePasswordReset}>Confirm Reset</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </RoleGuard>
  );
}