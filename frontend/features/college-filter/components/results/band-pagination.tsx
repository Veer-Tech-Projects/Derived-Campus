"use client";

type BandPaginationProps = {
  page: number;
  pageSize: number;
  totalMatchingCount: number;
  cappedTotalAvailable: number;
  hasNextPage: boolean;
  capReached: boolean;
  isLoading: boolean;
  onPrevious: () => void;
  onNext: () => void;
};

export function BandPagination({
  page,
  pageSize,
  totalMatchingCount,
  cappedTotalAvailable,
  hasNextPage,
  capReached,
  isLoading,
  onPrevious,
  onNext,
}: BandPaginationProps) {
  const hasPreviousPage = page > 1;

  return (
    <div className="space-y-3 rounded-2xl border border-border bg-card p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground">
        <div>
          <span className="font-medium text-foreground">Page:</span> {page}
        </div>
        <div>
          <span className="font-medium text-foreground">Page Size:</span> {pageSize}
        </div>
        <div>
          <span className="font-medium text-foreground">Available in Current Window:</span>{" "}
          {cappedTotalAvailable}
        </div>
        <div>
          <span className="font-medium text-foreground">Total Matching Count:</span>{" "}
          {totalMatchingCount}
        </div>
      </div>

      {capReached ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-700">
          The backend indicates more results may exist, but the current window is capped for performance.
        </div>
      ) : null}

      <div className="flex items-center justify-end gap-3">
        <button
          type="button"
          onClick={onPrevious}
          disabled={!hasPreviousPage || isLoading}
          className="inline-flex h-10 items-center justify-center rounded-xl border border-border bg-background px-4 text-sm font-medium text-foreground transition disabled:cursor-not-allowed disabled:opacity-50"
        >
          Previous
        </button>

        <button
          type="button"
          onClick={onNext}
          disabled={!hasNextPage || isLoading}
          className="inline-flex h-10 items-center justify-center rounded-xl border border-border bg-background px-4 text-sm font-medium text-foreground transition disabled:cursor-not-allowed disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}