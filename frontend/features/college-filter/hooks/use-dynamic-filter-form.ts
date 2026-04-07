"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CollegeFilterMetadataResponse,
  FilterOptionDTO,
  FilterSchemaDTO,
} from "../types/contracts";

type DynamicFilterValue = string;

export interface DynamicFilterFormState {
  score: string;
  filters: Record<string, DynamicFilterValue>;
}

interface UseDynamicFilterFormArgs {
  metadata: CollegeFilterMetadataResponse | null;
  initialScore?: string;
  initialFilters?: Record<string, string>;
}

function normalizeString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

export function useDynamicFilterForm({
  metadata,
  initialScore = "",
  initialFilters = {},
}: UseDynamicFilterFormArgs) {
  const [score, setScore] = useState(initialScore);
  const [filters, setFilters] = useState<Record<string, DynamicFilterValue>>(initialFilters);

  const visibleFilters = useMemo(() => {
    if (!metadata) return [];
    return [...metadata.filters]
      .filter((filter) => filter.is_visible)
      .sort((a, b) => a.sort_order - b.sort_order);
  }, [metadata]);

  const filterMap = useMemo(() => {
    const map = new Map<string, FilterSchemaDTO>();
    for (const filter of visibleFilters) {
      map.set(filter.filter_key, filter);
    }
    return map;
  }, [visibleFilters]);

  const dependencyChildrenMap = useMemo(() => {
    const map = new Map<string, string[]>();

    for (const filter of visibleFilters) {
      const parentKey = filter.dependency?.depends_on_filter_key;
      if (!parentKey) continue;

      const existing = map.get(parentKey) ?? [];
      existing.push(filter.filter_key);
      map.set(parentKey, existing);
    }

    return map;
  }, [visibleFilters]);

  const collectDescendants = useCallback(
    (parentKey: string): string[] => {
      const visited = new Set<string>();
      const stack = [...(dependencyChildrenMap.get(parentKey) ?? [])];

      while (stack.length > 0) {
        const current = stack.pop();
        if (!current || visited.has(current)) continue;

        visited.add(current);

        const children = dependencyChildrenMap.get(current) ?? [];
        for (const child of children) {
          stack.push(child);
        }
      }

      return Array.from(visited);
    },
    [dependencyChildrenMap]
  );

  const resetForm = useCallback(() => {
    setScore("");
    setFilters({});
  }, []);

  const resetForNewPath = useCallback(() => {
    setScore("");
    setFilters({});
  }, []);

  const setScoreValue = useCallback((value: string) => {
    setScore(value);
  }, []);

  const setFilterValue = useCallback(
    (filterKey: string, value: string) => {
      setFilters((prev) => {
        const next = { ...prev };

        if (normalizeString(value)) {
          next[filterKey] = value;
        } else {
          delete next[filterKey];
        }

        const descendants = collectDescendants(filterKey);
        for (const descendantKey of descendants) {
          delete next[descendantKey];
        }

        /**
         * Special governed UX rules on top of dependency graph:
         * - district cannot survive state changes
         * - pincode may need clearing depending on state/district changes
         * - branch changes always clear variant-like specialization behavior
         */
        if (filterKey === "state_code") {
          delete next["district"];
        }

        if (filterKey === "district") {
          // district change may re-drive pincode later from option metadata
          delete next["pincode"];
        }

        if (filterKey === "branch") {
          delete next["variant"];
        }

        return next;
      });
    },
    [collectDescendants]
  );

  const clearFilterValue = useCallback(
    (filterKey: string) => {
      setFilters((prev) => {
        const next = { ...prev };
        delete next[filterKey];

        const descendants = collectDescendants(filterKey);
        for (const descendantKey of descendants) {
          delete next[descendantKey];
        }

        return next;
      });
    },
    [collectDescendants]
  );

  const getFilterValue = useCallback(
    (filterKey: string): string => {
      return filters[filterKey] ?? "";
    },
    [filters]
  );

  const isDependencySatisfied = useCallback(
    (filter: FilterSchemaDTO): boolean => {
      const parentKey = filter.dependency?.depends_on_filter_key;
      if (!parentKey) return true;

      const parentValue = filters[parentKey];
      return Boolean(normalizeString(parentValue));
    },
    [filters]
  );

  const getFilteredOptions = useCallback(
    (filter: FilterSchemaDTO): FilterOptionDTO[] => {
      const baseOptions = [...filter.options].sort((a, b) => {
        const aOrder = a.sort_order ?? Number.MAX_SAFE_INTEGER;
        const bOrder = b.sort_order ?? Number.MAX_SAFE_INTEGER;

        if (aOrder !== bOrder) return aOrder - bOrder;
        return a.label.localeCompare(b.label);
      });

      if (filter.filter_key === "variant") {
        const selectedBranch = normalizeString(filters["branch"]);
        if (!selectedBranch) {
          return [];
        }

        const filtered = baseOptions.filter((option) => {
          const branchDisciplineKey = normalizeString(
            option.metadata?.branch_discipline_key
          );
          return branchDisciplineKey === selectedBranch;
        });

        return filtered;
      }

      if (filter.filter_key === "district") {
        const selectedState = normalizeString(filters["state_code"]);
        if (!selectedState) {
          return [];
        }

        return baseOptions.filter((option) => {
          const optionState = normalizeString(
            option.metadata?.state_code ?? option.metadata?.state
          );
          return optionState === selectedState;
        });
      }

      return baseOptions;
    },
    [filters]
  );

  const shouldRenderFilter = useCallback(
    (filter: FilterSchemaDTO): boolean => {
      if (!filter.is_visible) return false;

      if (!isDependencySatisfied(filter)) return false;

      /**
       * Variant/specialization must remain hidden unless:
       * - branch is selected
       * - filtered variant options exist for that branch
       */
      if (filter.filter_key === "variant") {
        const options = getFilteredOptions(filter);
        return options.length > 0;
      }

      /**
       * District cannot be shown before state code.
       */
      if (filter.filter_key === "district") {
        const selectedState = normalizeString(filters["state_code"]);
        return Boolean(selectedState);
      }

      return true;
    },
    [filters, getFilteredOptions, isDependencySatisfied]
  );

  const applyDistrictAutofill = useCallback(
    (districtValue: string) => {
      const districtFilter = filterMap.get("district");
      if (!districtFilter) return;

      const districtOptions = getFilteredOptions(districtFilter);
      const matched = districtOptions.find((option) => option.value === districtValue);

      if (!matched) return;

      const pincode = normalizeString(
        matched.metadata?.pincode ?? matched.metadata?.postal_code
      );

      if (!pincode) return;

      setFilters((prev) => ({
        ...prev,
        district: districtValue,
        pincode,
      }));
    },
    [filterMap, getFilteredOptions]
  );

  const applyPincodeAutofill = useCallback(
    (pincodeValue: string) => {
      const stateFilter = filterMap.get("state_code");
      const districtFilter = filterMap.get("district");

      if (!stateFilter || !districtFilter) {
        setFilters((prev) => ({
          ...prev,
          pincode: pincodeValue,
        }));
        return;
      }

      const allDistrictOptions = [...districtFilter.options];
      const matches = allDistrictOptions.filter((option) => {
        const optionPincode = normalizeString(
          option.metadata?.pincode ?? option.metadata?.postal_code
        );
        return optionPincode === normalizeString(pincodeValue);
      });

      if (matches.length === 1) {
        const match = matches[0];
        const stateCode = normalizeString(
          match.metadata?.state_code ?? match.metadata?.state
        );

        setFilters((prev) => {
          const next: Record<string, DynamicFilterValue> = {
            ...prev,
            pincode: pincodeValue,
          };

          if (stateCode) {
            next["state_code"] = stateCode;
          }

          next["district"] = match.value;

          return next;
        });
        return;
      }

      setFilters((prev) => ({
        ...prev,
        pincode: pincodeValue,
      }));
    },
    [filterMap]
  );

  const scoreValidation = useMemo(() => {
    if (!metadata) {
      return {
        isValid: false,
        parsedValue: null as number | null,
      };
    }

    const raw = normalizeString(score);
    if (!raw) {
      return {
        isValid: false,
        parsedValue: null as number | null,
      };
    }

    const parsed = Number(raw);
    if (!Number.isFinite(parsed)) {
      return {
        isValid: false,
        parsedValue: null as number | null,
      };
    }

    if (metadata.path.metric_type === "rank") {
      return {
        isValid: parsed > 0,
        parsedValue: parsed,
      };
    }

    return {
      isValid: parsed > 0 && parsed <= 100,
      parsedValue: parsed,
    };
  }, [metadata, score]);

  const requiredVisibleFilters = useMemo(() => {
    return visibleFilters.filter(
      (filter) => filter.is_required && shouldRenderFilter(filter)
    );
  }, [visibleFilters, shouldRenderFilter]);

  const areRequiredFiltersSatisfied = useMemo(() => {
    return requiredVisibleFilters.every((filter) => {
      if (filter.filter_key === "score") {
        return scoreValidation.isValid;
      }

      const value = normalizeString(filters[filter.filter_key]);
      return Boolean(value);
    });
  }, [filters, requiredVisibleFilters, scoreValidation.isValid]);

  const isSearchReady = useMemo(() => {
    return Boolean(metadata) && scoreValidation.isValid && areRequiredFiltersSatisfied;
  }, [metadata, scoreValidation.isValid, areRequiredFiltersSatisfied]);

  const isStepCompleted = useCallback(
    (filterKey: string): boolean => {
      if (filterKey === "score") {
        return scoreValidation.isValid;
      }

      return Boolean(normalizeString(filters[filterKey]));
    },
    [filters, scoreValidation.isValid]
  );

  const unmetRequiredFilterKeys = useMemo(() => {
    return requiredVisibleFilters
      .filter((filter) => {
        if (filter.filter_key === "score") {
          return !scoreValidation.isValid;
        }

        const value = normalizeString(filters[filter.filter_key]);
        return !value;
      })
      .map((filter) => filter.filter_key);
  }, [filters, requiredVisibleFilters, scoreValidation.isValid]);

  return {
    score,
    filters,
    visibleFilters,
    filterMap,
    scoreValidation,
    isSearchReady,
    unmetRequiredFilterKeys,
    setScoreValue,
    setFilterValue,
    clearFilterValue,
    getFilterValue,
    getFilteredOptions,
    shouldRenderFilter,
    isDependencySatisfied,
    isStepCompleted,
    applyDistrictAutofill,
    applyPincodeAutofill,
    resetForm,
    resetForNewPath,
  };
}