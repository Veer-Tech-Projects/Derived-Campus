"use client";

type StudentBillingEmptyStateProps = {
  title: string;
  description: string;
};

export function StudentBillingEmptyState({
  title,
  description,
}: StudentBillingEmptyStateProps) {
  return (
    <div className="rounded-[2rem] border border-dashed border-border bg-card p-8 text-center shadow-sm">
      <div className="mx-auto flex max-w-md flex-col items-center gap-3">
        <div className="inline-flex rounded-full border border-border bg-secondary px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">
          Nothing here yet
        </div>
        <h3 className="text-lg font-semibold text-foreground">{title}</h3>
        <p className="text-sm leading-6 text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}