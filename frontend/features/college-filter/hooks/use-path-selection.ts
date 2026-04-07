import { useMemo } from "react";
import {
  buildEducationTypeGroups,
  findFinalPathByEducationTypeAndPathId,
  findRootNode,
  PathCatalogTreeVM,
} from "../adapters/path-catalog.adapter";
import { UUID } from "../types/contracts";
import { PathSelectionResolution } from "../types/view-models";

interface UsePathSelectionArgs {
  tree: PathCatalogTreeVM | null;
  selectedRootPathId: UUID | null;
  selectedEducationType: string | null;
  selectedFinalPathId: UUID | null;
}

export function usePathSelection({
  tree,
  selectedRootPathId,
  selectedEducationType,
  selectedFinalPathId,
}: UsePathSelectionArgs): PathSelectionResolution {
  return useMemo(() => {
    const rootNode = findRootNode(tree, selectedRootPathId);

    if (!rootNode) {
      return {
        rootPathId: null,
        educationType: null,
        finalPathId: null,
        isStructuralParentSelection: false,
        requiresEducationTypeSelection: false,
        requiresSelectionTypeSelection: false,
        hasResolvedFinalPath: false,
        shouldShowEducationTypeStep: false,
        shouldShowSelectionTypeStep: false,
      };
    }

    if (rootNode.is_leaf) {
      return {
        rootPathId: rootNode.path_id,
        educationType: null,
        finalPathId: rootNode.path_id,
        isStructuralParentSelection: false,
        requiresEducationTypeSelection: false,
        requiresSelectionTypeSelection: false,
        hasResolvedFinalPath: true,
        shouldShowEducationTypeStep: false,
        shouldShowSelectionTypeStep: false,
      };
    }

    const educationGroups = buildEducationTypeGroups(rootNode);
    const hasEducationGroups = educationGroups.length > 0;

    if (!hasEducationGroups) {
      const hasValidFinalPath = Boolean(
        selectedFinalPathId &&
          rootNode.children.some((child) => child.path_id === selectedFinalPathId)
      );

      return {
        rootPathId: rootNode.path_id,
        educationType: null,
        finalPathId: hasValidFinalPath ? selectedFinalPathId : null,
        isStructuralParentSelection: true,
        requiresEducationTypeSelection: false,
        requiresSelectionTypeSelection: !hasValidFinalPath,
        hasResolvedFinalPath: hasValidFinalPath,
        shouldShowEducationTypeStep: false,
        shouldShowSelectionTypeStep: true,
      };
    }

    if (!selectedEducationType) {
      return {
        rootPathId: rootNode.path_id,
        educationType: null,
        finalPathId: null,
        isStructuralParentSelection: true,
        requiresEducationTypeSelection: true,
        requiresSelectionTypeSelection: false,
        hasResolvedFinalPath: false,
        shouldShowEducationTypeStep: true,
        shouldShowSelectionTypeStep: false,
      };
    }

    const selectedGroup = educationGroups.find(
      (group) => group.education_type === selectedEducationType
    );

    if (!selectedGroup) {
      return {
        rootPathId: rootNode.path_id,
        educationType: null,
        finalPathId: null,
        isStructuralParentSelection: true,
        requiresEducationTypeSelection: true,
        requiresSelectionTypeSelection: false,
        hasResolvedFinalPath: false,
        shouldShowEducationTypeStep: true,
        shouldShowSelectionTypeStep: false,
      };
    }

    if (!selectedFinalPathId) {
      return {
        rootPathId: rootNode.path_id,
        educationType: selectedEducationType,
        finalPathId: null,
        isStructuralParentSelection: true,
        requiresEducationTypeSelection: false,
        requiresSelectionTypeSelection: true,
        hasResolvedFinalPath: false,
        shouldShowEducationTypeStep: true,
        shouldShowSelectionTypeStep: true,
      };
    }

    const selectedFinalNode = findFinalPathByEducationTypeAndPathId(
      rootNode,
      selectedEducationType,
      selectedFinalPathId
    );

    if (!selectedFinalNode) {
      return {
        rootPathId: rootNode.path_id,
        educationType: selectedEducationType,
        finalPathId: null,
        isStructuralParentSelection: true,
        requiresEducationTypeSelection: false,
        requiresSelectionTypeSelection: true,
        hasResolvedFinalPath: false,
        shouldShowEducationTypeStep: true,
        shouldShowSelectionTypeStep: true,
      };
    }

    return {
      rootPathId: rootNode.path_id,
      educationType: selectedEducationType,
      finalPathId: selectedFinalNode.path_id,
      isStructuralParentSelection: true,
      requiresEducationTypeSelection: false,
      requiresSelectionTypeSelection: false,
      hasResolvedFinalPath: true,
      shouldShowEducationTypeStep: true,
      shouldShowSelectionTypeStep: true,
    };
  }, [tree, selectedRootPathId, selectedEducationType, selectedFinalPathId]);
}