"use client";

import { FilterSchemaDTO } from "../../types/contracts";
import { ScoreInputControl } from "./controls/score-input-control";
import { SelectControl } from "./controls/select-control";
import { AutocompleteControl } from "./controls/autocomplete-control";

type FilterControlRendererProps = {
  filter: FilterSchemaDTO;
  value: string;
  metricType: "rank" | "percentile";
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
};

export function FilterControlRenderer({
  filter,
  value,
  metricType,
  options,
  onChange,
}: FilterControlRendererProps) {
  if (filter.filter_key === "score") {
    return (
      <ScoreInputControl
        label={filter.filter_label}
        value={value}
        metricType={metricType}
        onChange={onChange}
      />
    );
  }

  if (filter.control_type === "SELECT") {
    return (
      <SelectControl
        label={filter.filter_label}
        value={value}
        placeholder={`Select ${filter.filter_label.toLowerCase()}`}
        options={options}
        onChange={onChange}
      />
    );
  }

  if (filter.control_type === "AUTOCOMPLETE") {
    return (
      <AutocompleteControl
        label={filter.filter_label}
        value={value}
        placeholder={`Search ${filter.filter_label.toLowerCase()}`}
        options={options}
        onChange={onChange}
      />
    );
  }

  return null;
}