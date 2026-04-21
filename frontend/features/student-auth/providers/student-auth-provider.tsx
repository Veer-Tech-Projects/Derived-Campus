"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  getStudentAuthMe,
  logoutStudent,
  refreshStudentSession,
} from "../api/student-auth-api";
import type {
  StudentAuthMeResponse,
  StudentProfileDTO,
} from "../types/student-auth-contracts";
import type {
  StudentAuthContextValue,
  StudentAuthState,
} from "../types/student-auth-view-models";
import { registerStudentSessionLifecycleHandlers } from "../api/student-auth-api";

const StudentAuthContext = createContext<StudentAuthContextValue | undefined>(
  undefined,
);

function deriveStatusFromProfile(profile: StudentProfileDTO | null) {
  if (!profile) {
    return "unauthenticated" as const;
  }

  if (profile.onboarding_status === "PENDING") {
    return "authenticated_pending_onboarding" as const;
  }

  return "authenticated_completed" as const;
}

const initialState: StudentAuthState = {
  status: "unknown",
  accessToken: null,
  profile: null,
  providerLinks: [],
  initialized: false,
  errorMessage: null,
};

export function StudentAuthProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [state, setState] = useState<StudentAuthState>(initialState);

  const clearAuth = useCallback(() => {
    setState({
      status: "unauthenticated",
      accessToken: null,
      profile: null,
      providerLinks: [],
      initialized: true,
      errorMessage: null,
    });
  }, []);

  const setAccessToken = useCallback((token: string | null) => {
    setState((prev) => ({
      ...prev,
      accessToken: token,
    }));
  }, []);

  const setAuthenticatedFromMe = useCallback((payload: StudentAuthMeResponse) => {
    setState((prev) => ({
      ...prev,
      status: deriveStatusFromProfile(payload.profile),
      profile: payload.profile,
      providerLinks: payload.provider_links,
      initialized: true,
      errorMessage: null,
    }));
  }, []);

  const refreshSession = useCallback(async () => {
    setState((prev) => ({
      ...prev,
      status: prev.initialized ? "refreshing" : "unknown",
      errorMessage: null,
    }));

    try {
      const refreshResponse = await refreshStudentSession();

      setState((prev) => ({
        ...prev,
        accessToken: refreshResponse.access_token,
      }));

      const meResponse = await getStudentAuthMe(refreshResponse.access_token);

      setState((prev) => ({
        ...prev,
        status: deriveStatusFromProfile(meResponse.profile),
        accessToken: refreshResponse.access_token,
        profile: meResponse.profile,
        providerLinks: meResponse.provider_links,
        initialized: true,
        errorMessage: null,
      }));
    } catch (error) {
      const message =
        error instanceof Error && error.message === "SESSION_EXPIRED"
          ? "Your session expired. Please sign in again."
          : error instanceof Error
            ? error.message
            : "Failed to refresh student session.";

      setState({
        status: "unauthenticated",
        accessToken: null,
        profile: null,
        providerLinks: [],
        initialized: true,
        errorMessage: message,
      });
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutStudent();
    } finally {
      clearAuth();
    }
  }, [clearAuth]);

  useEffect(() => {
    const unregister = registerStudentSessionLifecycleHandlers({
      onAccessTokenRefreshed: (nextAccessToken: string) => {
        setAccessToken(nextAccessToken);
      },
      onSessionExpired: () => {
        clearAuth();
      },
    });

    return unregister;
  }, [clearAuth, setAccessToken]);

  useEffect(() => {
    void refreshSession();
  }, [refreshSession]);

  const value = useMemo<StudentAuthContextValue>(
    () => ({
      ...state,
      refreshSession,
      logout,
      setAccessToken,
      setAuthenticatedFromMe,
      clearAuth,
    }),
    [state, refreshSession, logout, setAccessToken, setAuthenticatedFromMe, clearAuth],
  );

  return (
    <StudentAuthContext.Provider value={value}>
      {children}
    </StudentAuthContext.Provider>
  );
}

export function useStudentAuthContext(): StudentAuthContextValue {
  const context = useContext(StudentAuthContext);
  if (!context) {
    throw new Error("useStudentAuthContext must be used within StudentAuthProvider.");
  }
  return context;
}