import { create } from 'zustand'

interface P1State {
  motion: string
  answers: Record<string, string | string[]>
  setMotion: (m: string) => void
  setAnswer: (id: string, val: string | string[]) => void
  reset: () => void
}

export const useP1State = create<P1State>((set) => ({
  motion: '',
  answers: {},
  setMotion: (motion) => set({ motion, answers: {} }),
  setAnswer: (id, val) => set((s) => ({ answers: { ...s.answers, [id]: val } })),
  reset: () => set({ motion: '', answers: {} }),
}))
