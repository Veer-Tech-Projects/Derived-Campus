"use client";

export function PremiumLoader({ label }: { label: string }) {
  return (
    <div className="rounded-2xl border border-blue-500/30 bg-blue-500/10 p-4 text-sm text-blue-700">
      <div className="flex items-center gap-3">
        <span className="relative inline-flex h-3 w-3">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-75" />
          <span className="relative inline-flex h-3 w-3 rounded-full bg-current" />
        </span>
        <span>{label}</span>
      </div>
    </div>
  );
}