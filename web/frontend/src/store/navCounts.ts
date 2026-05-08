import { create } from 'zustand'

type NavCountsState = {
  entryCount: number | null
  patternCount: number | null
}

export const useNavCounts = create<NavCountsState>(() => ({
  entryCount: null,
  patternCount: null,
}))
