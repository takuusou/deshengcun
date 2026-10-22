import { computed, readonly, ref } from "vue";

const successToast = ref("");
let dismissTimer = null;

export function showSuccessToast(message, duration = 2000) {
  const text = String(message || "").trim();
  if (dismissTimer) {
    window.clearTimeout(dismissTimer);
    dismissTimer = null;
  }
  successToast.value = text;
  if (!text) return;
  dismissTimer = window.setTimeout(() => {
    successToast.value = "";
    dismissTimer = null;
  }, Math.max(300, Number(duration) || 2000));
}

export function clearSuccessToast() {
  showSuccessToast("");
}

export function useSuccessToastState() {
  return readonly(successToast);
}

export function useTransientMessage() {
  return computed({
    get: () => "",
    set: (value) => {
      if (String(value || "").trim()) {
        showSuccessToast(value);
      }
    },
  });
}
