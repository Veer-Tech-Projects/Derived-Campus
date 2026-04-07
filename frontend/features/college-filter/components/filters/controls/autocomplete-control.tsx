"use client";

import { useEffect, useMemo, useState } from "react";

type AutocompleteOption = {
  value: string;
  label: string;
};

type AutocompleteControlProps = {
  label: string;
  value: string;
  placeholder: string;
  options: AutocompleteOption[];
  onChange: (value: string) => void;
};

export function AutocompleteControl({
  label,
  value,
  placeholder,
  options,
  onChange,
}: AutocompleteControlProps) {
  const [inputValue, setInputValue] = useState(value);

  useEffect(() => {
    setInputValue(value);
  }, [value]);

  const filteredOptions = useMemo(() => {
    const normalized = inputValue.trim().toLowerCase();

    if (!normalized) {
      return options.slice(0, 50);
    }

    return options
      .filter((option) => option.label.toLowerCase().includes(normalized))
      .slice(0, 50);
  }, [inputValue, options]);

  const commitIfValid = () => {
    const normalizedInput = inputValue.trim().toLowerCase();

    const exactMatch =
      options.find(
        (option) =>
          option.value.trim().toLowerCase() === normalizedInput ||
          option.label.trim().toLowerCase() === normalizedInput
      ) ?? null;

    if (exactMatch) {
      setInputValue(exactMatch.label);
      onChange(exactMatch.value);
      return;
    }

    setInputValue("");
    onChange("");
  };

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-foreground">{label}</label>

      <div className="space-y-2">
        <input
          value={inputValue}
          onChange={(event) => setInputValue(event.target.value)}
          onBlur={commitIfValid}
          placeholder={placeholder}
          className="flex h-11 w-full rounded-xl border border-border bg-background px-3 text-sm outline-none transition focus:ring-2 focus:ring-ring"
        />

        {filteredOptions.length > 0 ? (
          <div className="max-h-48 overflow-auto rounded-xl border border-border bg-background p-2">
            <div className="space-y-1">
              {filteredOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onMouseDown={(event) => {
                    event.preventDefault();
                    setInputValue(option.label);
                    onChange(option.value);
                  }}
                  className="flex w-full items-center rounded-lg px-3 py-2 text-left text-sm text-foreground transition hover:bg-muted"
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}