import { create } from 'zustand'

type NavCountsState = {
  entryCount: number | null
  patternCount: number | null
  setEntryCount: (n: number | null) => void
  setPatternCount: (n: number | null) => void
}

export const useNavCounts = create<NavCountsState>((set) => ({
  entryCount: null,
  patternCount: null,
  setEntryCount: (entryCount) => set({ entryCount }),
  setPatternCount: (patternCount) => set({ patternCount }),
}))
