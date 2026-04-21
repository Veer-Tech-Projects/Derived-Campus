"use client";

import type { ReactNode } from "react";

type OnboardingContentPanelProps = {
  children: ReactNode;
  className?: string;
};

export function OnboardingContentPanel({
  children,
  className = "",
}: OnboardingContentPanelProps) {
  return (
    <div
      className={[
        "onb-panel relative w-full rounded-[2rem] border border-border/70 bg-card/95 shadow-[0_20px_60px_rgba(0,0,0,0.10)] backdrop-blur-sm",
        "p-5 sm:p-6 lg:p-7",
        className,
      ].join(" ")}
    >
      {children}
    </div>
  );
}