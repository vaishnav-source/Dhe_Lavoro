import { Link } from "react-router-dom";
import type { Job } from "../types";

function daysUntil(dateStr: string | null): number | null {
  if (!dateStr) return null;
  const target = new Date(dateStr);
  if (isNaN(target.getTime())) return null;
  const diffMs = target.getTime() - Date.now();
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
}

export default function JobCard({ job }: { job: Job }) {
  const remaining = daysUntil(job.closing_date);
  const urgent = remaining !== null && remaining <= 5 && remaining >= 0;

  return (
    <Link
      to={`/jobs/${job.id}`}
      className="badge-card group block rounded-xl bg-surface border border-hairline shadow-sm overflow-hidden"
    >
      {/* Badge header: park clearance zone + punch hole */}
      <div className="flex items-center justify-between bg-ink px-4 py-2.5">
        <span className="font-mono text-[11px] tracking-wider text-stock/80 uppercase">
          {job.source} clearance
        </span>
        <span className="badge-hole" aria-hidden="true" />
      </div>

      <div className="p-5">
        <h3 className="font-display font-semibold text-lg leading-snug text-inktext group-hover:text-park transition-colors">
          {job.job_title}
        </h3>
        <p className="mt-1 text-sm text-inktext/70">{job.company}</p>

        {job.short_description && (
          <p className="mt-3 text-sm text-inktext/60 line-clamp-2">
            {job.short_description}
          </p>
        )}

        {urgent && (
          <span className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-gold/15 text-inktext text-xs font-medium px-2.5 py-1 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-gold" />
            {remaining === 0 ? "closes today" : `${remaining}d to close`}
          </span>
        )}
      </div>

      {/* Tear line + badge ID footer */}
      <div className="badge-tear flex items-center justify-between px-5 py-2.5 bg-stock/60">
        <span className="font-mono text-[11px] text-inktext/50">
          ID·{job.source_job_id}
        </span>
        <span className="font-mono text-[11px] text-park font-medium">
          view pass →
        </span>
      </div>
    </Link>
  );
}
