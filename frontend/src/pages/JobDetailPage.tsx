import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getJob } from "../api/client";
import type { Job } from "../types";
import HandDrawnFilters from "../components/HandDrawnFilters";
import "../components/HandDrawnButton.css";

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    getJob(id)
      .then((res) => {
        if (!cancelled) setJob(res);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "Something went wrong");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <div className="min-h-screen">
      <HandDrawnFilters />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        <Link
          to="/"
          className="font-mono text-xs text-park hover:underline inline-flex items-center gap-1"
        >
          ← back to terminal
        </Link>

        {loading && (
          <p className="mt-10 font-mono text-sm text-inktext/50">
            reading pass…
          </p>
        )}

        {error && (
          <div className="mt-6 rounded-xl border border-gold/40 bg-gold/10 px-4 py-3 text-sm">
            {error === "Job not found"
              ? "This pass has expired or been removed."
              : `Couldn't reach the terminal — ${error}`}
          </div>
        )}

        {job && (
          <article className="mt-6 rounded-xl border border-hairline bg-surface overflow-hidden">
            <div className="bg-ink text-stock px-6 py-4 flex items-center justify-between">
              <span className="font-mono text-xs uppercase tracking-wider text-stock/70">
                {job.source} clearance · ID·{job.source_job_id}
              </span>
              <span
                className="w-3.5 h-3.5 rounded-full border border-stock/40"
                aria-hidden="true"
              />
            </div>

            <div className="p-6 sm:p-8">
              <h1 className="font-display font-semibold text-2xl sm:text-3xl text-inktext">
                {job.job_title}
              </h1>
              <p className="mt-1 text-inktext/70">{job.company}</p>

              <dl className="mt-5 grid grid-cols-2 gap-4 text-sm font-mono">
                <div>
                  <dt className="text-inktext/40 uppercase text-xs">posted</dt>
                  <dd className="mt-0.5">{job.posted_date || "—"}</dd>
                </div>
                <div>
                  <dt className="text-inktext/40 uppercase text-xs">closes</dt>
                  <dd className="mt-0.5">{job.closing_date || "—"}</dd>
                </div>
              </dl>

              {job.short_description && (
                <p className="mt-6 text-inktext/80 leading-relaxed">
                  {job.short_description}
                </p>
              )}

              <div className="mt-8 flex flex-wrap gap-3 items-center">
                {job.contact_email && (
                  <a
                    href={`mailto:${job.contact_email}?subject=Application: ${encodeURIComponent(
                      job.job_title
                    )}`}
                    className="hand-btn"
                  >
                    <svg
                      className="highlight"
                      viewBox="0 0 144.75738 77.18431"
                      preserveAspectRatio="none"
                    >
                      <g transform="translate(-171.52826,-126.11624)">
                        <g
                          fill="none"
                          strokeWidth={17}
                          strokeLinecap="round"
                          strokeMiterlimit={10}
                        >
                          <path d="M180.02826,169.45123c0,0 12.65228,-25.55115 24.2441,-25.66863c6.39271,-0.06479 -5.89143,46.12943 4.90937,50.63857c10.22345,4.2681 24.14292,-52.38336 37.86455,-59.80493c3.31715,-1.79413 -5.35094,45.88889 -0.78872,58.34589c5.19371,14.18125 33.36934,-58.38221 36.43049,-56.91633c4.67078,2.23667 -0.06338,44.42744 5.22574,47.53647c6.04041,3.55065 19.87185,-20.77286 19.87185,-20.77286" />
                        </g>
                      </g>
                    </svg>
                    apply via email
                  </a>
                )}

                {job.detail_url && (
                  <a
                    href={job.detail_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 rounded-lg border border-hairline px-5 py-2.5 text-sm font-medium hover:bg-stock transition-colors"
                  >
                    view original posting
                  </a>
                )}
              </div>

              {job.description && (
                <details className="mt-8 badge-tear pt-6">
                  <summary className="cursor-pointer font-mono text-xs uppercase tracking-wide text-inktext/50 hover:text-park">
                    full posting text
                  </summary>
                  <p className="mt-4 text-sm text-inktext/70 whitespace-pre-line leading-relaxed">
                    {job.description}
                  </p>
                </details>
              )}
            </div>
          </article>
        )}
      </div>
    </div>
  );
}