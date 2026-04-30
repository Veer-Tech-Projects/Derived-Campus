"use client";

import type { ReactNode } from "react";
import { ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";

type StudentBillingPageShellProps = {
  title: string;
  description: string;
  backHref: string;
  backLabel?: string;
  children: ReactNode;
  headerSlot?: ReactNode;
};

export function StudentBillingPageShell({
  title,
  description,
  backHref,
  backLabel = "Back",
  children,
  headerSlot,
}: StudentBillingPageShellProps) {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-background px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <div className="flex flex-col gap-4">
          <button
            type="button"
            onClick={() => router.push(backHref)}
            className="inline-flex w-fit items-center gap-2 rounded-2xl border border-border bg-card px-4 py-2.5 text-sm font-semibold text-foreground shadow-sm transition-colors hover:bg-secondary"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>{backLabel}</span>
          </button>

          <div className="rounded-[2rem] border border-border bg-card p-5 shadow-sm sm:p-6 lg:p-8">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="max-w-3xl">
                <div className="inline-flex rounded-full border border-border bg-secondary px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                  Student Billing
                </div>

                <h1 className="mt-4 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
                  {title}
                </h1>

                <p className="mt-3 text-sm leading-6 text-muted-foreground sm:text-base">
                  {description}
                </p>
              </div>

              {headerSlot ? (
                <div className="w-full lg:w-auto">{headerSlot}</div>
              ) : null}
            </div>
          </div>
        </div>

        {children}
      </div>
    </div>
  );
}