import { PathCatalogItemDTO, UUID } from "../types/contracts";

export interface PathCatalogNodeVM extends PathCatalogItemDTO {
  children: PathCatalogNodeVM[];
  is_parent: boolean;
  is_leaf: boolean;
}

export interface EducationTypeGroupVM {
  education_type: string;
  items: PathCatalogNodeVM[];
}

export interface PathCatalogTreeVM {
  roots: PathCatalogNodeVM[];
  byId: Record<string, PathCatalogNodeVM>;
}

function cloneNode(item: PathCatalogItemDTO): PathCatalogNodeVM {
  return {
    ...item,
    children: [],
    is_parent: false,
    is_leaf: true,
  };
}

export function buildPathCatalogTree(items: PathCatalogItemDTO[]): PathCatalogTreeVM {
  const sorted = [...items].sort((a, b) => {
    if (a.display_order !== b.display_order) {
      return a.display_order - b.display_order;
    }

    if (a.visible_label !== b.visible_label) {
      return a.visible_label.localeCompare(b.visible_label);
    }

    return a.path_key.localeCompare(b.path_key);
  });

  const byId: Record<UUID, PathCatalogNodeVM> = {};
  for (const item of sorted) {
    byId[item.path_id] = cloneNode(item);
  }

  const roots: PathCatalogNodeVM[] = [];

  for (const item of sorted) {
    const node = byId[item.path_id];

    if (item.parent_path_id && byId[item.parent_path_id]) {
      byId[item.parent_path_id].children.push(node);
    } else {
      roots.push(node);
    }
  }

  for (const node of Object.values(byId)) {
    node.is_parent = node.children.length > 0;
    node.is_leaf = node.children.length === 0;
  }

  return { roots, byId };
}

/**
 * Returns child rows for a structural parent grouped by DB-driven education_type.
 *
 * Design rules:
 * - no invented grouping labels
 * - only non-empty education_type values become groups
 * - preserve backend ordering through already-sorted child rows
 */
export function buildEducationTypeGroups(
  parentNode: PathCatalogNodeVM | null
): EducationTypeGroupVM[] {
  if (!parentNode || parentNode.children.length === 0) {
    return [];
  }

  const groups = new Map<string, PathCatalogNodeVM[]>();

  for (const child of parentNode.children) {
    const educationType = (child.education_type ?? "").trim();

    if (!educationType) {
      continue;
    }

    const existing = groups.get(educationType) ?? [];
    existing.push(child);
    groups.set(educationType, existing);
  }

  return Array.from(groups.entries()).map(([education_type, items]) => ({
    education_type,
    items,
  }));
}

export function findRootNode(
  tree: PathCatalogTreeVM | null,
  rootPathId: UUID | null
): PathCatalogNodeVM | null {
  if (!tree || !rootPathId) return null;
  return tree.byId[rootPathId] ?? null;
}

export function findFinalPathByEducationTypeAndPathId(
  parentNode: PathCatalogNodeVM | null,
  educationType: string | null,
  finalPathId: UUID | null
): PathCatalogNodeVM | null {
  if (!parentNode || !educationType || !finalPathId) return null;

  return (
    parentNode.children.find(
      (child) =>
        child.path_id === finalPathId &&
        (child.education_type ?? "").trim() === educationType.trim()
    ) ?? null
  );
}