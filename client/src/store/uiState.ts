import { create } from "zustand";

interface UIState {
  paletteOpen: boolean;
  openPalette: () => void;
  closePalette: () => void;
  togglePalette: () => void;
  composerOpen: boolean;
  openComposer: () => void;
  closeComposer: () => void;
  selectedEventId: string | null;
  setSelectedEventId: (id: string | null) => void;
  activePage: string;
  setActivePage: (page: string) => void;
}

export const useUIState = create<UIState>((set) => ({
  paletteOpen: false,
  openPalette: () => set({ paletteOpen: true }),
  closePalette: () => set({ paletteOpen: false }),
  togglePalette: () => set((s) => ({ paletteOpen: !s.paletteOpen })),
  composerOpen: false,
  openComposer: () => set({ composerOpen: true }),
  closeComposer: () => set({ composerOpen: false }),
  selectedEventId: null,
  setSelectedEventId: (id) => set({ selectedEventId: id }),
  activePage: "/dashboard",
  setActivePage: (page) => set({ activePage: page }),
}));
