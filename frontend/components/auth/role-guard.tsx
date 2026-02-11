"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth, AdminRole } from "@/components/providers/auth-provider";
import { Loader2, ShieldAlert } from "lucide-react";

interface RoleGuardProps {
  children: React.ReactNode;
  requiredRole: AdminRole;
}

export default function RoleGuard({ children, requiredRole }: RoleGuardProps) {
  const { user, isLoading, hasRole } = useAuth();
  const router = useRouter();
  const [isAuthorized, setIsAuthorized] = useState(false);

  useEffect(() => {
    if (isLoading) return;

    if (!user || !hasRole(requiredRole)) {
      // Not authorized -> Redirect to Dashboard
      router.replace("/admin");
    } else {
      setIsAuthorized(true);
    }
  }, [user, isLoading, hasRole, requiredRole, router]);

  if (isLoading || !isAuthorized) {
    return (
      <div className="h-screen w-full flex flex-col items-center justify-center bg-slate-50 gap-4">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
        <p className="text-sm text-slate-500 font-medium">Verifying Clearance...</p>
      </div>
    );
  }

  return <>{children}</>;
}