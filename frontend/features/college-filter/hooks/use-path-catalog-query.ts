import { useQuery } from "@tanstack/react-query";
import { fetchCollegeFilterPaths } from "../api/college-filter.api";
import { buildPathCatalogTree } from "../adapters/path-catalog.adapter";

export const COLLEGE_FILTER_PATHS_QUERY_KEY = ["college-filter", "paths"] as const;

export function usePathCatalogQuery() {
  return useQuery({
    queryKey: COLLEGE_FILTER_PATHS_QUERY_KEY,
    queryFn: fetchCollegeFilterPaths,
    staleTime: 5 * 60 * 1000,
    select: (data) => ({
      raw: data,
      tree: buildPathCatalogTree(data.items),
    }),
  });
}