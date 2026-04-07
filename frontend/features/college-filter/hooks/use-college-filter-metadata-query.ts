import { useQuery } from "@tanstack/react-query";
import { fetchCollegeFilterMetadata } from "../api/college-filter.api";
import { getVisibleFilters } from "../adapters/metadata.adapter";
import { UUID } from "../types/contracts";

export function getCollegeFilterMetadataQueryKey(pathId: UUID | null) {
  return ["college-filter", "metadata", pathId] as const;
}

export function useCollegeFilterMetadataQuery(pathId: UUID | null) {
  return useQuery({
    queryKey: getCollegeFilterMetadataQueryKey(pathId),
    queryFn: async () => {
      if (!pathId) {
        throw new Error("Path id is required to fetch college filter metadata.");
      }
      return fetchCollegeFilterMetadata(pathId);
    },
    enabled: Boolean(pathId),
    staleTime: 5 * 60 * 1000,
    select: (data) => ({
      raw: data,
      visibleFilters: getVisibleFilters(data),
    }),
  });
}