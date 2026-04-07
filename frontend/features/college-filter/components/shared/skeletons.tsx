"use client";

export function FilterPanelSkeleton() {
  return (
    <div className="space-y-4 rounded-2xl border border-border bg-card p-5 shadow-sm">
      <SkeletonLine className="h-5 w-32" />
      <SkeletonLine className="h-4 w-64" />

      <div className="space-y-4 pt-2">
        {Array.from({ length: 5 }).map((_, index) => (
          <div key={index} className="space-y-2">
            <SkeletonLine className="h-4 w-24" />
            <SkeletonLine className="h-11 w-full rounded-xl" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function ResultsPanelSkeleton() {
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <SkeletonLine className="h-5 w-28" />
        <SkeletonLine className="mt-3 h-4 w-80" />
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          <SkeletonLine className="h-4 w-full" />
          <SkeletonLine className="h-4 w-full" />
          <SkeletonLine className="h-4 w-full" />
          <SkeletonLine className="h-4 w-full" />
        </div>
      </div>

      <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
        <div className="flex flex-wrap gap-3">
          {Array.from({ length: 4 }).map((_, index) => (
            <SkeletonLine key={index} className="h-10 w-28 rounded-full" />
          ))}
        </div>
      </div>

      {Array.from({ length: 2 }).map((_, index) => (
        <div
          key={index}
          className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm"
        >
          <SkeletonLine className="h-40 w-full rounded-none" />
          <div className="space-y-4 p-5">
            <SkeletonLine className="h-5 w-56" />
            <SkeletonLine className="h-4 w-40" />
            <div className="grid gap-3 sm:grid-cols-2">
              <SkeletonLine className="h-20 w-full rounded-xl" />
              <SkeletonLine className="h-20 w-full rounded-xl" />
            </div>
            <SkeletonLine className="h-24 w-full rounded-xl" />
          </div>
        </div>
      ))}
    </div>
  );
}

function SkeletonLine({ className }: { className: string }) {
  return <div className={`animate-pulse bg-muted ${className}`} />;
}