"use client";

import { FilterSchemaDTO, FilterOptionDTO } from "../../../types/contracts";
import { AutocompleteControl } from "../controls/autocomplete-control";
import { SelectControl } from "../controls/select-control";

type LocationClusterProps = {
  stateFilter: FilterSchemaDTO | null;
  districtFilter: FilterSchemaDTO | null;
  pincodeFilter: FilterSchemaDTO | null;

  stateValue: string;
  districtValue: string;
  pincodeValue: string;

  stateOptions: FilterOptionDTO[];
  districtOptions: FilterOptionDTO[];

  onStateChange: (value: string) => void;
  onDistrictChange: (value: string) => void;
  onPincodeChange: (value: string) => void;
};

export function LocationCluster({
  stateFilter,
  districtFilter,
  pincodeFilter,
  stateValue,
  districtValue,
  pincodeValue,
  stateOptions,
  districtOptions,
  onStateChange,
  onDistrictChange,
  onPincodeChange,
}: LocationClusterProps) {
  if (!stateFilter && !districtFilter && !pincodeFilter) {
    return null;
  }

  return (
    <div className="space-y-4 rounded-2xl border border-border bg-card p-4">
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-foreground">Location</h3>
        <p className="text-xs text-muted-foreground">
          Select state first to view supported districts, or enter pincode directly if known.
        </p>
      </div>

      {stateFilter ? (
        <SelectControl
          label={stateFilter.filter_label}
          value={stateValue}
          placeholder={`Select ${stateFilter.filter_label.toLowerCase()}`}
          options={stateOptions.map((option) => ({
            value: option.value,
            label: option.label,
          }))}
          onChange={onStateChange}
        />
      ) : null}

      {districtFilter && stateValue ? (
        <AutocompleteControl
          label={districtFilter.filter_label}
          value={districtValue}
          placeholder={`Select ${districtFilter.filter_label.toLowerCase()}`}
          options={districtOptions.map((option) => ({
            value: option.value,
            label: option.label,
          }))}
          onChange={onDistrictChange}
        />
      ) : null}

      {pincodeFilter ? (
        <div className="space-y-2">
          <label className="text-sm font-medium text-foreground">
            {pincodeFilter.filter_label}
          </label>
          <input
            type="text"
            inputMode="numeric"
            value={pincodeValue}
            onChange={(event) => onPincodeChange(event.target.value)}
            placeholder={`Enter ${pincodeFilter.filter_label.toLowerCase()}`}
            className="flex h-11 w-full rounded-xl border border-border bg-background px-3 text-sm outline-none transition focus:ring-2 focus:ring-ring"
          />
        </div>
      ) : null}
    </div>
  );
}