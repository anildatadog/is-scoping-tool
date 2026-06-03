import { create } from 'zustand'
import type { SfData } from '@shared/api-types'

interface P2State {
  sfData: SfData | null
  answers: Record<string, string | string[]>
  setSfData: (d: SfData) => void
  setAnswer: (id: string, val: string | string[]) => void
  reset: () => void
}

export const useP2State = create<P2State>((set) => ({
  sfData: null,
  answers: {},
  setSfData: (sfData) => {
    const seed = sessionStorage.getItem('p1_seed')
    const p1 = seed ? JSON.parse(seed) : null
    const prefill = sfData.prefill || {}
    const merged = p1
      ? { ...p1.answers, ...prefill, _p1_stated_motion: p1.motion }
      : prefill
    sessionStorage.removeItem('p1_seed')
    set({ sfData, answers: merged })
  },
  setAnswer: (id, val) => set((s) => ({ answers: { ...s.answers, [id]: val } })),
  reset: () => set({ sfData: null, answers: {} }),
}))
