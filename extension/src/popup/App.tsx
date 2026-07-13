import { useEffect, useState } from "react";
import { ApiError, getStatus, packContext, scanRepo } from "../lib/api";
import type { PackResponse, RepoInfo } from "../types";
import RepoPicker from "./components/RepoPicker";
import TokenBudgetPicker from "./components/TokenBudgetPicker";
import BundlePreview from "./components/BundlePreview";

type ServerStatus = "checking" | "ok" | "down";

export default function App() {
  const [serverStatus, setServerStatus] = useState<ServerStatus>("checking");
  const [repos, setRepos] = useState<RepoInfo[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string | null>(null);

  const [repoPathInput, setRepoPathInput] = useState("");
  const [scanning, setScanning] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);

  const [task, setTask] = useState("");
  const [tokenBudget, setTokenBudget] = useState(8192);
  const [packing, setPacking] = useState(false);
  const [packError, setPackError] = useState<string | null>(null);
  const [packResult, setPackResult] = useState<PackResponse | null>(null);
  const [packVersion, setPackVersion] = useState(0);

  useEffect(() => {
    getStatus()
      .then((res) => {
        setRepos(res.indexed_repos);
        if (res.indexed_repos.length > 0) setSelectedRepoId(res.indexed_repos[0].repo_id);
        setServerStatus("ok");
      })
      .catch(() => setServerStatus("down"));
  }, []);

  async function handleScan() {
    setScanning(true);
    setScanError(null);
    try {
      const res = await scanRepo(repoPathInput.trim());
      const newRepo: RepoInfo = {
        repo_id: res.repo_id,
        repo_path: res.repo_path,
        last_scanned_at: new Date().toISOString(),
        file_count: res.files_scanned,
        chunk_count: res.chunks_indexed,
      };
      setRepos((prev) => [newRepo, ...prev.filter((r) => r.repo_id !== newRepo.repo_id)]);
      setSelectedRepoId(newRepo.repo_id);
      setRepoPathInput("");
      setPackResult(null);
    } catch (err) {
      setScanError(err instanceof ApiError ? err.message : "Scan failed unexpectedly.");
    } finally {
      setScanning(false);
    }
  }

  async function handlePack() {
    if (!selectedRepoId) return;
    setPacking(true);
    setPackError(null);
    setPackResult(null);
    try {
      const res = await packContext(selectedRepoId, task.trim(), tokenBudget);
      setPackResult(res);
      setPackVersion((v) => v + 1);
    } catch (err) {
      setPackError(err instanceof ApiError ? err.message : "Pack failed unexpectedly.");
    } finally {
      setPacking(false);
    }
  }

  if (serverStatus === "checking") {
    return <Shell>Checking local server…</Shell>;
  }

  if (serverStatus === "down") {
    return (
      <Shell>
        <p className="text-sm text-red-400">Local server not running.</p>
        <p className="mt-2 text-xs text-neutral-400">
          Start it from <code className="text-neutral-300">server/</code>:
        </p>
        <pre className="mt-1 overflow-x-auto rounded bg-neutral-900 p-2 text-[11px] text-neutral-300">
          uv run uvicorn app.main:app --port 8000
        </pre>
      </Shell>
    );
  }

  return (
    <Shell>
      <RepoPicker
        repos={repos}
        selectedRepoId={selectedRepoId}
        onSelect={setSelectedRepoId}
        repoPathInput={repoPathInput}
        onRepoPathInputChange={setRepoPathInput}
        onScan={handleScan}
        scanning={scanning}
        scanError={scanError}
      />

      <textarea
        className="mt-3 w-full resize-none rounded border border-neutral-700 bg-neutral-900 px-2 py-1.5 text-sm"
        rows={3}
        placeholder="Describe the task, e.g. fix the auth bug in login flow"
        value={task}
        onChange={(e) => setTask(e.target.value)}
      />

      <div className="mt-2">
        <TokenBudgetPicker value={tokenBudget} onChange={setTokenBudget} />
      </div>

      <button
        className="mt-3 w-full rounded bg-amber-500 py-1.5 text-sm font-semibold text-neutral-950 disabled:opacity-50"
        disabled={!selectedRepoId || !task.trim() || packing}
        onClick={handlePack}
      >
        {packing ? "Packing…" : "Pack Context"}
      </button>

      {packError && <p className="mt-2 text-xs text-red-400">{packError}</p>}

      {packResult && (
        <div className="mt-3">
          <BundlePreview key={packVersion} result={packResult} />
        </div>
      )}
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return <div className="w-[380px] p-3">{children}</div>;
}
