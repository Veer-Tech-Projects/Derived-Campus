"use client";

type StudentBillingLoadingStateProps = {
  title?: string;
  lines?: number;
};

export function StudentBillingLoadingState({
  title = "Loading billing",
  lines = 4,
}: StudentBillingLoadingStateProps) {
  return (
    <div
      className="rounded-[2rem] border border-border bg-card p-6 shadow-sm"
      aria-busy="true"
      aria-live="polite"
    >
      <div className="animate-pulse space-y-4">
        <div className="h-4 w-32 rounded-full bg-secondary" />
        <div className="h-8 w-56 rounded-full bg-secondary" />
        <div className="space-y-3">
          {Array.from({ length: lines }).map((_, index) => (
            <div
              key={index}
              className="h-4 rounded-full bg-secondary"
              style={{ width: `${92 - index * 8}%` }}
            />
          ))}
        </div>
      </div>
      <span className="sr-only">{title}</span>
    </div>
  );
}