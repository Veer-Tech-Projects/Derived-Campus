import type {
  StudentAuthMeResponse,
  StudentOnboardingStateResponse,
  StudentProfileDTO,
} from "./student-auth-contracts";

export type StudentAuthStatus =
  | "unknown"
  | "refreshing"
  | "unauthenticated"
  | "authenticated_pending_onboarding"
  | "authenticated_completed"
  | "error";

export interface StudentAuthState {
  status: StudentAuthStatus;
  accessToken: string | null;
  profile: StudentProfileDTO | null;
  providerLinks: string[];
  initialized: boolean;
  errorMessage: string | null;
}

export interface StudentAuthContextValue extends StudentAuthState {
  refreshSession: () => Promise<void>;
  logout: () => Promise<void>;
  setAccessToken: (token: string | null) => void;
  setAuthenticatedFromMe: (payload: StudentAuthMeResponse) => void;
  clearAuth: () => void;
}

export interface StudentOnboardingViewState {
  onboardingRequired: boolean;
  onboardingState: StudentOnboardingStateResponse | null;
  loading: boolean;
  errorMessage: string | null;
}