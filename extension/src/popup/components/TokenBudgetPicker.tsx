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
          className={`flex-1 rounded-lg border px-2 py-1 text-xs font-medium transition ${
            value === preset.value
              ? "border-amber-400/60 bg-amber-500/15 text-amber-300 shadow-inner shadow-amber-500/10"
              : "glass-field border-transparent text-neutral-300"
          }`}
          onClick={() => onChange(preset.value)}
        >
          {preset.label}
        </button>
      ))}
      <input
        type="number"
        min={1}
        className="glass-field w-20 rounded-lg px-2 py-1 text-xs text-neutral-300"
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
