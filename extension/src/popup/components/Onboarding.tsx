interface Props {
  onDismiss: () => void;
}

export default function Onboarding({ onDismiss }: Props) {
  return (
    <div className="space-y-3 text-sm">
      <h1 className="text-base font-semibold text-neutral-100">Welcome to Context Packer</h1>
      <p className="text-neutral-300">
        This extension picks the most relevant files from a local repo for a
        task you describe, and packs them into a bundle sized to fit a token
        budget — so you stop hand-picking files to paste into claude.ai.
      </p>
      <p className="text-neutral-300">
        Because browser extensions can't read your filesystem directly, a
        small local companion server does the actual scanning — it only
        listens on your machine (<code className="text-neutral-400">127.0.0.1</code>),
        nothing leaves it.
      </p>
      <div>
        <p className="mb-1 text-xs text-neutral-400">Start it once per work session, from the repo's `server/` folder:</p>
        <pre className="overflow-x-auto rounded bg-neutral-900 p-2 text-[11px] text-neutral-300">
          uv run uvicorn app.main:app --port 8000
        </pre>
      </div>
      <button
        className="w-full rounded bg-amber-500 py-1.5 text-sm font-semibold text-neutral-950"
        onClick={onDismiss}
      >
        Got it, let's go
      </button>
    </div>
  );
}
