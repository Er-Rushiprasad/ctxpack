import { useMemo, useState } from "react";
import type { PackResponse } from "../../types";
import { assembleBundle } from "../../lib/bundle";
import { injectIntoClaude } from "../../lib/inject";

interface Props {
  result: PackResponse;
}

const INJECT_FAILURE_MESSAGES: Record<string, string> = {
  "no-tab": "No claude.ai tab open — copied to clipboard instead. Open claude.ai and paste.",
  unreachable:
    "Couldn't reach the claude.ai tab (try refreshing it) — copied to clipboard instead.",
  "composer-not-found":
    "Couldn't find the message box on claude.ai (its layout may have changed) — copied to clipboard instead.",
  "insert-failed": "Couldn't type into the message box — copied to clipboard instead.",
};

export default function BundlePreview({ result }: Props) {
  const [excluded, setExcluded] = useState<Set<string>>(new Set());
  const [copied, setCopied] = useState(false);
  const [injecting, setInjecting] = useState(false);
  const [injectMessage, setInjectMessage] = useState<string | null>(null);

  const includedFiles = useMemo(
    () => result.files.filter((f) => !excluded.has(f.path)),
    [result.files, excluded]
  );
  const totalTokens = useMemo(
    () => includedFiles.reduce((sum, f) => sum + f.token_count, 0),
    [includedFiles]
  );
  // Min-max normalized (not just divided by max) so the bars actually show
  // contrast — RRF fusion scores cluster in a narrow range, so relative-to-
  // max alone made every file's bar look ~80-100% regardless of how much
  // less relevant it was.
  const scoreRange = useMemo(() => {
    const scores = result.files.map((f) => f.relevance_score);
    const min = Math.min(...scores);
    const max = Math.max(...scores);
    return { min, max: Math.max(max, min + Number.EPSILON) };
  }, [result.files]);

  function toggle(path: string) {
    setExcluded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
    setCopied(false);
  }

  async function handleCopy() {
    const bundle = assembleBundle(includedFiles);
    await navigator.clipboard.writeText(bundle);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  async function handleInject() {
    setInjecting(true);
    setInjectMessage(null);
    const bundle = assembleBundle(includedFiles);
    try {
      const outcome = await injectIntoClaude(bundle);
      if (outcome.status === "injected") {
        setInjectMessage("Injected into claude.ai!");
      } else {
        await navigator.clipboard.writeText(bundle);
        setInjectMessage(INJECT_FAILURE_MESSAGES[outcome.status]);
      }
    } finally {
      setInjecting(false);
      setTimeout(() => setInjectMessage(null), 4000);
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-neutral-400">
          {includedFiles.length} / {result.files.length} files
        </span>
        <span
          className={
            totalTokens > result.token_budget ? "text-red-400" : "text-neutral-300"
          }
        >
          {totalTokens.toLocaleString()} / {result.token_budget.toLocaleString()} tokens
        </span>
      </div>

      <ul className="glass-field max-h-80 space-y-1 overflow-y-auto rounded-lg">
        {result.files.map((f) => (
          <li
            key={f.path}
            className="flex items-center gap-2 border-b border-white/5 px-2 py-1 last:border-b-0"
          >
            <input
              type="checkbox"
              checked={!excluded.has(f.path)}
              onChange={() => toggle(f.path)}
              className="shrink-0"
            />
            <span className="min-w-0 flex-1 truncate text-xs" title={f.path}>
              {f.path}
            </span>
            <span
              className="h-1.5 w-10 shrink-0 overflow-hidden rounded-full bg-white/10"
              title={`relevance score: ${f.relevance_score.toFixed(4)}`}
            >
              <span
                className="block h-full rounded-full bg-amber-500"
                style={{
                  width: `${Math.max(
                    4,
                    ((f.relevance_score - scoreRange.min) / (scoreRange.max - scoreRange.min)) * 100
                  )}%`,
                }}
              />
            </span>
            <span className="shrink-0 text-[10px] text-neutral-500">
              {f.token_count.toLocaleString()}t
            </span>
          </li>
        ))}
      </ul>

      <div className="flex gap-2">
        <button
          className="flex-1 rounded-lg bg-amber-500 py-1.5 text-sm font-medium text-neutral-950 shadow-lg shadow-amber-500/20 transition hover:bg-amber-400 disabled:opacity-50 disabled:shadow-none"
          disabled={includedFiles.length === 0}
          onClick={handleCopy}
        >
          {copied ? "Copied!" : "Copy to clipboard"}
        </button>
        <button
          className="flex-1 rounded-lg border border-amber-500/50 bg-white/5 py-1.5 text-sm font-medium text-amber-400 backdrop-blur-md transition hover:bg-amber-500/10 disabled:opacity-50"
          disabled={includedFiles.length === 0 || injecting}
          onClick={handleInject}
        >
          {injecting ? "Injecting…" : "Inject into claude.ai"}
        </button>
      </div>

      {injectMessage && <p className="text-xs text-neutral-400">{injectMessage}</p>}
    </div>
  );
}
