import { useEffect, useState } from "react";
import { TOKEN_BUDGET_PRESETS } from "../../types";

interface Props {
  value: number;
  onChange: (value: number) => void;
}

export default function TokenBudgetPicker({ value, onChange }: Props) {
  const [customInput, setCustomInput] = useState(String(value));

  // Keep the text box in sync when a preset button changes `value`
  // elsewhere, but don't fight the user while they're typing a custom one.
  useEffect(() => {
    setCustomInput(String(value));
  }, [value]);

  function commitCustom(raw: string) {
    const parsed = Number.parseInt(raw, 10);
    if (Number.isFinite(parsed) && parsed > 0) onChange(parsed);
  }

  return (
    <div className="flex gap-2">
      {TOKEN_BUDGET_PRESETS.map((preset) => (
        <button
          key={preset.value}
          className={`flex-1 rounded border px-2 py-1 text-xs font-medium ${
            value === preset.value
              ? "border-amber-500 bg-amber-500/10 text-amber-400"
              : "border-neutral-700 bg-neutral-900 text-neutral-300"
          }`}
          onClick={() => onChange(preset.value)}
        >
          {preset.label}
        </button>
      ))}
      <input
        type="number"
        min={1}
        className="w-20 rounded border border-neutral-700 bg-neutral-900 px-2 py-1 text-xs text-neutral-300"
        placeholder="custom"
        value={customInput}
        onChange={(e) => setCustomInput(e.target.value)}
        onBlur={(e) => commitCustom(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            commitCustom(e.currentTarget.value);
          }
        }}
      />
    </div>
  );
}
