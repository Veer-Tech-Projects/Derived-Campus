"use client";

import {
  buildEducationTypeGroups,
  PathCatalogNodeVM,
} from "../../adapters/path-catalog.adapter";
import { UUID } from "../../types/contracts";

type PathSelectorProps = {
  roots: PathCatalogNodeVM[];
  selectedRootPathId: UUID | null;
  selectedEducationType: string | null;
  selectedFinalPathId: UUID | null;
  onSelectRootPath: (pathId: UUID | null) => void;
  onSelectEducationType: (educationType: string | null) => void;
  onSelectFinalPath: (pathId: UUID | null) => void;
};

export function PathSelector({
  roots,
  selectedRootPathId,
  selectedEducationType,
  selectedFinalPathId,
  onSelectRootPath,
  onSelectEducationType,
  onSelectFinalPath,
}: PathSelectorProps) {
  const selectedRoot =
    roots.find((root) => root.path_id === selectedRootPathId) ?? null;

  const educationTypeGroups = buildEducationTypeGroups(selectedRoot);
  const shouldShowEducationTypeSelector =
    Boolean(selectedRoot && selectedRoot.children.length > 0 && educationTypeGroups.length > 0);

  const selectedEducationGroup =
    educationTypeGroups.find(
      (group) => group.education_type === selectedEducationType
    ) ?? null;

  const rootChildren = selectedRoot?.children ?? [];
  const hasRootChildren = rootChildren.length > 0;

  const selectionTypeOptions = selectedEducationGroup?.items ?? [];

  const shouldShowSelectionTypeSelector =
    hasRootChildren &&
    (
      (shouldShowEducationTypeSelector && Boolean(selectedEducationType)) ||
      !shouldShowEducationTypeSelector
    );

  const fallbackSelectionTypeOptions = !shouldShowEducationTypeSelector
    ? rootChildren
    : selectionTypeOptions;

  return (
    <div className="space-y-4">
      <SelectorField
        id="college-filter-root-path"
        label="Exam Type"
        value={selectedRootPathId ?? ""}
        placeholder="Select exam type"
        options={roots.map((root) => ({
          value: root.path_id,
          label: root.visible_label,
        }))}
        onChange={(value) => {
          onSelectRootPath(value || null);
        }}
      />

      {shouldShowEducationTypeSelector ? (
        <SelectorField
          id="college-filter-education-type"
          label="Education Type"
          value={selectedEducationType ?? ""}
          placeholder="Select education type"
          options={educationTypeGroups.map((group) => ({
            value: group.education_type,
            label: group.education_type,
          }))}
          onChange={(value) => {
            onSelectEducationType(value || null);
          }}
        />
      ) : null}

      {shouldShowSelectionTypeSelector ? (
        <SelectorField
          id="college-filter-selection-type"
          label="Selection Type"
          value={selectedFinalPathId ?? ""}
          placeholder="Select selection type"
          options={fallbackSelectionTypeOptions.map((item) => ({
            value: item.path_id,
            label: item.selection_type?.trim() || item.visible_label,
          }))}
          onChange={(value) => {
            onSelectFinalPath(value || null);
          }}
        />
      ) : null}
    </div>
  );
}

type SelectorFieldProps = {
  id: string;
  label: string;
  value: string;
  placeholder: string;
  options: Array<{
    value: string;
    label: string;
  }>;
  onChange: (value: string) => void;
};

function SelectorField({
  id,
  label,
  value,
  placeholder,
  options,
  onChange,
}: SelectorFieldProps) {
  return (
    <div className="space-y-2">
      <label
        htmlFor={id}
        className="text-sm font-medium text-foreground"
      >
        {label}
      </label>

      <select
        id={id}
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