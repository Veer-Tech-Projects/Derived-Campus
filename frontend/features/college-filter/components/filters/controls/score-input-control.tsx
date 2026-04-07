"use client";

type ScoreInputControlProps = {
  label: string;
  value: string;
  metricType: "rank" | "percentile";
  onChange: (value: string) => void;
};

export function ScoreInputControl({
  label,
  value,
  metricType,
  onChange,
}: ScoreInputControlProps) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-foreground">{label}</label>
      <input
        type="number"
        inputMode="decimal"
        min={metricType === "percentile" ? 0 : 1}
        max={metricType === "percentile" ? 100 : undefined}
        step={metricType === "percentile" ? "0.0001" : "1"}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={metricType === "percentile" ? "Enter percentile" : "Enter rank"}
        className="flex h-11 w-full rounded-xl border border-border bg-background px-3 text-sm outline-none transition focus:ring-2 focus:ring-ring"
      />
    </div>
  );
}