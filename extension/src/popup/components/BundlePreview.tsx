import { useMemo, useState } from "react";
import type { PackResponse } from "../../types";
import { assembleBundle } from "../../lib/bundle";

interface Props {
  result: PackResponse;
}

export default function BundlePreview({ result }: Props) {
  const [excluded, setExcluded] = useState<Set<string>>(new Set());
  const [copied, setCopied] = useState(false);

  const includedFiles = useMemo(
    () => result.files.filter((f) => !excluded.has(f.path)),
    [result.files, excluded]
  );
  const totalTokens = useMemo(
    () => includedFiles.reduce((sum, f) => sum + f.token_count, 0),
    [includedFiles]
  );

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

      <ul className="max-h-56 space-y-1 overflow-y-auto rounded border border-neutral-800">
        {result.files.map((f) => (
          <li
            key={f.path}
            className="flex items-center gap-2 border-b border-neutral-800 px-2 py-1 last:border-b-0"
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
            <span className="shrink-0 text-[10px] text-neutral-500">
              {f.token_count.toLocaleString()}t
            </span>
          </li>
        ))}
      </ul>

      <button
        className="w-full rounded bg-amber-500 py-1.5 text-sm font-medium text-neutral-950 disabled:opacity-50"
        disabled={includedFiles.length === 0}
        onClick={handleCopy}
      >
        {copied ? "Copied!" : "Copy to clipboard"}
      </button>
    </div>
  );
}
