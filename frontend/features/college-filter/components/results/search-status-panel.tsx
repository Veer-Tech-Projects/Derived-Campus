"use client";

import { useMemo, useState } from "react";
import { AlertTriangle, Check, Copy, Wallet } from "lucide-react";
import {
  CollegeBand,
  CollegeCardDTO,
  CollegeFilterSearchResponse,
} from "../../types/contracts";
import { BandPillSwitcher } from "./band-pill-switcher";
import { BandResultsPanel } from "./band-results-panel";
import { ResultsHeader } from "./results-header";
import { ResultsPanelSkeleton } from "../shared/skeletons";
import { PremiumLoader } from "../shared/premium-loader";

type SearchStatusPanelProps = {
  searchResponse: CollegeFilterSearchResponse | null;
  activeVisibleBand: CollegeBand | null;
  resultsAreStale: boolean;
  searchErrorMessage: string | null;
  insufficientCreditsState: {
    message: string;
    availableCredits: number;
    requiredCredits: number;
    billingRedirectPath: string;
  } | null;
  isRefreshingResults: boolean;
  isSelectionPanelCollapsed: boolean;
  onOpenBilling: () => void;
  onChangeBand: (band: CollegeBand) => void;
  onPreviousPage: (band: CollegeBand) => void;
  onNextPage: (band: CollegeBand) => void;
};

export function SearchStatusPanel({
  searchResponse,
  activeVisibleBand,
  resultsAreStale,
  searchErrorMessage,
  insufficientCreditsState,
  isRefreshingResults,
  isSelectionPanelCollapsed,
  onOpenBilling,
  onChangeBand,
  onPreviousPage,
  onNextPage,
}: SearchStatusPanelProps) {
  const [copied, setCopied] = useState(false);

  const activeItems = useMemo(() => {
    if (!searchResponse || !activeVisibleBand) return [];
    switch (activeVisibleBand) {
      case "SAFE":
        return searchResponse.bands.safe.items;
      case "MODERATE":
        return searchResponse.bands.moderate.items;
      case "HARD":
        return searchResponse.bands.hard.items;
      case "SUGGESTED":
        return searchResponse.bands.suggested.items;
    }
  }, [searchResponse, activeVisibleBand]);

  const handleCopy = async () => {
    if (!activeItems.length || !searchResponse || !activeVisibleBand) return;

    const lines: string[] = [];
    lines.push(`${searchResponse.path.visible_label} - ${activeVisibleBand} colleges`);
    lines.push("");

    activeItems.forEach((item, index) => {
      lines.push(`${index + 1}.`);

      if (shouldIncludeInstituteCode(item)) {
        addCopyLine(lines, "Institute Code", item.institute_code);
      }

      addCopyLine(lines, "College Name", item.college_name);

      if (item.course_type) {
        addCopyLine(lines, "Course Type", item.course_type);
      }

      addCopyLine(lines, "Program Name", item.program_name);
      addCopyLine(lines, "Band", item.band);
      addCopyLine(
        lines,
        "Current Cutoff",
        formatMetricValue(item.current_round_cutoff_value, false)
      );

      if (item.opening_rank !== null && item.opening_rank !== undefined) {
        addCopyLine(lines, "Opening Rank", String(item.opening_rank));
      }

      addCopyLine(
        lines,
        "Probability",
        formatMetricValue(item.probability_percent, true)
      );

      if (item.location_type) {
        addCopyLine(lines, "Location Type", item.location_type);
      }
      if (item.category_name) {
        addCopyLine(lines, "Category", item.category_name);
      }
      if (item.reservation_type) {
        addCopyLine(lines, "Reservation Type", item.reservation_type);
      }
      if (item.gender) {
        addCopyLine(lines, "Gender", item.gender);
      }

      const location = [item.district, item.state_code, item.pincode]
        .filter(Boolean)
        .join(", ");
      if (location) {
        addCopyLine(lines, "Location", location);
      }

      lines.push("");
    });

    await navigator.clipboard.writeText(lines.join("\n"));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  if (insufficientCreditsState) {
    return (
      <div className="rounded-2xl border border-amber-300/70 bg-amber-50 p-5 shadow-sm dark:border-amber-500/30 dark:bg-amber-500/10">
        <div className="flex flex-col gap-4">
          <div className="flex items-start gap-3">
            <div className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-200">
              <AlertTriangle className="h-5 w-5" />
            </div>

            <div className="min-w-0 space-y-2">
              <h2 className="text-sm font-semibold text-amber-900 dark:text-amber-100">
                Insufficient credits
              </h2>
              <p className="text-sm leading-6 text-amber-800 dark:text-amber-100/90">
                {insufficientCreditsState.message}
              </p>
              <p className="text-xs leading-5 text-amber-700 dark:text-amber-200/80">
                You currently have {insufficientCreditsState.availableCredits} credit
                {insufficientCreditsState.availableCredits === 1 ? "" : "s"} available.
                This search requires {insufficientCreditsState.requiredCredits} credit
                {insufficientCreditsState.requiredCredits === 1 ? "" : "s"}.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={onOpenBilling}
              className="inline-flex items-center justify-center gap-2 rounded-2xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm transition hover:opacity-90"
            >
              <Wallet className="h-4 w-4" />
              View plans
            </button>

            <p className="text-xs leading-5 text-amber-700 dark:text-amber-200/80">
              Buy credits to continue with a new College Filter search.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (searchErrorMessage) {
    return (
      <div className="rounded-2xl border border-destructive/30 bg-destructive/10 p-5 shadow-sm">
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-destructive">Search failed</h2>
          <p className="text-sm text-destructive">{searchErrorMessage}</p>
        </div>
      </div>
    );
  }

  if (!searchResponse || !activeVisibleBand) {
    if (isRefreshingResults) {
      return <ResultsPanelSkeleton />;
    }

    return (
      <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <div className="text-sm text-muted-foreground">
          Search results will appear here after the first successful search.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3 xl:flex xl:h-full xl:flex-col">
      <div className="shrink-0 space-y-3">
        {resultsAreStale ? (
          <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-3.5">
            <div className="text-sm font-medium text-amber-700">
              Selections changed after the last search.
            </div>
            <div className="mt-1 text-xs text-amber-700">
              These results reflect the previous successful search until you search again.
            </div>
          </div>
        ) : null}

        {isRefreshingResults ? (
          <PremiumLoader label="Loading the latest results..." />
        ) : null}

        {!isSelectionPanelCollapsed ? (
          <div className="rounded-2xl border border-border cf-soft-surface p-3 shadow-sm">
            <ResultsHeader searchResponse={searchResponse} />
          </div>
        ) : null}

        <div className="flex items-start gap-3 xl:items-center xl:justify-center">
          <div className="min-w-0 flex-1">
            <BandPillSwitcher
              searchResponse={searchResponse}
              activeBand={activeVisibleBand}
              onChangeBand={onChangeBand}
            />
          </div>

          <button
            type="button"
            onClick={() => void handleCopy()}
            className="inline-flex cursor-pointer h-10 shrink-0 items-center gap-2 rounded-xl border border-border bg-background/90 px-3 text-xs font-medium text-foreground transition hover:bg-muted xl:self-center"
            title="Copy colleges on this page"
            aria-label="Copy colleges on this page"
          >
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            <span className="hidden sm:inline">{copied ? "Copied" : "Copy"}</span>
          </button>
        </div>
      </div>

      <div className="min-h-0 xl:flex-1 xl:overflow-y-auto xl:pr-1 xl:cf-panel-scroll">
        <BandResultsPanel
          searchResponse={searchResponse}
          activeBand={activeVisibleBand}
          isLoading={isRefreshingResults || resultsAreStale}
          isSelectionPanelCollapsed={isSelectionPanelCollapsed}
          onPreviousPage={onPreviousPage}
          onNextPage={onNextPage}
        />
      </div>
    </div>
  );
}

function shouldIncludeInstituteCode(item: CollegeCardDTO): boolean {
  return (
    Boolean(item.institute_code?.trim()) &&
    item.exam_code !== "JEE_MAIN" &&
    item.exam_code !== "JEE_ADV"
  );
}

function addCopyLine(lines: string[], label: string, value: string | null | undefined) {
  if (!value || !value.trim()) return;
  lines.push(`   ${label}: ${value}`);
}

function formatMetricValue(value: string, isPercent: boolean): string {
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return isPercent ? `${value}%` : value;
  }

  const normalized =
    Number.isInteger(numeric) ? String(numeric) : String(Number(numeric.toFixed(4)));

  return isPercent ? `${normalized}%` : normalized;
}