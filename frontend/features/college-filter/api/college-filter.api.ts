import axios from "axios";

import {
  CollegeFilterMetadataResponse,
  CollegeFilterPathCatalogResponse,
  CollegeFilterSearchRequest,
  CollegeFilterSearchResponse,
  UUID,
} from "../types/contracts";
import { studentPublicClient } from "./student-public-client";
import {
  buildStudentAuthConfig,
  studentAuthenticatedClient,
} from "./student-authenticated-client";

type InsufficientCreditsDetail = {
  error_code: string;
  message: string;
  available_credits: number;
  required_credits: number;
  billing_redirect_path: string;
};

function isInsufficientCreditsDetail(
  value: unknown,
): value is InsufficientCreditsDetail {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Record<string, unknown>;

  return (
    candidate.error_code === "INSUFFICIENT_CREDITS" &&
    typeof candidate.message === "string" &&
    typeof candidate.available_credits === "number" &&
    typeof candidate.required_credits === "number" &&
    typeof candidate.billing_redirect_path === "string"
  );
}

export class CollegeFilterInsufficientCreditsError extends Error {
  readonly errorCode: "INSUFFICIENT_CREDITS";
  readonly availableCredits: number;
  readonly requiredCredits: number;
  readonly billingRedirectPath: string;

  constructor(detail: InsufficientCreditsDetail) {
    super(detail.message);
    this.name = "CollegeFilterInsufficientCreditsError";
    this.errorCode = "INSUFFICIENT_CREDITS";
    this.availableCredits = detail.available_credits;
    this.requiredCredits = detail.required_credits;
    this.billingRedirectPath = detail.billing_redirect_path;
  }
}

export function isCollegeFilterInsufficientCreditsError(
  error: unknown,
): error is CollegeFilterInsufficientCreditsError {
  return error instanceof CollegeFilterInsufficientCreditsError;
}

export async function fetchCollegeFilterPaths(): Promise<CollegeFilterPathCatalogResponse> {
  const response = await studentPublicClient.get<CollegeFilterPathCatalogResponse>(
    "/student/college-filter/paths",
  );
  return response.data;
}

export async function fetchCollegeFilterMetadata(
  pathId: UUID,
): Promise<CollegeFilterMetadataResponse> {
  const response = await studentPublicClient.get<CollegeFilterMetadataResponse>(
    `/student/college-filter/metadata/${pathId}`,
  );
  return response.data;
}

export async function searchCollegeFilter(
  accessToken: string,
  payload: CollegeFilterSearchRequest,
): Promise<CollegeFilterSearchResponse> {
  try {
    const response = await studentAuthenticatedClient.post<CollegeFilterSearchResponse>(
      "/student/college-filter/search",
      payload,
      buildStudentAuthConfig(accessToken),
    );
    return response.data;
  } catch (error: unknown) {
    if (axios.isAxiosError(error)) {
      const detail = error.response?.data?.detail;
      if (isInsufficientCreditsDetail(detail)) {
        throw new CollegeFilterInsufficientCreditsError(detail);
      }
    }

    throw error;
  }
}