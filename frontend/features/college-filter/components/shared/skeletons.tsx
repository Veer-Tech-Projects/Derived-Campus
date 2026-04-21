"use client";

type DynamicFilterPanelSkeletonProps = {
  controlCount?: number;
  showLocationCluster?: boolean;
  showFooterHint?: boolean;
};

type ResultsWorkspaceSkeletonProps = {
  cardCount?: number;
};

export function SelectionPanelSkeleton() {
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <div className="flex items-start gap-3">
          <SkeletonBlock className="h-10 w-10 shrink-0 rounded-2xl" />
          <div className="min-w-0 flex-1 space-y-2 pt-1">
            <SkeletonBlock className="h-5 w-36 rounded-lg" />
            <SkeletonBlock className="h-4 w-full max-w-[220px] rounded-lg" />
            <SkeletonBlock className="h-4 w-40 rounded-lg" />
          </div>
          <SkeletonBlock className="hidden h-8 w-8 rounded-lg xl:block" />
        </div>
      </div>

      <div className="space-y-4 rounded-2xl border border-border bg-card p-5 shadow-sm">
        <div className="space-y-2">
          <SkeletonBlock className="h-4 w-24 rounded-lg" />
          <SkeletonBlock className="h-11 w-full rounded-xl" />
        </div>

        <DynamicFilterPanelSkeleton
          controlCount={5}
          showLocationCluster={true}
          showFooterHint={true}
        />
      </div>
    </div>
  );
}

export function DynamicFilterPanelSkeleton({
  controlCount = 4,
  showLocationCluster = true,
  showFooterHint = true,
}: DynamicFilterPanelSkeletonProps) {
  return (
    <div className="space-y-4 rounded-2xl border border-border bg-card p-5 shadow-sm">
      <div className="space-y-2">
        <SkeletonBlock className="h-5 w-20 rounded-lg" />
        <SkeletonBlock className="h-4 w-full max-w-[280px] rounded-lg" />
        <SkeletonBlock className="h-4 w-48 rounded-lg" />
      </div>

      <div className="space-y-4">
        {Array.from({ length: controlCount }).map((_, index) => (
          <div key={index} className="space-y-2">
            <SkeletonBlock className="h-4 w-24 rounded-lg" />
            <SkeletonBlock className="h-11 w-full rounded-xl" />
          </div>
        ))}

        {showLocationCluster ? (
          <div className="space-y-4 rounded-2xl border border-border bg-card p-4">
            <div className="space-y-2">
              <SkeletonBlock className="h-4 w-20 rounded-lg" />
              <SkeletonBlock className="h-4 w-full max-w-[250px] rounded-lg" />
              <SkeletonBlock className="h-4 w-40 rounded-lg" />
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <SkeletonBlock className="h-4 w-24 rounded-lg" />
                <SkeletonBlock className="h-11 w-full rounded-xl" />
              </div>

              <div className="space-y-2">
                <SkeletonBlock className="h-4 w-28 rounded-lg" />
                <SkeletonBlock className="h-11 w-full rounded-xl" />
              </div>

              <div className="space-y-2">
                <SkeletonBlock className="h-4 w-24 rounded-lg" />
                <SkeletonBlock className="h-11 w-full rounded-xl" />
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {showFooterHint ? (
        <div className="rounded-xl border border-border bg-background p-4">
          <div className="space-y-2">
            <SkeletonBlock className="h-4 w-full rounded-lg" />
            <SkeletonBlock className="h-4 w-4/5 rounded-lg" />
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function ResultsWorkspaceSkeleton({
  cardCount = 2,
}: ResultsWorkspaceSkeletonProps) {
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-border bg-card p-4 shadow-sm sm:p-6">
        <div className="space-y-2">
          <SkeletonBlock className="h-5 w-36 rounded-lg" />
          <SkeletonBlock className="h-4 w-full max-w-[320px] rounded-lg" />
          <SkeletonBlock className="h-4 w-56 rounded-lg" />
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div
              key={index}
              className="rounded-2xl border border-border bg-card p-4 shadow-sm"
            >
              <div className="space-y-2">
                <SkeletonBlock className="h-3 w-16 rounded-lg" />
                <SkeletonBlock className="h-5 w-24 rounded-lg" />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
          <div className="flex-1">
            <div className="grid grid-cols-2 gap-3 sm:flex sm:flex-wrap">
              {Array.from({ length: 4 }).map((_, index) => (
                <SkeletonBlock
                  key={index}
                  className="h-10 w-full rounded-full sm:w-32"
                />
              ))}
            </div>
          </div>

          <SkeletonBlock className="h-10 w-24 rounded-2xl self-end sm:self-auto" />
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        {Array.from({ length: cardCount }).map((_, index) => (
          <div
            key={index}
            className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm"
          >
            <SkeletonBlock className="h-44 w-full rounded-none sm:h-52" />

            <div className="space-y-4 p-4 sm:p-5">
              <div className="space-y-2">
                <SkeletonBlock className="h-6 w-4/5 rounded-lg" />
                <SkeletonBlock className="h-4 w-3/5 rounded-lg" />
              </div>

              <SkeletonBlock className="h-7 w-16 rounded-full" />

              <div className="grid gap-3 sm:grid-cols-2">
                <SkeletonMetricCard />
                <SkeletonMetricCard />
                <SkeletonMetricCard />
              </div>

              <div className="rounded-2xl border border-border bg-background p-4">
                <div className="space-y-2">
                  <SkeletonBlock className="h-4 w-32 rounded-lg" />
                  <SkeletonBlock className="h-4 w-full rounded-lg" />
                  <SkeletonBlock className="h-4 w-11/12 rounded-lg" />
                  <SkeletonBlock className="h-4 w-4/5 rounded-lg" />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function FilterPanelSkeleton() {
  return (
    <DynamicFilterPanelSkeleton
      controlCount={5}
      showLocationCluster={true}
      showFooterHint={true}
    />
  );
}

export function ResultsPanelSkeleton() {
  return <ResultsWorkspaceSkeleton cardCount={2} />;
}

function SkeletonMetricCard() {
  return (
    <div className="rounded-2xl border border-border bg-background p-4">
      <div className="space-y-2">
        <SkeletonBlock className="h-3 w-20 rounded-lg" />
        <SkeletonBlock className="h-5 w-16 rounded-lg" />
      </div>
    </div>
  );
}

function SkeletonBlock({ className }: { className: string }) {
  return <div className={`animate-pulse bg-muted ${className}`} />;
}