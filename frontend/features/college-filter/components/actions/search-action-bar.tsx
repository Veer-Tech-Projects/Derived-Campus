"use client";

type SearchActionBarProps = {
  isSearchReady: boolean;
  isSearching: boolean;
  hasExecutedSearch: boolean;
  resultsAreStale: boolean;
  onSearch: () => void;
};

export function SearchActionBar({
  isSearchReady,
  isSearching,
  hasExecutedSearch,
  resultsAreStale,
  onSearch,
}: SearchActionBarProps) {
  const helperText = !isSearchReady
    ? "Complete all required inputs to enable search."
    : resultsAreStale
      ? "Selections changed after the last successful search."
      : hasExecutedSearch
        ? "Search is up to date."
        : "Ready to search colleges.";

  return (
    <div className="space-y-3 rounded-2xl border border-border cf-soft-surface p-3.5 shadow-sm">
      <div className="space-y-1">
        <h3 className="text-xs font-semibold text-foreground">Search Workspace</h3>
        <p className="text-[11px] leading-5 text-muted-foreground">{helperText}</p>
      </div>

      <button
        type="button"
        onClick={onSearch}
        disabled={!isSearchReady || isSearching}
        className={[
          "inline-flex cursor-pointer h-10 w-full items-center justify-center rounded-xl px-4 text-sm font-medium transition-all duration-200",
          "bg-foreground text-background shadow-sm",
          "hover:opacity-95",
          "disabled:cursor-not-allowed disabled:opacity-50",
        ].join(" ")}
      >
        {isSearching
          ? "Searching..."
          : resultsAreStale
            ? "Search Again"
            : "Search Colleges"}
      </button>
    </div>
  );
}