"use client";

import React, { createContext, useContext, useEffect, useState, useRef, useCallback } from "react"; // <--- Added useCallback
import { apiClient, setAccessToken } from "@/lib/api-client"; // Updated import path
import { useRouter, usePathname } from "next/navigation";
import { toast } from "sonner";

// Matches backend RBAC Enum
export type AdminRole = "SUPERADMIN" | "EDITOR" | "VIEWER";

interface AdminUser {
  id: string;
  username: string;
  role: AdminRole;
  email: string;
}

interface AuthContextType {
  user: AdminUser | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  hasRole: (requiredRole: AdminRole) => boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

const ROLE_HIERARCHY: Record<AdminRole, number> = {
  SUPERADMIN: 3,
  EDITOR: 2,
  VIEWER: 1,
};

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<AdminUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();
  
  // Ref to prevent multiple concurrent checks
  const isCheckInProgress = useRef(false);

  // 1. Initial Session Hydration
  useEffect(() => {
    const initAuth = async () => {
      try {
        // Attempt Silent Refresh
        const refreshRes = await apiClient.post("/auth/refresh");
        setAccessToken(refreshRes.data.access_token);
        
        // Fetch Profile
        const meRes = await apiClient.get("/auth/me");
        setUser(meRes.data);
      } catch (e) {
        // Session invalid or expired -> Normal behavior for first visit
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  // 2. Heartbeat: Check Session Validity Every 30 Seconds
  // This ensures that if the backend invalidates the session (e.g. password change),
  // the UI catches up without requiring a page refresh.
  useEffect(() => {
    if (!user) return; 

    const heartbeat = setInterval(async () => {
      if (isCheckInProgress.current) return;
      isCheckInProgress.current = true;

      try {
        await apiClient.get("/auth/me");
      } catch (e) {
        console.log("Heartbeat failed - Session invalid");
        // Interceptor handles the redirect
      } finally {
        isCheckInProgress.current = false;
      }
    }, 30000); 

    return () => clearInterval(heartbeat);
  }, [user]);

  // 3. Route Protection (Client Side)
  useEffect(() => {
    if (pathname === "/admin/login") return;

    if (!isLoading && !user && pathname.startsWith("/admin")) {
      router.push("/admin/login");
    }
  }, [user, isLoading, pathname, router]);

  const login = async (username: string, password: string) => {
    try {
      const res = await apiClient.post("/auth/login", { username, password });
      setAccessToken(res.data.access_token);
      
      const me = await apiClient.get("/auth/me");
      setUser(me.data);
      
      toast.success("Welcome back, Commander");
      router.push("/admin");
    } catch (e: any) {
      const msg = e.response?.data?.detail || "Login failed";
      // Pass error up so the Login Page can handle specific codes (like Lockout)
      throw e; 
    }
  };

  const logout = async () => {
    try {
      await apiClient.post("/auth/logout");
    } catch (e) {
      // Ignore errors
    } finally {
      setAccessToken(null);
      setUser(null);
      router.push("/admin/login");
      toast.info("Session terminated");
    }
  };

  // [FIX] Memoized RBAC Helper
  // Prevents RoleGuard from re-running logic unnecessarily
  const hasRole = useCallback((requiredRole: AdminRole) => {
    if (!user) return false;
    return ROLE_HIERARCHY[user.role] >= ROLE_HIERARCHY[requiredRole];
  }, [user]);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, hasRole }}>
      {!isLoading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
};