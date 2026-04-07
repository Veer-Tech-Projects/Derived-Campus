"use client";

type SelectOption = {
  value: string;
  label: string;
};

type SelectControlProps = {
  label: string;
  value: string;
  placeholder: string;
  options: SelectOption[];
  onChange: (value: string) => void;
};

export function SelectControl({
  label,
  value,
  placeholder,
  options,
  onChange,
}: SelectControlProps) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-foreground">{label}</label>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="flex h-11 w-full rounded-xl border border-border bg-background px-3 text-sm outline-none transition focus:ring-2 focus:ring-ring"
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}