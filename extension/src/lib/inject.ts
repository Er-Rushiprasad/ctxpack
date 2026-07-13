import type { InjectBundleMessage, InjectResult } from "./messages";

export type InjectOutcome =
  | { status: "injected" }
  | { status: "no-tab" }
  | { status: "unreachable" }
  | { status: "composer-not-found" }
  | { status: "insert-failed" };

export async function injectIntoClaude(text: string): Promise<InjectOutcome> {
  const tabs = await chrome.tabs.query({ url: "https://claude.ai/*" });
  const tab = tabs[0];
  if (!tab?.id) return { status: "no-tab" };

  const message: InjectBundleMessage = { type: "inject-bundle", text };
  let response: InjectResult;
  try {
    response = await chrome.tabs.sendMessage(tab.id, message);
  } catch {
    // No content script listening — likely the tab was open before the
    // extension was (re)loaded and hasn't been refreshed since.
    return { status: "unreachable" };
  }

  return response.ok ? { status: "injected" } : { status: response.reason };
}
