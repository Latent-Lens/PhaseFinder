const MODAL_SELECTOR = ".stats_modal";
const FOCUSABLE_SELECTOR = "button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], [tabindex]:not([tabindex='-1'])";

let last_trigger = null;
const open_modals = [];

function focusable(modal) {
  return [...modal.querySelectorAll(FOCUSABLE_SELECTOR)].filter((element) => !element.hidden && element.getClientRects().length);
}

function open_modal(modal) {
  if (open_modals.some((entry) => entry.modal === modal)) return;
  open_modals.push({ modal, return_focus: last_trigger });
  if (!modal.contains(document.activeElement)) focusable(modal)[0]?.focus();
}

function close_modal(modal) {
  const index = open_modals.findIndex((entry) => entry.modal === modal);
  if (index < 0) return;
  const [entry] = open_modals.splice(index, 1);
  if (entry.return_focus?.isConnected && !entry.return_focus.disabled) entry.return_focus.focus();
}

export function init_modal_focus() {
  document.addEventListener("pointerdown", (event) => {
    if (!event.target.closest(MODAL_SELECTOR)) last_trigger = event.target.closest(FOCUSABLE_SELECTOR) || document.activeElement;
  }, true);
  document.addEventListener("keydown", (event) => {
    const modal = open_modals[open_modals.length - 1]?.modal;
    if (!modal || modal.hidden) {
      if (event.key === "Enter" || event.key === " ") last_trigger = event.target;
      return;
    }
    if (event.key === "Escape") {
      queueMicrotask(() => {
        if (!modal.hidden) modal.querySelector(".stats_modal_close, [id$='_cancel']")?.click();
      });
    }
  }, true);

  const observer = new MutationObserver((records) => {
    records.forEach(({ target }) => target.hidden ? close_modal(target) : open_modal(target));
  });
  document.querySelectorAll(MODAL_SELECTOR).forEach((modal) => {
    observer.observe(modal, { attributes: true, attributeFilter: ["hidden"] });
    if (!modal.hidden) open_modal(modal);
  });
}
