export interface InjectBundleMessage {
  type: "inject-bundle";
  text: string;
}

export type InjectResult =
  | { ok: true }
  | { ok: false; reason: "composer-not-found" | "insert-failed" };
