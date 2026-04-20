import type { ReactNode } from 'react';
import { create } from 'zustand';

export interface AlertOptions {
  type?: 'info' | 'success' | 'warning' | 'error';
  title?: string;
  description: string;
  confirmLabel?: string;
  onClose?: () => void;
}

export interface ConfirmOptions {
  title?: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'default' | 'destructive';
  onConfirm: () => void;
  onCancel?: () => void;
}

export interface ModalOptions {
  title?: string;
  description?: string;
  content: ReactNode;
  footer?: ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl';
  showCloseButton?: boolean;
  stickyFooter?: boolean;
  onClose?: () => void;
}

interface OverlayState {
  alertOpen: boolean;
  alertOptions: AlertOptions | null;
  confirmOpen: boolean;
  confirmOptions: ConfirmOptions | null;
  modalOpen: boolean;
  modalOptions: ModalOptions | null;

  showAlert: (options: AlertOptions) => void;
  hideAlert: () => void;
  showConfirm: (options: ConfirmOptions) => void;
  hideConfirm: () => void;
  showModal: (options: ModalOptions) => void;
  hideModal: () => void;
}

export const useOverlayStore = create<OverlayState>((set) => ({
  alertOpen: false,
  alertOptions: null,
  confirmOpen: false,
  confirmOptions: null,
  modalOpen: false,
  modalOptions: null,

  showAlert: (options) => set({ alertOpen: true, alertOptions: options }),
  hideAlert: () => set({ alertOpen: false }),
  showConfirm: (options) => set({ confirmOpen: true, confirmOptions: options }),
  hideConfirm: () => set({ confirmOpen: false }),
  showModal: (options) => set({ modalOpen: true, modalOptions: options }),
  hideModal: () => set({ modalOpen: false }),
}));
