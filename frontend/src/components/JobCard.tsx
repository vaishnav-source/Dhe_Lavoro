import { Link } from "react-router-dom";
import type { Job } from "../types";

function daysUntil(dateStr: string | null): number | null {
  if (!dateStr) return null;
  const target = new Date(dateStr);
  if (isNaN(target.getTime())) return null;
  const diffMs = target.getTime() - Date.now();
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
}

const SOURCE_LABEL: Record<string, string> = {
  infopark: "Infopark",
  technopark: "Technopark",
};

// null experience_max means an open-ended "X+ years" posting (see
// experience_extractor.py) — render that as "5+ yrs" instead of "5-null yrs".
function formatExperience(min: number | null, max: number | null): string | null {
  if (min === null) return null;
  if (min === 0 && max === 0) return "fresher";
  if (max === null) return `${min}+ yrs`;
  if (min === max) return `${min} yrs`;
  return `${min}-${max} yrs`;
}

export default function JobCard({ job }: { job: Job }) {
  const remaining = daysUntil(job.closing_date);
  const urgent = remaining !== null && remaining <= 5 && remaining >= 0;
  const experience = formatExperience(job.experience_min, job.experience_max);

  return (
    <Link
      to={`/jobs/${job.id}`}
      className="badge-card group flex flex-col h-full rounded-xl bg-surface border border-hairline shadow-sm overflow-hidden"
    >
      {/* Badge header: park clearance zone + punch hole */}
      <div className="flex items-center justify-between bg-ink px-4 py-2.5 shrink-0">
        <span className="font-mono text-[11px] tracking-wider text-stock/80 uppercase">
          {(SOURCE_LABEL[job.source] ?? job.source)} clearance
        </span>
        <span className="badge-hole" aria-hidden="true" />
      </div>

      {/* Body — flex-1 so it stretches and keeps footers aligned across cards */}
      <div className="flex-1 p-5">
        <h3 className="font-display font-semibold text-lg leading-snug text-inktext group-hover:text-park transition-colors">
          {job.job_title}
        </h3>
        <p className="mt-1 text-sm text-inktext/70">{job.company}</p>

        {job.short_description && (
          <p className="mt-3 text-sm text-inktext/60 line-clamp-2">
            {job.short_description}
          </p>
        )}

        <div className="mt-3 flex flex-wrap gap-2">
          {experience && (
            <span className="inline-flex items-center rounded-full bg-park/10 text-park text-xs font-medium px-2.5 py-1 font-mono">
              {experience}
            </span>
          )}
          {urgent && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-gold/15 text-inktext text-xs font-medium px-2.5 py-1 font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-gold" />
              {remaining === 0 ? "closes today" : `${remaining}d to close`}
            </span>
          )}
        </div>
      </div>

      {/* Tear line + badge ID footer — mt-auto pins it to the bottom */}
      <div className="badge-tear mt-auto flex items-center justify-between px-5 py-2.5 bg-stock/60 shrink-0">
        <span className="font-mono text-[11px] text-inktext/50">
          ID·{job.source_job_id}
        </span>
        <span className="font-mono text-[11px] text-park font-medium">
          view details →
        </span>
      </div>
    </Link>
  );
}