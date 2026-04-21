"use client";

import type { ReactNode } from "react";

type StudentAccountShellProps = {
  topBar: ReactNode;
  hero: ReactNode;
  children: ReactNode;
};

export function StudentAccountShell({
  topBar,
  hero,
  children,
}: StudentAccountShellProps) {
  return (
    <div className="relative min-h-screen bg-background text-foreground">
      <section className="absolute inset-x-0 top-0 h-[320px] sm:h-[360px] bg-primary rounded-b-[2.5rem] sm:rounded-b-[4rem] shadow-sm">
        <div className="pointer-events-none absolute inset-0 rounded-b-[2.5rem] bg-gradient-to-b from-transparent to-black/10 sm:rounded-b-[4rem]" />
      </section>

      <div className="relative z-10 mx-auto w-full max-w-5xl px-4 pt-4 sm:px-6 sm:pt-8 lg:px-8">
        {topBar}

        <div className="mt-20 sm:mt-24">
          <div className="mx-auto max-w-2xl">{hero}</div>
        </div>

        <div className="mx-auto mt-8 max-w-3xl pb-16">
          <div className="space-y-5 sm:space-y-6">{children}</div>
        </div>
      </div>
    </div>
  );
}