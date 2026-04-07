"use client";

import { CollegeBand, CollegeFilterSearchResponse } from "../../types/contracts";

type BandPillSwitcherProps = {
  searchResponse: CollegeFilterSearchResponse;
  activeBand: CollegeBand;
  onChangeBand: (band: CollegeBand) => void;
};

const BAND_ORDER: CollegeBand[] = ["SAFE", "MODERATE", "HARD", "SUGGESTED"];

export function BandPillSwitcher({
  searchResponse,
  activeBand,
  onChangeBand,
}: BandPillSwitcherProps) {
  return (
    <div className="rounded-2xl border border-border cf-soft-surface p-4 shadow-sm">
      {/* 1. Added w-full, prevented wrapping on desktop, and standardized gaps */}
      <div className="flex w-full flex-wrap items-center gap-3 sm:gap-4 xl:flex-nowrap xl:gap-6">
        {BAND_ORDER.map((band) => {
          const count = getBandCount(searchResponse, band);
          const isActive = activeBand === band;
          const toneClass = getBandToneClass(band);

          return (
            <button
              key={band}
              type="button"
              onClick={() => onChangeBand(band)}
              className={[
                // 2. Added flex-1 (equal width distribution), justify-center (centers inner content), and whitespace-nowrap (prevents text breaks)
                "inline-flex flex-1 cursor-pointer items-center justify-center gap-2.5 whitespace-nowrap rounded-full border px-3 py-2 text-sm font-medium transition-all duration-200 sm:px-4",
                toneClass,
                isActive
                  ? "cf-band-active shadow-sm"
                  : "border-border bg-background text-foreground hover:bg-muted",
              ].join(" ")}
            >
              <span className="relative inline-flex h-2.5 w-2.5">
                <span
                  className={[
                    "absolute inline-flex h-full w-full animate-ping rounded-full opacity-75",
                    isActive ? "cf-band-dot" : "bg-muted-foreground",
                  ].join(" ")}
                />
                <span
                  className={[
                    "relative inline-flex h-2.5 w-2.5 rounded-full",
                    isActive ? "cf-band-dot" : "bg-muted-foreground",
                  ].join(" ")}
                />
              </span>

              <span>{band}</span>

              <span
                className={[
                  "inline-flex min-w-7 items-center justify-center rounded-full px-2 py-0.5 text-xs font-semibold",
                  isActive ? "cf-band-badge" : "bg-muted text-foreground",
                ].join(" ")}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function getBandCount(
  searchResponse: CollegeFilterSearchResponse,
  band: CollegeBand
): number {
  switch (band) {
    case "SAFE":
      return searchResponse.band_counts.safe;
    case "MODERATE":
      return searchResponse.band_counts.moderate;
    case "HARD":
      return searchResponse.band_counts.hard;
    case "SUGGESTED":
      return searchResponse.band_counts.suggested;
  }
}

function getBandToneClass(band: CollegeBand): string {
  switch (band) {
    case "SAFE":
      return "cf-safe";
    case "MODERATE":
      return "cf-moderate";
    case "HARD":
      return "cf-hard";
    case "SUGGESTED":
      return "cf-suggested";
  }
}