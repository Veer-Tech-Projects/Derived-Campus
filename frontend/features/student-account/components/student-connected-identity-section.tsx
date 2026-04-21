"use client";

import { ShieldCheck } from "lucide-react";
import type { StudentConnectedIdentityViewModel } from "../types/student-account-view-models";

type StudentConnectedIdentitySectionProps = {
  identity: StudentConnectedIdentityViewModel;
};

export function StudentConnectedIdentitySection({
  identity,
}: StudentConnectedIdentitySectionProps) {
  return (
    <section className="rounded-[2rem] bg-card p-6 shadow-[0_8px_30px_rgba(0,0,0,0.04)] dark:shadow-[0_8px_30px_rgba(0,0,0,0.1)]">
      <div className="mb-6 flex items-center gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[1.1rem] bg-purple-500/10 text-purple-600 dark:bg-purple-500/20 dark:text-purple-400">
          <ShieldCheck className="h-6 w-6" />
        </div>

        <div>
          <h3 className="text-lg font-bold tracking-tight text-foreground">
            Linked provider
          </h3>
          <p className="text-sm text-muted-foreground">
            Your trusted sign-in method.
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row">
        <div className="flex-1 rounded-[1.5rem] bg-secondary/50 p-4">
          <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Provider
          </p>
          <p className="mt-1 text-sm font-bold text-foreground">
            {identity.providerLabel}
          </p>
        </div>

        <div className="flex-[2] rounded-[1.5rem] bg-secondary/50 p-4">
          <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Connected Email
          </p>
          <p className="mt-1 truncate text-sm font-bold text-foreground">
            {identity.email || "—"}
          </p>
        </div>
      </div>
    </section>
  );
}