import type { RepoInfo } from "../../types";

interface Props {
  repos: RepoInfo[];
  selectedRepoId: string | null;
  onSelect: (repoId: string) => void;
  repoPathInput: string;
  onRepoPathInputChange: (value: string) => void;
  onScan: () => void;
  scanning: boolean;
  scanError: string | null;
}

export default function RepoPicker({
  repos,
  selectedRepoId,
  onSelect,
  repoPathInput,
  onRepoPathInputChange,
  onScan,
  scanning,
  scanError,
}: Props) {
  return (
    <div className="space-y-2">
      {repos.length > 0 && (
        <select
          className="w-full rounded border border-neutral-700 bg-neutral-900 px-2 py-1.5 text-sm"
          value={selectedRepoId ?? ""}
          onChange={(e) => onSelect(e.target.value)}
        >
          <option value="" disabled>
            Select a scanned repo…
          </option>
          {repos.map((r) => (
            <option key={r.repo_id} value={r.repo_id}>
              {r.repo_path} ({r.file_count} files)
            </option>
          ))}
        </select>
      )}

      <div className="flex gap-2">
        <input
          className="min-w-0 flex-1 rounded border border-neutral-700 bg-neutral-900 px-2 py-1.5 text-sm"
          placeholder="C:\path\to\repo"
          value={repoPathInput}
          onChange={(e) => onRepoPathInputChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && repoPathInput.trim() && !scanning) onScan();
          }}
        />
        <button
          className="shrink-0 rounded bg-amber-500 px-3 py-1.5 text-sm font-medium text-neutral-950 disabled:opacity-50"
          disabled={!repoPathInput.trim() || scanning}
          onClick={onScan}
        >
          {scanning ? "Scanning…" : "Scan"}
        </button>
      </div>

      {scanError && <p className="text-xs text-red-400">{scanError}</p>}
    </div>
  );
}
