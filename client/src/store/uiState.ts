import { create } from "zustand";

interface UIState {
  paletteOpen: boolean;
  openPalette: () => void;
  closePalette: () => void;
  togglePalette: () => void;
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
  selectedEventId: null,
  setSelectedEventId: (id) => set({ selectedEventId: id }),
  activePage: "/",
  setActivePage: (page) => set({ activePage: page }),
}));
