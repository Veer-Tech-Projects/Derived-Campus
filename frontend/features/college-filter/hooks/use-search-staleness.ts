interface UseSearchStalenessArgs {
  hasExecutedSearch: boolean;
  resultsAreStale: boolean;
}

export function useSearchStaleness({
  hasExecutedSearch,
  resultsAreStale,
}: UseSearchStalenessArgs) {
  const shouldShowStaleBanner = hasExecutedSearch && resultsAreStale;

  return {
    shouldShowStaleBanner,
  };
}