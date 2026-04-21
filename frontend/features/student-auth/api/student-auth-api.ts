import type {
  StudentAuthMeResponse,
  StudentAuthProvider,
  StudentAuthProviderDTO,
  StudentLogoutResponse,
  StudentOnboardingCompleteRequest,
  StudentOnboardingCompleteResponse,
  StudentOnboardingStateResponse,
  StudentProfileImageUploadResponse,
  StudentSessionTokenResponse,
  StudentPhoneValidationRequest,
  StudentPhoneValidationResponse,
} from "../types/student-auth-contracts";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

if (!API_BASE_URL) {
  throw new Error("NEXT_PUBLIC_API_URL is not configured.");
}

export type StudentJsonRequestOptions = {
  accessToken?: string | null;
  method?: "GET" | "POST" | "PATCH";
  body?: unknown;
};

type StudentSessionLifecycleHandlers = {
  onAccessTokenRefreshed?: (accessToken: string) => void;
  onSessionExpired?: () => void;
};

let studentSessionLifecycleHandlers: StudentSessionLifecycleHandlers = {};
let inFlightRefreshPromise: Promise<StudentSessionTokenResponse> | null = null;

function notifyAccessTokenRefreshed(accessToken: string): void {
  studentSessionLifecycleHandlers.onAccessTokenRefreshed?.(accessToken);
}

function notifySessionExpired(): void {
  studentSessionLifecycleHandlers.onSessionExpired?.();
}

export function registerStudentSessionLifecycleHandlers(
  handlers: StudentSessionLifecycleHandlers,
): () => void {
  studentSessionLifecycleHandlers = handlers;

  return () => {
    studentSessionLifecycleHandlers = {};
  };
}

function isUnauthorizedResponse(response: Response): boolean {
  return response.status === 401;
}

function isSessionExpiredMessage(message: string): boolean {
  const normalized = message.trim().toUpperCase();
  return normalized === "SESSION_EXPIRED";
}

async function parseErrorResponse(response: Response): Promise<string> {
  let message = `Request failed with status ${response.status}`;

  try {
    const errorPayload = await response.json();
    if (errorPayload?.detail) {
      message =
        typeof errorPayload.detail === "string"
          ? errorPayload.detail
          : JSON.stringify(errorPayload.detail);
    }
  } catch {
    // keep fallback message
  }

  return message;
}

async function requestFreshStudentSessionDirect(): Promise<StudentSessionTokenResponse> {
  if (!inFlightRefreshPromise) {
    inFlightRefreshPromise = (async () => {
      const response = await fetch(`${API_BASE_URL}/student-auth/refresh`, {
        method: "POST",
        credentials: "include",
        cache: "no-store",
      });

      if (!response.ok) {
        notifySessionExpired();
        throw new Error("SESSION_EXPIRED");
      }

      const payload =
        (await response.json()) as StudentSessionTokenResponse;

      if (!payload.access_token) {
        notifySessionExpired();
        throw new Error("SESSION_EXPIRED");
      }

      notifyAccessTokenRefreshed(payload.access_token);
      return payload;
    })().finally(() => {
      inFlightRefreshPromise = null;
    });
  }

  return inFlightRefreshPromise;
}

export async function executeStudentJsonRequest<T>(
  path: string,
  options: StudentJsonRequestOptions = {},
  hasRetried = false,
): Promise<T> {
  const { accessToken, method = "GET", body } = options;

  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    credentials: "include",
    cache: "no-store",
  });

  if (response.ok) {
    return response.json() as Promise<T>;
  }

  if (
    isUnauthorizedResponse(response) &&
    !hasRetried &&
    path !== "/student-auth/refresh"
  ) {
    try {
      const refreshedSession = await requestFreshStudentSessionDirect();

      return executeStudentJsonRequest<T>(
        path,
        {
          ...options,
          accessToken: refreshedSession.access_token,
        },
        true,
      );
    } catch (error) {
      if (
        error instanceof Error &&
        isSessionExpiredMessage(error.message)
      ) {
        throw error;
      }

      notifySessionExpired();
      throw new Error("SESSION_EXPIRED");
    }
  }

  if (isUnauthorizedResponse(response) && hasRetried) {
    notifySessionExpired();
    throw new Error("SESSION_EXPIRED");
  }

  throw new Error(await parseErrorResponse(response));
}

async function executeMultipartRequest<T>(
  path: string,
  {
    accessToken,
    file,
  }: {
    accessToken: string;
    file: File;
  },
  hasRetried = false,
): Promise<T> {
  const headers: HeadersInit = {};

  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers,
    body: formData,
    credentials: "include",
    cache: "no-store",
  });

  if (response.ok) {
    return response.json() as Promise<T>;
  }

  if (
    isUnauthorizedResponse(response) &&
    !hasRetried &&
    path !== "/student-auth/refresh"
  ) {
    try {
      const refreshedSession = await requestFreshStudentSessionDirect();

      return executeMultipartRequest<T>(
        path,
        {
          accessToken: refreshedSession.access_token,
          file,
        },
        true,
      );
    } catch (error) {
      if (
        error instanceof Error &&
        isSessionExpiredMessage(error.message)
      ) {
        throw error;
      }

      notifySessionExpired();
      throw new Error("SESSION_EXPIRED");
    }
  }

  if (isUnauthorizedResponse(response) && hasRetried) {
    notifySessionExpired();
    throw new Error("SESSION_EXPIRED");
  }

  throw new Error(await parseErrorResponse(response));
}

export async function getStudentAuthProviders(): Promise<StudentAuthProviderDTO[]> {
  return executeStudentJsonRequest<StudentAuthProviderDTO[]>("/student-auth/providers");
}

export async function refreshStudentSession(): Promise<StudentSessionTokenResponse> {
  return requestFreshStudentSessionDirect();
}

export async function getStudentAuthMe(
  accessToken: string,
): Promise<StudentAuthMeResponse> {
  return executeStudentJsonRequest<StudentAuthMeResponse>("/student-auth/me", {
    accessToken,
  });
}

export async function getStudentOnboardingState(
  accessToken: string,
): Promise<StudentOnboardingStateResponse> {
  return executeStudentJsonRequest<StudentOnboardingStateResponse>(
    "/student-auth/onboarding-state",
    { accessToken },
  );
}

export async function uploadStudentProfileImage(
  accessToken: string,
  file: File,
): Promise<StudentProfileImageUploadResponse> {
  return executeMultipartRequest<StudentProfileImageUploadResponse>(
    "/student-auth/profile-image",
    {
      accessToken,
      file,
    },
  );
}

export async function completeStudentOnboarding(
  accessToken: string,
  payload: StudentOnboardingCompleteRequest,
): Promise<StudentOnboardingCompleteResponse> {
  return executeStudentJsonRequest<StudentOnboardingCompleteResponse>(
    "/student-auth/onboarding/complete",
    {
      method: "POST",
      accessToken,
      body: payload,
    },
  );
}

export async function logoutStudent(): Promise<StudentLogoutResponse> {
  return executeStudentJsonRequest<StudentLogoutResponse>("/student-auth/logout", {
    method: "POST",
  });
}

export function buildStudentProviderLoginUrl(
  provider: StudentAuthProvider,
): string {
  switch (provider) {
    case "GOOGLE":
      return `${API_BASE_URL}/student-auth/oauth/start/google`;
    case "FACEBOOK":
      return `${API_BASE_URL}/student-auth/oauth/start/facebook`;
    default:
      throw new Error(`Unsupported student auth provider: ${provider}`);
  }
}

export async function validateStudentPhoneForOnboarding(
  accessToken: string,
  payload: StudentPhoneValidationRequest,
): Promise<StudentPhoneValidationResponse> {
  return executeStudentJsonRequest<StudentPhoneValidationResponse>(
    "/student-auth/onboarding/validate-phone",
    {
      method: "POST",
      accessToken,
      body: payload,
    },
  );
}