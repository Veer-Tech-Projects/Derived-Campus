import {
  CollegeFilterMetadataResponse,
  CollegeFilterPathCatalogResponse,
  CollegeFilterSearchRequest,
  CollegeFilterSearchResponse,
  UUID,
} from "../types/contracts";
import { studentPublicClient } from "./student-public-client";

export async function fetchCollegeFilterPaths(): Promise<CollegeFilterPathCatalogResponse> {
  const response = await studentPublicClient.get<CollegeFilterPathCatalogResponse>(
    "/student/college-filter/paths"
  );
  return response.data;
}

export async function fetchCollegeFilterMetadata(
  pathId: UUID
): Promise<CollegeFilterMetadataResponse> {
  const response = await studentPublicClient.get<CollegeFilterMetadataResponse>(
    `/student/college-filter/metadata/${pathId}`
  );
  return response.data;
}

export async function searchCollegeFilter(
  payload: CollegeFilterSearchRequest
): Promise<CollegeFilterSearchResponse> {
  const response = await studentPublicClient.post<CollegeFilterSearchResponse>(
    "/student/college-filter/search",
    payload
  );
  return response.data;
}