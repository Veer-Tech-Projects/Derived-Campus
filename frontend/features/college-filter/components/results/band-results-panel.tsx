"use client";

import { CollegeBand, CollegeFilterSearchResponse } from "../../types/contracts";
import { BandEmptyNotice } from "./band-empty-notice";
import { BandPagination } from "./band-pagination";
import { CollegeCard } from "./college-card";

type BandResultsPanelProps = {
  searchResponse: CollegeFilterSearchResponse;
  activeBand: CollegeBand;
  isLoading: boolean;
  isSelectionPanelCollapsed: boolean;
  onPreviousPage: (band: CollegeBand) => void;
  onNextPage: (band: CollegeBand) => void;
};

export function BandResultsPanel({
  searchResponse,
  activeBand,
  isLoading,
  isSelectionPanelCollapsed,
  onPreviousPage,
  onNextPage,
}: BandResultsPanelProps) {
  const bandResult = getBandResult(searchResponse, activeBand);

  if (bandResult.items.length === 0) {
    return <BandEmptyNotice band={activeBand} />;
  }

  return (
    <div className="space-y-4">
      {bandResult.pagination.cap_reached ? (
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-700">
          More colleges are available in this band, but the current result view is capped for performance.
        </div>
      ) : null}

      <div
        className={[
          "grid gap-4",
          isSelectionPanelCollapsed
            ? "xl:grid-cols-3"
            : "xl:grid-cols-2",
        ].join(" ")}
      >
        {bandResult.items.map((item) => (
          <CollegeCard
            key={`${item.college_id}-${item.program_code}-${item.band}`}
            item={item}
          />
        ))}
      </div>

      <BandPagination
        page={bandResult.pagination.page}
        pageSize={bandResult.pagination.page_size}
        totalMatchingCount={bandResult.pagination.total_matching_count}
        cappedTotalAvailable={bandResult.pagination.capped_total_available}
        hasNextPage={bandResult.pagination.has_next_page}
        capReached={bandResult.pagination.cap_reached}
        isLoading={isLoading}
        onPrevious={() => onPreviousPage(activeBand)}
        onNext={() => onNextPage(activeBand)}
      />
    </div>
  );
}

function getBandResult(
  searchResponse: CollegeFilterSearchResponse,
  band: CollegeBand
) {
  switch (band) {
    case "SAFE":
      return searchResponse.bands.safe;
    case "MODERATE":
      return searchResponse.bands.moderate;
    case "HARD":
      return searchResponse.bands.hard;
    case "SUGGESTED":
      return searchResponse.bands.suggested;
  }
}