"use client";

import Image from "next/image";
import { CollegeBand } from "../../types/contracts";

type BandEmptyNoticeProps = {
  band: CollegeBand;
};

const EMPTY_BAND_ILLUSTRATION_SRC =
  "/illustrations/college-filter/no-band-results.svg";

export function BandEmptyNotice({ band }: BandEmptyNoticeProps) {
  return (
    <div className="flex w-full flex-col overflow-hidden rounded-3xl border border-border bg-card p-6 shadow-sm sm:p-10 lg:p-12">
      
      {/* 1. Typography & Messaging Layer (Top, Left-aligned) */}
      <div className="flex w-full max-w-2xl flex-col items-start space-y-4">
        <div className="inline-flex items-center rounded-full border border-border/50 bg-muted/50 px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground shadow-sm">
          {band} Band
        </div>

        <div className="space-y-2.5 text-left">
          <h3 className="text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
            No colleges found for this band
          </h3>

          <p className="text-sm leading-relaxed text-muted-foreground sm:text-[15px]">
            There are currently no colleges in the{" "}
            <span className="font-medium text-foreground">{band}</span> band for
            your selected preferences. You can switch bands or refine your filters
            and search again to explore more relevant matches.
          </p>
        </div>
      </div>

      {/* 2. Illustration Layer (Bottom, Centered) */}
      <div className="mt-10 flex w-full flex-1 items-end justify-center sm:mt-12 lg:mt-16">
        <div className="relative flex h-56 w-full max-w-[260px] items-center justify-center sm:h-64 sm:max-w-[320px] lg:h-80 lg:max-w-[400px]">
          {/* Ambient theme-aware glow */}
          <div className="pointer-events-none absolute inset-0 scale-110 rounded-full bg-primary/5 blur-3xl dark:bg-primary/10" />
          <Image
            src={EMPTY_BAND_ILLUSTRATION_SRC}
            alt={`No colleges found in ${band} band`}
            fill
            className="object-contain drop-shadow-sm transition-opacity duration-300 dark:opacity-90"
            priority={false}
          />
        </div>
      </div>

    </div>
  );
}