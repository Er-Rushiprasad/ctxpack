import type { InjectBundleMessage, InjectResult } from "../lib/messages";

// Selector list, most-specific first — see PLAN.md Phase 0 Spike 3 and
// ARCHI.md §4.1 for how the ProseMirror selector was found. Kept as a list
// (not a single hardcoded selector) because claude.ai's DOM has changed
// before and will again; fall back to clipboard in the popup if none match.
const COMPOSER_SELECTORS = [
  'div[contenteditable="true"].ProseMirror',
  'div[contenteditable="true"]',
  "textarea",
];

function findComposer(): HTMLElement | null {
  for (const selector of COMPOSER_SELECTORS) {
    const el = document.querySelector<HTMLElement>(selector);
    if (el) return el;
  }
  return null;
}

function insertText(el: HTMLElement, text: string): boolean {
  el.focus();
  try {
    if (el instanceof HTMLTextAreaElement) {
      el.value = text;
      el.dispatchEvent(new Event("input", { bubbles: true }));
      return true;
    }
    // contenteditable (ProseMirror etc.): execCommand still reliably fires
    // the input events these editors listen for, unlike directly mutating
    // textContent.
    return document.execCommand("insertText", false, text);
  } catch {
    return false;
  }
}

chrome.runtime.onMessage.addListener(
  (message: InjectBundleMessage, _sender, sendResponse: (r: InjectResult) => void) => {
    if (message.type !== "inject-bundle") return undefined;

    const composer = findComposer();
    if (!composer) {
      sendResponse({ ok: false, reason: "composer-not-found" });
      return undefined;
    }

    const inserted = insertText(composer, message.text);
    sendResponse(inserted ? { ok: true } : { ok: false, reason: "insert-failed" });
    return undefined;
  }
);
