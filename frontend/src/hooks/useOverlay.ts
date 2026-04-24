import {
  type AlertOptions,
  type ConfirmOptions,
  type ModalOptions,
  type PromptOptions,
  useOverlayStore,
} from '@/stores/overlay-store';

/**
 * 컴포넌트 트리 어디서든 overlay를 imperative하게 호출하는 hook.
 *
 * @example
 * const overlay = useOverlay();
 *
 * // Alert
 * overlay.alert({ type: "success", title: "저장됨", description: "변경사항이 저장되었습니다." });
 *
 * // Confirm
 * overlay.confirm({
 *   title: "삭제하시겠습니까?",
 *   description: "이 작업은 되돌릴 수 없습니다.",
 *   confirmLabel: "삭제",
 *   variant: "destructive",
 *   onConfirm: () => handleDelete(),
 * });
 *
 * // Modal
 * overlay.modal({
 *   title: "프로필 편집",
 *   size: "lg",
 *   content: <ProfileEditForm />,
 *   footer: <Button onClick={() => overlay.closeModal()}>저장</Button>,
 * });
 */
export function useOverlay() {
  const {
    showAlert,
    hideAlert,
    showConfirm,
    hideConfirm,
    showModal,
    hideModal,
    showPrompt,
    hidePrompt,
  } = useOverlayStore();

  return {
    alert: showAlert,
    confirm: showConfirm,
    modal: showModal,
    prompt: showPrompt,
    closeAlert: hideAlert,
    closeConfirm: hideConfirm,
    closeModal: hideModal,
    closePrompt: hidePrompt,
  };
}

export type { AlertOptions, ConfirmOptions, ModalOptions, PromptOptions };
