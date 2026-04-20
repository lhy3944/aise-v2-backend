import { create } from 'zustand';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
  description?: string;
  duration: number;
}

interface ToastState {
  toasts: ToastItem[];
  add: (toast: Omit<ToastItem, 'id'>) => void;
  remove: (id: string) => void;
}

let counter = 0;

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],

  add: (toast) => {
    const id = `toast-${++counter}`;
    set((s) => ({ toasts: [...s.toasts, { ...toast, id }] }));
  },

  remove: (id) => {
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
  },
}));
