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
  repoChanged: boolean;
  onRescan?: () => void;
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
  repoChanged,
  onRescan,
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

      {onRescan && (
        <div className="flex items-center justify-between text-xs">
          {repoChanged ? (
            <span className="text-amber-400">⚠ Repo changed since last scan</span>
          ) : (
            <span className="text-neutral-500">Up to date</span>
          )}
          <button
            className={`rounded px-2 py-0.5 font-medium ${
              repoChanged ? "bg-amber-500 text-neutral-950" : "text-neutral-400 hover:text-neutral-200"
            }`}
            disabled={scanning}
            onClick={onRescan}
          >
            {scanning ? "Scanning…" : "Re-scan"}
          </button>
        </div>
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
