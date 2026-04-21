"use client";

import { ArrowLeft } from "lucide-react";

type OnboardingProgressHeaderProps = {
  currentStep: number;
  totalSteps: number;
  title: string;
  subtitle: string;
  canGoBack: boolean;
  onBack: () => void;
};

export function OnboardingProgressHeader({
  currentStep,
  totalSteps,
  title,
  subtitle,
  canGoBack,
  onBack,
}: OnboardingProgressHeaderProps) {
  const progressPercent = Math.max(
    0,
    Math.min(100, (currentStep / totalSteps) * 100),
  );

  return (
    <div className="w-full">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            disabled={!canGoBack}
            aria-label="Go back"
            className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-border/70 bg-background/80 text-foreground shadow-sm transition hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-40"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>

          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Step {currentStep} of {totalSteps}
            </p>
            <h1 className="mt-1 truncate text-lg font-semibold tracking-tight text-foreground sm:text-xl">
              {title}
            </h1>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <div className="onb-progress-track h-2 w-full overflow-hidden rounded-full">
          <div
            className="onb-progress-fill h-full rounded-full transition-[width] duration-300 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <p className="text-sm leading-6 text-muted-foreground">{subtitle}</p>
      </div>
    </div>
  );
}