import { useMutation } from "@tanstack/react-query";
import { searchCollegeFilter } from "../api/college-filter.api";
import { getDefaultVisibleBand } from "../adapters/search.adapter";
import {
  CollegeBand,
  CollegeFilterSearchRequest,
  CollegeFilterSearchResponse,
} from "../types/contracts";

interface SearchSuccessPayload {
  response: CollegeFilterSearchResponse;
  resolvedDefaultBand: CollegeBand;
}

export function useCollegeFilterSearchQuery() {
  return useMutation<SearchSuccessPayload, Error, CollegeFilterSearchRequest>({
    mutationFn: async (payload) => {
      const response = await searchCollegeFilter(payload);
      const resolvedDefaultBand = getDefaultVisibleBand(response);
      return {
        response,
        resolvedDefaultBand,
      };
    },
  });
}