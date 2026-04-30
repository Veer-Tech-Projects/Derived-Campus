"use client";

import type { ReactNode } from "react";

type StudentBillingProcessingShellProps = {
  eyebrow: string;
  title: string;
  description: string;
  orderRef?: string | null;
  children: ReactNode;
};

export function StudentBillingProcessingShell({
  eyebrow,
  title,
  description,
  orderRef,
  children,
}: StudentBillingProcessingShellProps) {
  return (
    <div className="min-h-screen bg-background px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-3xl items-center justify-center">
        <div className="w-full rounded-[2rem] border border-border bg-card p-6 shadow-sm sm:p-8 lg:p-10">
          <div className="mb-8">
            <div className="inline-flex rounded-full border border-border bg-secondary px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">
              {eyebrow}
            </div>

            <h1 className="mt-4 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
              {title}
            </h1>

            <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground sm:text-base">
              {description}
            </p>

            {orderRef ? (
              <p className="mt-4 break-all text-xs text-muted-foreground">
                Order reference: {orderRef}
              </p>
            ) : null}
          </div>

          {children}
        </div>
      </div>
    </div>
  );
}