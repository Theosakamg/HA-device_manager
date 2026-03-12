/**
 * Global toast helper.
 *
 * Dispatches a "show-toast" CustomEvent on `window` that is picked up by
 * `dm-app-shell`, which forwards it to the mounted `<dm-toast>` component.
 */
export type ToastType = "success" | "error" | "info";

export function showToast(
  message: string,
  type: ToastType = "info",
  duration = 3000
) {
  window.dispatchEvent(
    new CustomEvent("show-toast", { detail: { message, type, duration } })
  );
}
