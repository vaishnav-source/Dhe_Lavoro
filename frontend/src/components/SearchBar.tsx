interface Props {
  value: string;
  onChange: (v: string) => void;
  source: string;
  onSourceChange: (v: string) => void;
}

export default function SearchBar({ value, onChange, source, onSourceChange }: Props) {
  return (
    <div className="rounded-xl border border-hairline bg-surface p-2 flex flex-col sm:flex-row gap-2">
      <div className="flex-1 flex items-center gap-2 px-3">
        <span className="font-mono text-park text-sm">›</span>
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="search role or company"
          className="w-full bg-transparent py-2.5 text-sm font-body placeholder:text-inktext/40 focus:outline-none"
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
  );
}
