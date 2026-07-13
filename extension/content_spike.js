// Spike 3: confirm we can locate and write into the claude.ai input box.
// This is throwaway detection logic — Phase 3 will replace it with a
// properly maintained, feature-detected selector list plus a clipboard
// fallback (see ARCHI.md §6 / PLAN.md Phase 3).

function findClaudeInput() {
  // claude.ai's composer is a contenteditable ProseMirror div; fall back to
  // any contenteditable or textarea if the class name has since changed.
  return (
    document.querySelector('div[contenteditable="true"].ProseMirror') ||
    document.querySelector('div[contenteditable="true"]') ||
    document.querySelector("textarea")
  );
}

function injectHelloWorld() {
  const el = findClaudeInput();
  if (!el) {
    console.warn("[context-packer spike] no input box found on this page");
    return;
  }

  el.focus();
  if (el.tagName === "TEXTAREA") {
    el.value = "hello world";
    el.dispatchEvent(new Event("input", { bubbles: true }));
  } else {
    // contenteditable: use execCommand so React/ProseMirror's input
    // listeners see it as a real edit, not a silent DOM mutation.
    document.execCommand("insertText", false, "hello world");
  }
  console.log("[context-packer spike] injected into", el);
}

// Expose a manual trigger since we don't want to auto-inject on every page
// load during this spike — run `contextPackerSpike()` from the devtools
// console on a claude.ai chat page.
window.contextPackerSpike = injectHelloWorld;
