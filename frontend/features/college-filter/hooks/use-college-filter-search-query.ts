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

export class CollegeFilterSearchApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CollegeFilterSearchApiError";
  }
}

export function useCollegeFilterSearchQuery(accessToken: string | null) {
  return useMutation<SearchSuccessPayload, Error, CollegeFilterSearchRequest>({
    mutationFn: async (payload) => {
      if (!accessToken || !accessToken.trim()) {
        throw new CollegeFilterSearchApiError(
          "You must be signed in to run a College Filter search.",
        );
      }

      const response = await searchCollegeFilter(accessToken, payload);
      const resolvedDefaultBand = getDefaultVisibleBand(response);

      return {
        response,
        resolvedDefaultBand,
      };
    },
    retry: false,
  });
}