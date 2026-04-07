"use client";

import { CollegeFilterSearchResponse } from "../../types/contracts";

type ResultsHeaderProps = {
  searchResponse: CollegeFilterSearchResponse;
};

export function ResultsHeader({ searchResponse }: ResultsHeaderProps) {
  return (
    <div className="space-y-2.5">
      <div className="space-y-0.5">
        <h2 className="text-sm font-semibold text-foreground">Results Overview</h2>
        <p className="text-[11px] leading-5 text-muted-foreground">
          Fit bands are calculated from your selected exam type and current inputs.
        </p>
      </div>

      <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
        <MetricTile label="EXAM TYPE" value={searchResponse.path.visible_label} />
        <MetricTile label="CUTOFF TYPE" value={capitalize(searchResponse.path.metric_type)} />
        <MetricTile label="YOUR SCORE" value={formatMetricValue(searchResponse.user_score)} />
        <MetricTile
          label="TOTAL MATCHES"
          value={String(searchResponse.total_matching_count)}
        />
      </div>
    </div>
  );
}

function MetricTile({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-background/92 px-3 py-2.5">
      <div className="text-[10px] font-medium tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-sm font-semibold text-foreground">{value}</div>
    </div>
  );
}

function formatMetricValue(value: string): string {
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return value;
  return Number.isInteger(numeric)
    ? String(numeric)
    : String(Number(numeric.toFixed(4)));
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}