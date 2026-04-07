import axios from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL;

/**
 * Dedicated public/student API client for the college filter tool.
 *
 * Design rules:
 * - no admin auth coupling
 * - no token refresh logic
 * - no redirects to admin login
 * - safe for unauthenticated student-facing routes
 */
export const studentPublicClient = axios.create({
  baseURL: BASE_URL,
  withCredentials: false,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 15000,
});

export type ApiErrorPayload = {
  detail?: string | Record<string, unknown> | Array<unknown>;
};

export function normalizeApiError(error: unknown): string {
  if (axios.isAxiosError<ApiErrorPayload>(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }

    if (Array.isArray(detail)) {
      return "Request validation failed.";
    }

    if (detail && typeof detail === "object") {
      return "Request could not be processed.";
    }

    if (error.response?.status === 404) {
      return "Requested resource was not found.";
    }

    if (error.response?.status === 500) {
      return "Server error occurred while processing the request.";
    }

    if (error.code === "ECONNABORTED") {
      return "Request timed out. Please try again.";
    }

    return "Something went wrong while calling the API.";
  }

  return "Unexpected error occurred.";
}