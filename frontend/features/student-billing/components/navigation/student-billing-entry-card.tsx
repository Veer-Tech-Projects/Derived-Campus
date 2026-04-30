"use client";

import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { ArrowRight } from "lucide-react";

type StudentBillingEntryCardProps = {
  href: string;
  title: string;
  description: string;
  icon: LucideIcon;
};

export function StudentBillingEntryCard({
  href,
  title,
  description,
  icon: Icon,
}: StudentBillingEntryCardProps) {
  return (
    <Link
      href={href}
      className="group rounded-[2rem] border border-border bg-card p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md sm:p-6"
    >
      <div className="flex h-full flex-col gap-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <Icon className="h-6 w-6" />
          </div>

          <div className="flex h-10 w-10 items-center justify-center rounded-full border border-border text-muted-foreground transition-colors group-hover:border-primary/30 group-hover:text-primary">
            <ArrowRight className="h-4 w-4" />
          </div>
        </div>

        <div>
          <h3 className="text-lg font-semibold text-foreground">{title}</h3>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {description}
          </p>
        </div>
      </div>
    </Link>
  );
}