import { TOKEN_BUDGET_PRESETS } from "../../types";

interface Props {
  value: number;
  onChange: (value: number) => void;
}

export default function TokenBudgetPicker({ value, onChange }: Props) {
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
    </div>
  );
}
