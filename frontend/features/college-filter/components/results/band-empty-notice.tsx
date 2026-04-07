"use client";

import { CollegeBand } from "../../types/contracts";

type BandEmptyNoticeProps = {
  band: CollegeBand;
};

export function BandEmptyNotice({ band }: BandEmptyNoticeProps) {
  return (
    <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
      <div className="space-y-2">
        <h3 className="text-base font-semibold text-foreground">
          No {band} colleges available
        </h3>
        <p className="text-sm text-muted-foreground">
          There are no colleges in the {band} band for your current selections.
          You can switch bands or adjust your filters and search again.
        </p>
      </div>
    </div>
  );
}