import type { PackedFileInfo } from "../types";

/**
 * Mirrors the server's packer._assemble format so toggling files in the
 * preview doesn't require a round trip to /pack — see
 * server/app/services/packer.py.
 */
export function assembleBundle(includedFiles: PackedFileInfo[]): string {
  const treeSummary = includedFiles.map((f) => `- ${f.path}`).join("\n");
  const body = includedFiles.map((f) => f.content).join("\n");
  return `# Files included (${includedFiles.length})\n${treeSummary}\n\n${body}`;
}
