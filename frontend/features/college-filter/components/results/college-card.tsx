"use client";

import { useMemo, useState } from "react";
import { CollegeBand, CollegeCardDTO } from "../../types/contracts";

type CollegeCardProps = {
  item: CollegeCardDTO;
};

export function CollegeCard({ item }: CollegeCardProps) {
  const [heroFailed, setHeroFailed] = useState(false);

  const hasLocation = Boolean(item.district || item.state_code || item.pincode);
  const hasOpeningRank = item.opening_rank !== null && item.opening_rank !== undefined;
  const hasBranchDisplayName =
    item.branch_display_name &&
    item.branch_display_name.trim().toLowerCase() !==
      item.program_name.trim().toLowerCase();

  const shouldRenderHero = Boolean(item.hero_media_url) && !heroFailed;

  const toneClass = useMemo(() => {
    const source = item.college_id ?? item.program_code ?? item.college_name;
    const hash =
      Array.from(source).reduce((acc, char) => acc + char.charCodeAt(0), 0) % 5;

    switch (hash) {
      case 0:
        return "cf-card-tone-a";
      case 1:
        return "cf-card-tone-b";
      case 2:
        return "cf-card-tone-c";
      case 3:
        return "cf-card-tone-d";
      default:
        return "cf-card-tone-e";
    }
  }, [item.college_id, item.program_code, item.college_name]);

  return (
    <div
      className={`overflow-hidden rounded-3xl border border-border ${toneClass} shadow-sm transition-all duration-200 hover:shadow-md`}
    >
      <div className="border-b border-border/70 bg-white/12 p-2.5">
        <div className="overflow-hidden rounded-2xl border border-white/55 bg-white/78 shadow-[inset_0_1px_0_rgba(255,255,255,0.55)]">
          {shouldRenderHero ? (
            <div className="aspect-[16/8] overflow-hidden xl:aspect-[16/7]">
              <img
                src={item.hero_media_url!}
                alt={`${item.college_name} campus`}
                className="h-full w-full object-cover object-center"
                loading="lazy"
                onError={() => setHeroFailed(true)}
              />
            </div>
          ) : (
            <div className="flex aspect-[16/8] items-center justify-center px-4 text-center text-sm text-muted-foreground xl:aspect-[16/7]">
              Campus image will appear here
            </div>
          )}
        </div>
      </div>

      <div className="space-y-4 bg-white/10 p-4">
        <div className="space-y-2">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <h3 className="text-[15px] font-semibold leading-snug text-foreground">
                {item.college_name}
              </h3>
              <p className="text-sm text-muted-foreground">{item.program_name}</p>
            </div>

            <div className={[
                "rounded-full border px-3 py-1 text-[11px] font-semibold",
                getCardBandBadgeTone(item.band),
              ].join(" ")}
            >
              {item.band}
            </div>
          </div>

          {hasBranchDisplayName ? (
            <p className="text-sm text-muted-foreground">
              Academic Program: {item.branch_display_name}
            </p>
          ) : null}
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <InfoBlock
            label="Current Cutoff"
            value={formatMetricValue(item.current_round_cutoff_value, false)}
          />
          <InfoBlock
            label="Probability"
            value={formatMetricValue(item.probability_percent, true)}
          />
          {hasOpeningRank ? (
            <InfoBlock label="Opening Rank" value={String(item.opening_rank)} />
          ) : null}
          {hasLocation ? (
            <InfoBlock
              label="Location"
              value={[item.district, item.state_code, item.pincode]
                .filter(Boolean)
                .join(", ")}
            />
          ) : null}
        </div>

        <div className="rounded-2xl border border-border/75 bg-white/88 p-4">
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-foreground">
              System explanation
            </h4>
            <p className="text-sm leading-6 text-muted-foreground">
              {buildExplanation(item)}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function InfoBlock({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-2xl border border-border/75 bg-white/88 p-3.5">
      <div className="text-[10px] font-medium tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-1.5 text-sm font-semibold text-foreground">{value}</div>
    </div>
  );
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

function getCardBandBadgeTone(band: CollegeBand): string {
  switch (band) {
    case "SAFE":
      return "border-emerald-200 bg-emerald-50 text-emerald-800";
    case "MODERATE":
      return "border-amber-200 bg-amber-50 text-amber-800";
    case "HARD":
      return "border-rose-200 bg-rose-50 text-rose-800";
    case "SUGGESTED":
      return "border-violet-200 bg-violet-50 text-violet-800";
  }
}


function buildExplanation(item: CollegeCardDTO): string {
  if (item.band === "SAFE") {
    return "This college currently appears in the SAFE band based on your selected path, score, and the available evidence in the system.";
  }

  if (item.band === "MODERATE") {
    return "This college currently appears in the MODERATE band, meaning it may be achievable but is not as comfortable as the safest options.";
  }

  if (item.band === "HARD") {
    return item.evidence.is_cold_start
      ? "This college currently appears in the HARD band and has limited historical evidence, so it should be treated as a tougher option."
      : "This college currently appears in the HARD band, meaning it is a more competitive option for your current profile.";
  }

  return "This college is shown as a SUGGESTED alternative outside the strongest primary-fit results but still relevant to your broader search.";
}