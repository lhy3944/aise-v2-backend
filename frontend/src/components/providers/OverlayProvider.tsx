'use client';

import { AlertDialog } from '@/components/overlay/AlertDialog';
import { ConfirmDialog } from '@/components/overlay/ConfirmDialog';
import { Modal } from '@/components/overlay/Modal';
import { PromptDialog } from '@/components/overlay/PromptDialog';
import { useOverlayStore } from '@/stores/overlay-store';

export function OverlayProvider() {
  const {
    alertOpen,
    alertOptions,
    hideAlert,
    confirmOpen,
    confirmOptions,
    hideConfirm,
    modalOpen,
    modalOptions,
    hideModal,
    promptOpen,
    promptOptions,
    hidePrompt,
  } = useOverlayStore();

  return (
    <>
      {alertOptions && (
        <AlertDialog
          open={alertOpen}
          onOpenChange={(open) => {
            if (!open) hideAlert();
          }}
          {...alertOptions}
        />
      )}

      {confirmOptions && (
        <ConfirmDialog
          open={confirmOpen}
          onOpenChange={(open) => {
            if (!open) hideConfirm();
          }}
          {...confirmOptions}
        />
      )}

      {modalOptions && (
        <Modal
          open={modalOpen}
          onOpenChange={(open) => {
            if (!open) hideModal();
          }}
          {...modalOptions}
        >
          {modalOptions.content}
        </Modal>
      )}

      {promptOptions && (
        <PromptDialog
          open={promptOpen}
          onOpenChange={(open) => {
            if (!open) hidePrompt();
          }}
          {...promptOptions}
        />
      )}
    </>
  );
}
