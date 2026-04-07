interface UseFollowStepsArgs {
  hasExecutedSearch: boolean;
  hasRenderableResults: boolean;
}

export function useFollowStepsVisibility({
  hasExecutedSearch,
  hasRenderableResults,
}: UseFollowStepsArgs) {
  /**
   * Follow steps appear only in the fresh empty tool state.
   * They do not reappear merely because filters changed after a search.
   */
  const shouldShowFollowSteps = !hasExecutedSearch && !hasRenderableResults;

  return {
    shouldShowFollowSteps,
  };
}