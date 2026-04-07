"use client";

import { useEffect, useMemo } from "react";
import { CollegeFilterMetadataResponse } from "../../types/contracts";
import { useDynamicFilterForm } from "../../hooks/use-dynamic-filter-form";
import { FilterControlRenderer } from "./filter-control-renderer";
import { LocationCluster } from "./location/location-cluster";

type DynamicFilterPanelProps = {
  metadata: CollegeFilterMetadataResponse;
  initialScore?: string;
  initialFilters?: Record<string, string>;
  onFormStateChange?: (payload: {
    score: string;
    filters: Record<string, string>;
    isSearchReady: boolean;
    isFilterStepCompleted: (filterKey: string) => boolean;
  }) => void;
};

export function DynamicFilterPanel({
  metadata,
  initialScore = "",
  initialFilters = {},
  onFormStateChange,
}: DynamicFilterPanelProps) {
  const form = useDynamicFilterForm({
    metadata,
    initialScore,
    initialFilters,
  });

  const stateFilter = form.filterMap.get("state_code") ?? null;
  const districtFilter = form.filterMap.get("district") ?? null;
  const pincodeFilter = form.filterMap.get("pincode") ?? null;

  const stateOptions = stateFilter ? form.getFilteredOptions(stateFilter) : [];
  const districtOptions = districtFilter ? form.getFilteredOptions(districtFilter) : [];

  const locationKeys = new Set(["state_code", "district", "pincode"]);

  const nonLocationFilters = useMemo(() => {
    return form.visibleFilters.filter((filter) => {
      if (locationKeys.has(filter.filter_key)) return false;
      return form.shouldRenderFilter(filter);
    });
  }, [form.visibleFilters, form, locationKeys]);

  useEffect(() => {
    onFormStateChange?.({
      score: form.score,
      filters: form.filters,
      isSearchReady: form.isSearchReady,
      isFilterStepCompleted: form.isStepCompleted,
    });
  }, [
    form.score,
    form.filters,
    form.isSearchReady,
    form.isStepCompleted,
    onFormStateChange,
  ]);
  return (
    <div className="space-y-4 rounded-2xl border border-border bg-card p-5 shadow-sm">
      <div className="space-y-1">
        <h2 className="text-base font-semibold text-foreground">Filters</h2>
        <p className="text-sm text-muted-foreground">
          Complete the required metadata-governed inputs for the selected path.
        </p>
      </div>

      <div className="space-y-4">
        {nonLocationFilters.map((filter) => {
          const options = form.getFilteredOptions(filter).map((option) => ({
            value: option.value,
            label: option.label,
          }));

          const value =
            filter.filter_key === "score"
              ? form.score
              : form.getFilterValue(filter.filter_key);

          return (
            <FilterControlRenderer
              key={filter.filter_key}
              filter={filter}
              value={value}
              metricType={metadata.path.metric_type}
              options={options}
              onChange={(nextValue) => {
                if (filter.filter_key === "score") {
                  form.setScoreValue(nextValue);
                  return;
                }

                form.setFilterValue(filter.filter_key, nextValue);
              }}
            />
          );
        })}

        <LocationCluster
          stateFilter={stateFilter}
          districtFilter={districtFilter}
          pincodeFilter={pincodeFilter}
          stateValue={form.getFilterValue("state_code")}
          districtValue={form.getFilterValue("district")}
          pincodeValue={form.getFilterValue("pincode")}
          stateOptions={stateOptions}
          districtOptions={districtOptions}
          onStateChange={(value) => form.setFilterValue("state_code", value)}
          onDistrictChange={(value) => {
            form.setFilterValue("district", value);
            form.applyDistrictAutofill(value);
          }}
          onPincodeChange={(value) => {
            form.setFilterValue("pincode", value);
            form.applyPincodeAutofill(value);
          }}
        />
      </div>

      <div className="rounded-xl border border-border bg-background p-4 text-sm text-muted-foreground">
        {form.isSearchReady ? (
          "All required inputs are complete. Search can be enabled in the next step."
        ) : !form.scoreValidation.isValid ? (
          "Enter a valid score to enable search."
        ) : form.unmetRequiredFilterKeys.length > 0 ? (
          `Complete the remaining required fields: ${form.unmetRequiredFilterKeys.join(", ")}.`
        ) : (
          "Complete all required fields to enable search."
        )}
      </div>
    </div>
  );
}