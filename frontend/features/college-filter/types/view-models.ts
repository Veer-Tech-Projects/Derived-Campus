import { UUID } from "./contracts";

export interface CollegeFilterPagePathSelection {
  rootPathId: UUID | null;
  educationType: string | null;
  finalPathId: UUID | null;
}

export interface PathSelectionResolution {
  rootPathId: UUID | null;
  educationType: string | null;
  finalPathId: UUID | null;

  isStructuralParentSelection: boolean;
  requiresEducationTypeSelection: boolean;
  requiresSelectionTypeSelection: boolean;
  hasResolvedFinalPath: boolean;

  shouldShowEducationTypeStep: boolean;
  shouldShowSelectionTypeStep: boolean;
}