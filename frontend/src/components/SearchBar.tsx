// Keyed range presets — "expKey" is what lives in the URL/state, and maps
// to the (exp_min, exp_max) pair the backend's GET /api/jobs expects.
// "8+" has no expMax on purpose: the backend treats a missing max as
// open-ended, matching how experience_extractor.py stores "5+ years"
// postings (experience_max left null).
export const EXPERIENCE_RANGES: {
  key: string;
  label: string;
  expMin?: number;
  expMax?: number;
}[] = [
  { key: "0-2", label: "0-2 yrs", expMin: 0, expMax: 2 },
  { key: "3-5", label: "3-5 yrs", expMin: 3, expMax: 5 },
  { key: "5-8", label: "5-8 yrs", expMin: 5, expMax: 8 },
  { key: "8+", label: "8+ yrs", expMin: 8 },
];

interface Props {
  value: string;
  onChange: (v: string) => void;
  source: string;
  onSourceChange: (v: string) => void;
  expRange: string;
  onExpRangeChange: (v: string) => void;
}

export default function SearchBar({
  value,
  onChange,
  source,
  onSourceChange,
  expRange,
  onExpRangeChange,
}: Props) {
  return (
    <div className="rounded-xl border border-hairline bg-surface p-2 flex flex-col gap-2">
      <div className="flex flex-col sm:flex-row gap-2">
        <div className="flex-1 flex items-center gap-2 px-3">
          <span className="font-mono text-park text-sm">›</span>
          <input
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder="search role or company"
            className="w-full bg-transparent py-2.5 text-sm font-body text-black placeholder:text-inktext/40 focus:outline-none"
          />
        </div>
        <div className="flex gap-1 px-1">
          {[
            { label: "all parks", value: "" },
            { label: "infopark", value: "infopark" },
            { label: "technopark", value: "technopark" },
          ].map((opt) => (
            <button
              key={opt.value}
              onClick={() => onSourceChange(opt.value)}
              className={`rounded-lg px-3 py-2 text-xs font-mono uppercase tracking-wide transition-colors ${
                source === opt.value
                  ? "bg-park text-white"
                  : "text-inktext/60 hover:bg-stock"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Experience chips — click again to clear, only one active at a time */}
      <div className="flex flex-wrap gap-1 px-1 pt-1 border-t border-hairline/60">
        <span className="font-mono text-[11px] uppercase tracking-wide text-inktext/40 self-center px-1">
          experience
        </span>
        {EXPERIENCE_RANGES.map((opt) => {
          const active = expRange === opt.key;
          return (
            <button
              key={opt.key}
              onClick={() => onExpRangeChange(active ? "" : opt.key)}
              aria-pressed={active}
              className={`rounded-full px-3 py-1 text-xs font-mono transition-colors border ${
                active
                  ? "bg-park text-white border-park"
                  : "text-inktext/60 border-hairline hover:bg-stock"
              }`}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}