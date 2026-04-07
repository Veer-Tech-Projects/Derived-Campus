import {
  CollegeFilterMetadataResponse,
  FilterOptionDTO,
  FilterSchemaDTO,
} from "../types/contracts";

export function getVisibleFilters(metadata: CollegeFilterMetadataResponse): FilterSchemaDTO[] {
  return [...metadata.filters]
    .filter((filter) => filter.is_visible)
    .sort((a, b) => a.sort_order - b.sort_order);
}

export function getFilterByKey(
  metadata: CollegeFilterMetadataResponse,
  filterKey: string
): FilterSchemaDTO | undefined {
  return metadata.filters.find((filter) => filter.filter_key === filterKey);
}

export function getSortedOptions(options: FilterOptionDTO[]): FilterOptionDTO[] {
  return [...options].sort((a, b) => {
    const aOrder = a.sort_order ?? Number.MAX_SAFE_INTEGER;
    const bOrder = b.sort_order ?? Number.MAX_SAFE_INTEGER;

    if (aOrder !== bOrder) return aOrder - bOrder;
    return a.label.localeCompare(b.label);
  });
}

export function getDependentFilters(
  metadata: CollegeFilterMetadataResponse,
  parentKey: string
): FilterSchemaDTO[] {
  return metadata.filters
    .filter((filter) => filter.dependency?.depends_on_filter_key === parentKey)
    .sort((a, b) => a.sort_order - b.sort_order);
}