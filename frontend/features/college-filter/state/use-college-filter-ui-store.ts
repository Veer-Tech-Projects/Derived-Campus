import { create } from "zustand";
import { CollegeBand } from "../types/contracts";

interface CollegeFilterUiState {
  mobileFilterDrawerOpen: boolean;
  hasExecutedSearch: boolean;
  resultsAreStale: boolean;
  activeVisibleBand: CollegeBand | null;

  setMobileFilterDrawerOpen: (open: boolean) => void;
  setHasExecutedSearch: (value: boolean) => void;
  setResultsAreStale: (value: boolean) => void;
  setActiveVisibleBand: (band: CollegeBand | null) => void;

  markSearchExecuted: () => void;
  markFiltersEditedAfterSearch: () => void;
  resetUiState: () => void;
}

export const useCollegeFilterUiStore = create<CollegeFilterUiState>((set) => ({
  mobileFilterDrawerOpen: false,
  hasExecutedSearch: false,
  resultsAreStale: false,
  activeVisibleBand: null,

  setMobileFilterDrawerOpen: (open) => set({ mobileFilterDrawerOpen: open }),
  setHasExecutedSearch: (value) => set({ hasExecutedSearch: value }),
  setResultsAreStale: (value) => set({ resultsAreStale: value }),
  setActiveVisibleBand: (band) => set({ activeVisibleBand: band }),

  markSearchExecuted: () =>
    set({
      hasExecutedSearch: true,
      resultsAreStale: false,
    }),

  markFiltersEditedAfterSearch: () =>
    set((state) => ({
      resultsAreStale: state.hasExecutedSearch ? true : false,
    })),

  resetUiState: () =>
    set({
      mobileFilterDrawerOpen: false,
      hasExecutedSearch: false,
      resultsAreStale: false,
      activeVisibleBand: null,
    }),
}));