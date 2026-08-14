import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getJob } from "../api/client";
import type { Job } from "../types";

/** Turn raw scraped posting text into readable sections */
function FormattedDescription({ text }: { text: string }) {
  // Split on common section headers that appear in Technopark / Infopark posts
  const sectionRegex =
    /(Brief Description|Key Responsibilities|Required Skills|Preferred Skills|Experience|Work Location|Job Description|Responsibilities|Skills|Qualifications|About the Role|About the Company)/gi;

  const parts = text.split(sectionRegex).map((p) => p.trim()).filter(Boolean);

  // If we couldn't detect any sections, fall back to plain pre-line
  if (parts.length <= 1) {
    return (
      <p className="mt-4 text-sm text-inktext/70 whitespace-pre-line leading-relaxed">
        {text}
      </p>
    );
  }

  const blocks: { title?: string; body: string }[] = [];
  let i = 0;

  // First chunk before any header is usually company / meta info
  if (parts[0] && !sectionRegex.test(parts[0])) {
    blocks.push({ body: parts[0] });
    i = 1;
  }

  while (i < parts.length) {
    const title = parts[i];
    const body = parts[i + 1] ?? "";
    blocks.push({ title, body });
    i += 2;
  }

  return (
    <div className="mt-4 space-y-6">
      {blocks.map((block, idx) => {
        // Turn bullet-like lines into a real list when possible
        const lines = block.body
          .split(/\n+/)
          .map((l) => l.trim())
          .filter(Boolean);

        const looksLikeList =
          lines.length > 1 &&
          lines.every(
            (l) =>
              l.startsWith("-") ||
              l.startsWith("•") ||
              l.startsWith("*") ||
              /^\d+[\.\)]/.test(l) ||
              l.length < 120
          );

        return (
          <div key={idx}>
            {block.title && (
              <h4 className="font-mono text-xs uppercase tracking-wide text-park mb-2">
                {block.title}
              </h4>
            )}

            {looksLikeList ? (
              <ul className="space-y-1.5 text-sm text-inktext/70 leading-relaxed list-disc pl-5">
                {lines.map((line, li) => (
                  <li key={li}>
                    {line.replace(/^[-•*]\s*/, "").replace(/^\d+[\.\)]\s*/, "")}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-inktext/70 whitespace-pre-line leading-relaxed">
                {block.body}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

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
            {/* Badge header */}
            <div className="bg-ink text-stock px-6 py-4 flex items-center justify-between">
              <span className="font-mono text-xs uppercase tracking-wider text-stock/70">
                {job.source} clearance · ID·{job.source_job_id}
              </span>
              <span className="w-3.5 h-3.5 rounded-full border border-stock/40" aria-hidden="true" />
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

              <div className="mt-8 flex flex-wrap gap-3">
                {job.contact_email && (
                  <a
                    href={`mailto:${job.contact_email}?subject=Application: ${encodeURIComponent(
                      job.job_title
                    )}`}
                    className="inline-flex items-center gap-2 rounded-lg bg-park text-white px-5 py-2.5 text-sm font-medium hover:bg-park-dark transition-colors"
                  >
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
                  <FormattedDescription text={job.description} />
                </details>
              )}
            </div>
          </article>
        )}
      </div>
    </div>
  );
}