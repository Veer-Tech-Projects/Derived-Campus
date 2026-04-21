"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  SlidersHorizontal,
} from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { normalizeApiError } from "../../api/student-public-client";
import {
  buildCollegeFilterSearchRequest,
  COLLEGE_FILTER_DEFAULT_BAND_PAGES,
} from "../../adapters/search-request.adapter";
import { DynamicFilterPanel } from "../filters/dynamic-filter-panel";
import { PathSelector } from "../path/path-selector";
import { FollowStepsPanel } from "../guidance/follow-steps-panel";
import { SearchActionBar } from "../actions/search-action-bar";
import { SearchStatusPanel } from "../results/search-status-panel";
import { usePathCatalogQuery } from "../../hooks/use-path-catalog-query";
import { useCollegeFilterMetadataQuery } from "../../hooks/use-college-filter-metadata-query";
import { useCollegeFilterSearchQuery } from "../../hooks/use-college-filter-search-query";
import { usePathSelection } from "../../hooks/use-path-selection";
import { useFollowStepsVisibility } from "../../hooks/use-follow-steps";
import { useCollegeFilterUiStore } from "../../state/use-college-filter-ui-store";
import {
  DynamicFilterPanelSkeleton,
  SelectionPanelSkeleton,
} from "../shared/skeletons";
import {
  decodeCollegeFilterUrlState,
  encodeCollegeFilterUrlState,
  type CollegeFilterUrlState,
} from "../../state/url-codec";
import {
  BandPageRequest,
  CollegeBand,
  CollegeFilterSearchRequest,
  CollegeFilterSearchResponse,
  UUID,
} from "../../types/contracts";

function buildStableRequestKey(payload: CollegeFilterSearchRequest): string {
  const normalizedFilters = Object.keys(payload.filters)
    .sort()
    .reduce<Record<string, string>>((acc, key) => {
      const rawValue = payload.filters[key];
      const normalizedKey = key.trim();

      if (!normalizedKey) {
        return acc;
      }

      const value =
        typeof rawValue === "string" ? rawValue : String(rawValue ?? "");
      const normalizedValue = value.trim();

      if (!normalizedValue) {
        return acc;
      }

      acc[normalizedKey] = normalizedValue;
      return acc;
    }, {});

  return JSON.stringify({
    path_id: payload.path_id,
    score: payload.score.trim(),
    filters: normalizedFilters,
    sort_mode: payload.sort_mode,
    page_by_band: {
      safe: payload.page_by_band.safe,
      moderate: payload.page_by_band.moderate,
      hard: payload.page_by_band.hard,
      suggested: payload.page_by_band.suggested,
    },
    page_size: payload.page_size,
  });
}

export function CollegeFilterPageShell() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const decodedUrlState = useMemo(
    () => decodeCollegeFilterUrlState(searchParams),
    [searchParams]
  );

  const hasHydratedFromUrlRef = useRef(false);
  const hasRestoredAppliedSearchRef = useRef(false);
  const activeRequestKeyRef = useRef<string | null>(null);
  const latestIssuedRequestIdRef = useRef(0);
  const latestCommittedRequestIdRef = useRef(0);

  const [selectedRootPathId, setSelectedRootPathId] = useState<UUID | null>(null);
  const [selectedEducationType, setSelectedEducationType] = useState<string | null>(null);
  const [selectedFinalPathId, setSelectedFinalPathId] = useState<UUID | null>(null);

  const [draftScore, setDraftScore] = useState("");
  const [draftFilters, setDraftFilters] = useState<Record<string, string>>({});
  const [isSelectionPanelCollapsed, setIsSelectionPanelCollapsed] = useState(false);

  const [formSnapshot, setFormSnapshot] = useState<{
    score: string;
    filters: Record<string, string>;
    isSearchReady: boolean;
    isFilterStepCompleted: (filterKey: string) => boolean;
  } | null>(null);

  const [searchResponse, setSearchResponse] =
    useState<CollegeFilterSearchResponse | null>(null);
  const [searchErrorMessage, setSearchErrorMessage] = useState<string | null>(null);
  const [lastExecutedSearchFingerprint, setLastExecutedSearchFingerprint] =
    useState<string | null>(null);
  const [pageByBand, setPageByBand] = useState<BandPageRequest>(
    COLLEGE_FILTER_DEFAULT_BAND_PAGES
  );
  const [appliedSearchState, setAppliedSearchState] =
    useState<CollegeFilterUrlState | null>(null);

  const {
    data: pathCatalogData,
    isLoading: isPathCatalogLoading,
    isError: isPathCatalogError,
  } = usePathCatalogQuery();

  const pathTree = pathCatalogData?.tree ?? null;
  const roots = pathTree?.roots ?? [];

  const hasExecutedSearch = useCollegeFilterUiStore((state) => state.hasExecutedSearch);
  const resultsAreStale = useCollegeFilterUiStore((state) => state.resultsAreStale);
  const activeVisibleBand = useCollegeFilterUiStore((state) => state.activeVisibleBand);
  const markSearchExecuted = useCollegeFilterUiStore((state) => state.markSearchExecuted);
  const markFiltersEditedAfterSearch = useCollegeFilterUiStore(
    (state) => state.markFiltersEditedAfterSearch
  );
  const setHasExecutedSearch = useCollegeFilterUiStore((state) => state.setHasExecutedSearch);
  const setResultsAreStale = useCollegeFilterUiStore((state) => state.setResultsAreStale);
  const setActiveVisibleBand = useCollegeFilterUiStore((state) => state.setActiveVisibleBand);

  const searchMutation = useCollegeFilterSearchQuery();

  const resetSearchWorkspaceState = useCallback(() => {
    setDraftScore("");
    setDraftFilters({});
    setFormSnapshot(null);
    setSearchResponse(null);
    setSearchErrorMessage(null);
    setLastExecutedSearchFingerprint(null);
    setAppliedSearchState(null);
    setPageByBand(COLLEGE_FILTER_DEFAULT_BAND_PAGES);
    setActiveVisibleBand(null);
    setHasExecutedSearch(false);
    setResultsAreStale(false);
    hasRestoredAppliedSearchRef.current = false;
  }, [setActiveVisibleBand, setHasExecutedSearch, setResultsAreStale]);

  useEffect(() => {
    if (hasHydratedFromUrlRef.current) return;

    setSelectedRootPathId(decodedUrlState.rootPathId);
    setSelectedEducationType(decodedUrlState.educationType);
    setSelectedFinalPathId(decodedUrlState.finalPathId);
    setDraftScore(decodedUrlState.score);
    setDraftFilters(decodedUrlState.filters);
    setPageByBand(decodedUrlState.pageByBand);

    if (decodedUrlState.activeBand) {
      setActiveVisibleBand(decodedUrlState.activeBand);
    }

    if (decodedUrlState.applied && decodedUrlState.finalPathId) {
      setAppliedSearchState(decodedUrlState);
      setHasExecutedSearch(true);
      setLastExecutedSearchFingerprint(
        JSON.stringify({
          finalPathId: decodedUrlState.finalPathId,
          score: decodedUrlState.score,
          filters: decodedUrlState.filters,
        })
      );
    } else {
      setAppliedSearchState(null);
      setHasExecutedSearch(false);
    }

    setResultsAreStale(false);
    hasHydratedFromUrlRef.current = true;
  }, [
    decodedUrlState,
    setActiveVisibleBand,
    setHasExecutedSearch,
    setResultsAreStale,
  ]);

  const selection = usePathSelection({
    tree: pathTree,
    selectedRootPathId,
    selectedEducationType,
    selectedFinalPathId,
  });

  const {
    data: metadataData,
    isLoading: isMetadataLoading,
    isError: isMetadataError,
  } = useCollegeFilterMetadataQuery(selection.finalPathId);

  const { shouldShowFollowSteps } = useFollowStepsVisibility({
    hasExecutedSearch,
    hasRenderableResults: false,
  });

  const handleFormStateChange = useCallback(
    (payload: {
      score: string;
      filters: Record<string, string>;
      isSearchReady: boolean;
      isFilterStepCompleted: (filterKey: string) => boolean;
    }) => {
      setDraftScore(payload.score);
      setDraftFilters(payload.filters);
      setFormSnapshot(payload);
    },
    []
  );

  useEffect(() => {
    if (!pathTree || !selectedRootPathId) return;

    const selectedRootNode = pathTree.byId[selectedRootPathId];

    if (!selectedRootNode || selectedRootNode.is_leaf) {
      setSelectedEducationType(null);
      setSelectedFinalPathId(selectedRootNode?.path_id ?? null);
      return;
    }

    const rootChildren = selectedRootNode.children;

    const hasMatchingEducationType =
      selectedEducationType &&
      rootChildren.some(
        (child) => (child.education_type ?? "").trim() === selectedEducationType.trim()
      );

    if (!hasMatchingEducationType) {
      setSelectedEducationType(null);
      setSelectedFinalPathId(null);
      return;
    }

    const hasMatchingFinalPath =
      selectedFinalPathId &&
      rootChildren.some(
        (child) =>
          child.path_id === selectedFinalPathId &&
          (child.education_type ?? "").trim() === selectedEducationType.trim()
      );

    if (!hasMatchingFinalPath) {
      setSelectedFinalPathId(null);
    }
  }, [pathTree, selectedRootPathId, selectedEducationType, selectedFinalPathId]);

  const resolvedVisibleFilters = metadataData?.visibleFilters ?? [];

  const currentSearchFingerprint = useMemo(() => {
    return JSON.stringify({
      finalPathId: selection.finalPathId,
      score: draftScore,
      filters: draftFilters,
    });
  }, [selection.finalPathId, draftScore, draftFilters]);

  useEffect(() => {
    if (!hasExecutedSearch || !lastExecutedSearchFingerprint) return;

    if (currentSearchFingerprint === lastExecutedSearchFingerprint) {
      setResultsAreStale(false);
      return;
    }

    markFiltersEditedAfterSearch();
  }, [
    currentSearchFingerprint,
    hasExecutedSearch,
    lastExecutedSearchFingerprint,
    markFiltersEditedAfterSearch,
    setResultsAreStale,
  ]);

  useEffect(() => {
    if (!hasExecutedSearch || !resultsAreStale) return;
    setPageByBand(COLLEGE_FILTER_DEFAULT_BAND_PAGES);
  }, [hasExecutedSearch, resultsAreStale]);

  const isCurrentDraftApplied = useMemo(() => {
    if (!hasExecutedSearch) return false;
    if (!appliedSearchState?.applied) return false;
    if (!lastExecutedSearchFingerprint) return false;

    return currentSearchFingerprint === lastExecutedSearchFingerprint;
  }, [
    appliedSearchState,
    currentSearchFingerprint,
    hasExecutedSearch,
    lastExecutedSearchFingerprint,
  ]);

  const executeGuardedSearch = useCallback(
    async ({
      payload,
      onSuccess,
      onError,
    }: {
      payload: CollegeFilterSearchRequest;
      onSuccess: (result: Awaited<ReturnType<typeof searchMutation.mutateAsync>>, requestId: number) => void;
      onError: (message: string, requestId: number) => void;
    }) => {
      const requestKey = buildStableRequestKey(payload);

      if (activeRequestKeyRef.current === requestKey) {
        return;
      }

      const requestId = ++latestIssuedRequestIdRef.current;
      activeRequestKeyRef.current = requestKey;

      try {
        const result = await searchMutation.mutateAsync(payload);

        if (requestId !== latestIssuedRequestIdRef.current) {
          return;
        }

        latestCommittedRequestIdRef.current = requestId;
        onSuccess(result, requestId);
      } catch (error) {
        if (requestId !== latestIssuedRequestIdRef.current) {
          return;
        }

        onError(normalizeApiError(error), requestId);
      } finally {
        if (activeRequestKeyRef.current === requestKey) {
          activeRequestKeyRef.current = null;
        }
      }
    },
    [searchMutation]
  );

  useEffect(() => {
    if (!hasHydratedFromUrlRef.current) return;
    if (hasRestoredAppliedSearchRef.current) return;
    if (!appliedSearchState?.applied || !appliedSearchState.finalPathId) return;

    const appliedFinalPathId = appliedSearchState.finalPathId;
    const appliedScore = appliedSearchState.score;
    const appliedFilters = appliedSearchState.filters;  
    const appliedPageByBand = appliedSearchState.pageByBand;
    const appliedActiveBand = appliedSearchState.activeBand;

    if (selection.finalPathId !== appliedFinalPathId) return;

    hasRestoredAppliedSearchRef.current = true;
    setSearchErrorMessage(null);

    const payload = buildCollegeFilterSearchRequest({
      finalPathId: appliedFinalPathId,
      score: appliedScore,
      filters: appliedFilters,
      pageByBand: appliedPageByBand,
    });

    void executeGuardedSearch({
      payload,
      onSuccess: (result) => {
        setSearchResponse(result.response);
        setPageByBand(appliedPageByBand);
        setActiveVisibleBand(appliedActiveBand ?? result.resolvedDefaultBand);
        markSearchExecuted();
        setResultsAreStale(false);
      },
      onError: (message) => {
        setSearchErrorMessage(message);
      },
    });
  }, [
    appliedSearchState,
    executeGuardedSearch,
    markSearchExecuted,
    selection.finalPathId,
    setActiveVisibleBand,
    setResultsAreStale,
  ]);

  const urlStateForSync = useMemo<CollegeFilterUrlState>(() => {
    const liveDraftState: CollegeFilterUrlState = {
      rootPathId: selectedRootPathId,
      educationType: selectedEducationType,
      finalPathId: selection.finalPathId ?? selectedFinalPathId,
      score: draftScore,
      filters: draftFilters,
      activeBand: null,
      pageByBand: COLLEGE_FILTER_DEFAULT_BAND_PAGES,
      applied: false,
    };

    if (!isCurrentDraftApplied || !appliedSearchState) {
      return liveDraftState;
    }

    return {
      ...liveDraftState,
      activeBand: appliedSearchState.activeBand,
      pageByBand: appliedSearchState.pageByBand,
      applied: true,
    };
  }, [
    appliedSearchState,
    draftFilters,
    draftScore,
    isCurrentDraftApplied,
    selectedEducationType,
    selectedFinalPathId,
    selectedRootPathId,
    selection.finalPathId,
  ]);

  const encodedUrl = useMemo(() => {
    return encodeCollegeFilterUrlState(urlStateForSync).toString();
  }, [urlStateForSync]);

  const currentSearchParamsString = searchParams.toString();

  useEffect(() => {
    if (!hasHydratedFromUrlRef.current) return;
    if (currentSearchParamsString === encodedUrl) return;

    const nextUrl = encodedUrl ? `${pathname}?${encodedUrl}` : pathname;
    router.replace(nextUrl, { scroll: false });
  }, [currentSearchParamsString, encodedUrl, pathname, router]);


  const handleSearch = useCallback(async () => {
    if (!selection.finalPathId || !formSnapshot?.isSearchReady) return;

    setSearchErrorMessage(null);

    const freshPageByBand = COLLEGE_FILTER_DEFAULT_BAND_PAGES;
    setPageByBand(freshPageByBand);

    const payload = buildCollegeFilterSearchRequest({
      finalPathId: selection.finalPathId,
      score: formSnapshot.score,
      filters: formSnapshot.filters,
      pageByBand: freshPageByBand,
    });

    void executeGuardedSearch({
      payload,
      onSuccess: (result) => {
        const nextActiveBand = result.resolvedDefaultBand;

        const nextAppliedState: CollegeFilterUrlState = {
          rootPathId: selectedRootPathId,
          educationType: selectedEducationType,
          finalPathId: selection.finalPathId,
          score: formSnapshot.score,
          filters: formSnapshot.filters,
          activeBand: nextActiveBand,
          pageByBand: freshPageByBand,
          applied: true,
        };

        setSearchResponse(result.response);
        setActiveVisibleBand(nextActiveBand);
        setAppliedSearchState(nextAppliedState);
        setLastExecutedSearchFingerprint(
          JSON.stringify({
            finalPathId: selection.finalPathId,
            score: formSnapshot.score,
            filters: formSnapshot.filters,
          })
        );
        markSearchExecuted();
        setResultsAreStale(false);
      },
      onError: (message) => {
        setSearchErrorMessage(message);
      },
    });
  }, [
    executeGuardedSearch,
    formSnapshot,
    markSearchExecuted,
    selectedEducationType,
    selectedRootPathId,
    selection.finalPathId,
    setActiveVisibleBand,
    setResultsAreStale,
  ]);

  const handleBandPageChange = useCallback(
    async (band: CollegeBand, direction: "previous" | "next") => {
      if (resultsAreStale) return;
      if (!appliedSearchState?.applied || !appliedSearchState.finalPathId || !searchResponse) return;

      const bandKey = band.toLowerCase() as keyof BandPageRequest;
      const currentPage = pageByBand[bandKey];
      const nextPage =
        direction === "next" ? currentPage + 1 : Math.max(1, currentPage - 1);

      if (nextPage === currentPage) return;

      const nextPageByBand: BandPageRequest = {
        ...pageByBand,
        [bandKey]: nextPage,
      };

      setSearchErrorMessage(null);

      const payload = buildCollegeFilterSearchRequest({
        finalPathId: appliedSearchState.finalPathId,
        score: appliedSearchState.score,
        filters: appliedSearchState.filters,
        pageByBand: nextPageByBand,
      });

      void executeGuardedSearch({
        payload,
        onSuccess: (result) => {
          const nextAppliedState: CollegeFilterUrlState = {
            ...appliedSearchState,
            activeBand: band,
            pageByBand: nextPageByBand,
            applied: true,
          };

          setPageByBand(nextPageByBand);
          setSearchResponse(result.response);
          setActiveVisibleBand(band);
          setAppliedSearchState(nextAppliedState);
          setLastExecutedSearchFingerprint(
            JSON.stringify({
              finalPathId: appliedSearchState.finalPathId,
              score: appliedSearchState.score,
              filters: appliedSearchState.filters,
            })
          );
          markSearchExecuted();
          setResultsAreStale(false);
        },
        onError: (message) => {
          setSearchErrorMessage(message);
        },
      });
    },
    [
      appliedSearchState,
      executeGuardedSearch,
      markSearchExecuted,
      pageByBand,
      resultsAreStale,
      searchResponse,
      setActiveVisibleBand,
      setResultsAreStale,
    ]
  );

  return (
    <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-3 px-2.5 py-2.5 md:px-4 lg:px-5">
      <div
        className={[
          "grid gap-3 xl:h-[calc(100vh-1.25rem)]",
          isSelectionPanelCollapsed
            ? "xl:grid-cols-[84px_minmax(0,1fr)]"
            : "xl:grid-cols-[320px_minmax(0,1fr)]",
        ].join(" ")}
      >
        <section className="relative min-h-0 rounded-3xl border border-border bg-card shadow-sm xl:flex xl:flex-col xl:overflow-hidden">
          <div
            className={[
              "px-4 py-3",
              isSelectionPanelCollapsed ? "" : "border-b border-border",
            ].join(" ")}
          >
            {!isSelectionPanelCollapsed ? (
              <div className="flex items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-primary/12 text-primary">
                    <SlidersHorizontal className="h-4.5 w-4.5" />
                  </div>

                  <div className="min-w-0 space-y-1">
                    <h2 className="text-base font-semibold text-foreground">
                      College Filter Tool
                    </h2>
                    <p className="text-xs leading-5 text-muted-foreground">
                      Select your exam flow and complete the required details.
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  title="Collapse selection panel"
                  aria-label="Collapse selection panel"
                  onClick={() => setIsSelectionPanelCollapsed(true)}
                  className="hidden xl:inline-flex cursor-pointer h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-border bg-background/80 text-muted-foreground transition hover:bg-muted hover:text-foreground"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <>
                {/* 1. Mobile/Tablet View (< xl): Horizontal Logo + Text + Bottom Divider */}
                <div className="flex w-full flex-col xl:hidden">
                  <div className="flex items-center justify-start gap-3 pb-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-primary/12 text-primary">
                      <SlidersHorizontal className="h-4.5 w-4.5" />
                    </div>
                    {/* Fixed Truncation: Replaced 'truncate' with 'whitespace-nowrap' */}
                    <h2 className="text-base font-semibold leading-none text-foreground whitespace-nowrap">
                      College Filter Tool
                    </h2>
                  </div>
                  <div className="border-b border-border w-full"></div>
                </div>

                {/* 2. Desktop View (xl+): Vertical Logo + Expand Icon Centered */}
                <div className="hidden flex-col items-center gap-4 pt-2 xl:flex">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-primary/12 text-primary">
                    <SlidersHorizontal className="h-4.5 w-4.5" />
                  </div>
                  
                  {/* Added Enterprise Divider */}
                  <div className="w-6 border-b border-border"></div>
                  
                  <button
                    type="button"
                    title="Expand selection panel"
                    aria-label="Expand selection panel"
                    onClick={() => setIsSelectionPanelCollapsed(false)}
                    className="inline-flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-lg border border-border bg-background/80 text-muted-foreground transition hover:bg-muted hover:text-foreground"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </>
            )}
          </div>

          <div className="min-h-0 px-4 py-3 xl:flex-1 xl:overflow-y-auto xl:cf-panel-scroll">
            {!isSelectionPanelCollapsed ? (
              <>
                {isPathCatalogLoading ? <SelectionPanelSkeleton /> : null}

                {isPathCatalogError ? (
                  <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                    Failed to load exam paths.
                  </div>
                ) : null}

                {!isPathCatalogLoading && !isPathCatalogError ? (
                  <PathSelector
                    roots={roots}
                    selectedRootPathId={selectedRootPathId}
                    selectedEducationType={selectedEducationType}
                    selectedFinalPathId={selectedFinalPathId}
                    onSelectRootPath={(pathId) => {
                      if (pathId !== selectedRootPathId) {
                        resetSearchWorkspaceState();
                      }
                      setSelectedRootPathId(pathId);
                      setSelectedEducationType(null);
                      setSelectedFinalPathId(null);
                    }}
                    onSelectEducationType={(educationType) => {
                      if (educationType !== selectedEducationType) {
                        resetSearchWorkspaceState();
                      }
                      setSelectedEducationType(educationType);
                      setSelectedFinalPathId(null);
                    }}
                    onSelectFinalPath={(pathId) => {
                      if (pathId !== selectedFinalPathId) {
                        resetSearchWorkspaceState();
                      }
                      setSelectedFinalPathId(pathId);
                    }}
                  />
                ) : null}

                {selection.hasResolvedFinalPath ? (
                  <div className="mt-4">
                    {isMetadataLoading ? (
                      <DynamicFilterPanelSkeleton
                        controlCount={5}
                        showLocationCluster={true}
                        showFooterHint={true}
                      />
                    ) : metadataData?.raw ? (
                      <DynamicFilterPanel
                        key={selection.finalPathId ?? "college-filter-empty-path"}
                        metadata={metadataData.raw}
                        initialScore={draftScore}
                        initialFilters={draftFilters}
                        onFormStateChange={handleFormStateChange}
                      />
                    ) : isMetadataError ? (
                      <div className="rounded-2xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                        Failed to load filters for the selected path.
                      </div>
                    ) : null}
                  </div>
                ) : null}

                {selection.hasResolvedFinalPath && metadataData?.raw ? (
                  <div className="mt-4">
                    <SearchActionBar
                      isSearchReady={formSnapshot?.isSearchReady ?? false}
                      isSearching={searchMutation.isPending}
                      hasExecutedSearch={hasExecutedSearch}
                      resultsAreStale={resultsAreStale}
                      onSearch={handleSearch}
                    />
                  </div>
                ) : null}
              </>
            ) : null}
          </div>

          <div className="absolute -bottom-4 left-1/2 z-10 -translate-x-1/2 xl:hidden">
            <button
              type="button"
              title={
                isSelectionPanelCollapsed
                  ? "Expand selection panel"
                  : "Collapse selection panel"
              }
              aria-label={
                isSelectionPanelCollapsed
                  ? "Expand selection panel"
                  : "Collapse selection panel"
              }
              onClick={() => setIsSelectionPanelCollapsed((current) => !current)}
              className="inline-flex cursor-pointer h-10 w-10 items-center justify-center rounded-full border border-border bg-card text-muted-foreground shadow-md transition hover:bg-muted hover:text-foreground"
            >
              {isSelectionPanelCollapsed ? (
                <ChevronUp className="h-5 w-5" />
              ) : (
                <ChevronDown className="h-5 w-5" />
              )}
            </button>
          </div>
        </section>

        <section className="min-h-0 rounded-3xl border border-border bg-card shadow-sm xl:flex xl:flex-col xl:overflow-hidden">
          <div className="min-h-0 px-4 py-3 xl:flex-1 xl:overflow-hidden">
            {shouldShowFollowSteps ? (
              <div className="min-h-0 xl:h-full xl:overflow-y-auto xl:cf-panel-scroll">
                <FollowStepsPanel
                  selectedRootPathId={selectedRootPathId}
                  selectedEducationType={selectedEducationType}
                  selectedFinalPathId={selection.finalPathId}
                  visibleFilters={resolvedVisibleFilters}
                  shouldShowEducationTypeStep={selection.shouldShowEducationTypeStep}
                  shouldShowSelectionTypeStep={selection.shouldShowSelectionTypeStep}
                  isFilterStepCompleted={formSnapshot?.isFilterStepCompleted}
                />
              </div>
            ) : (
              <SearchStatusPanel
                searchResponse={searchResponse}
                activeVisibleBand={activeVisibleBand}
                resultsAreStale={resultsAreStale}
                searchErrorMessage={searchErrorMessage}
                isRefreshingResults={searchMutation.isPending}
                isSelectionPanelCollapsed={isSelectionPanelCollapsed}
                onChangeBand={(band) => {
                  setActiveVisibleBand(band);
                  if (appliedSearchState?.applied) {
                    setAppliedSearchState({
                      ...appliedSearchState,
                      activeBand: band,
                    });
                  }
                }}
                onPreviousPage={(band) => {
                  void handleBandPageChange(band, "previous");
                }}
                onNextPage={(band) => {
                  void handleBandPageChange(band, "next");
                }}
              />
            )}
          </div>
        </section>
      </div>
    </div>
  );
}