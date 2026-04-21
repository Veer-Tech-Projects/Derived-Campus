"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useRef,
  useCallback,
} from "react";
import { apiClient, setAccessToken } from "@/lib/api-client";
import { useRouter, usePathname } from "next/navigation";
import { toast } from "sonner";

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

  const isCheckInProgress = useRef(false);

  const isAdminRoute = pathname?.startsWith("/admin") ?? false;

  useEffect(() => {
    const initAuth = async () => {
      if (!isAdminRoute) {
        setUser(null);
        setIsLoading(false);
        return;
      }

      try {
        const refreshRes = await apiClient.post("/auth/refresh");
        setAccessToken(refreshRes.data.access_token);

        const meRes = await apiClient.get("/auth/me");
        setUser(meRes.data);
      } catch {
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    void initAuth();
  }, [isAdminRoute]);

  useEffect(() => {
    if (!isAdminRoute || !user) return;

    const heartbeat = setInterval(async () => {
      if (isCheckInProgress.current) return;
      isCheckInProgress.current = true;

      try {
        await apiClient.get("/auth/me");
      } catch {
        // interceptor handles route-aware failure behavior
      } finally {
        isCheckInProgress.current = false;
      }
    }, 30000);

    return () => clearInterval(heartbeat);
  }, [isAdminRoute, user]);

  useEffect(() => {
    if (!isAdminRoute) return;
    if (pathname === "/admin/login") return;

    if (!isLoading && !user && pathname.startsWith("/admin")) {
      router.push("/admin/login");
    }
  }, [user, isLoading, pathname, router, isAdminRoute]);

  const login = async (username: string, password: string) => {
    const res = await apiClient.post("/auth/login", { username, password });
    setAccessToken(res.data.access_token);

    const me = await apiClient.get("/auth/me");
    setUser(me.data);

    toast.success("Welcome back, Commander");
    router.push("/admin");
  };

  const logout = async () => {
    try {
      await apiClient.post("/auth/logout");
    } catch {
      // ignore
    } finally {
      setAccessToken(null);
      setUser(null);
      router.push("/admin/login");
      toast.info("Session terminated");
    }
  };

  const hasRole = useCallback(
    (requiredRole: AdminRole) => {
      if (!user) return false;
      return ROLE_HIERARCHY[user.role] >= ROLE_HIERARCHY[requiredRole];
    },
    [user],
  );

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, hasRole }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
};