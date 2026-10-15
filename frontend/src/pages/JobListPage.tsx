import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { listJobs } from "../api/client";
import type { Job } from "../types";
import JobCard from "../components/JobCard";
import SearchBar, { EXPERIENCE_RANGES } from "../components/SearchBar";

const LIMIT = 20;

const BROWSE_LINKS = [
  { label: "All Parks", to: "/" },
  { label: "Infopark Jobs", to: "/?source=infopark" },
  { label: "Technopark Jobs", to: "/?source=technopark" },
];

const COMPANY_LINKS = [{ label: "Terms & Conditions", to: "/terms" }];

const OFFICIAL_LINKS = [
  { label: "Infopark.in", href: "https://infopark.in" },
  { label: "Technopark.in", href: "https://technopark.in" },
];

// Re-shuffles which order jobs appear in on every fetch — since the
// backend always returns newest-first (id desc), without this the same
// jobs would sit in the same order on every visit. Shuffling only the
// already-fetched page of results (not the query itself) keeps pagination
// correct.
function shuffle<T>(items: T[]): T[] {
  const result = [...items];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

function JobCardSkeleton() {
  return (
    <div className="rounded-xl border border-hairline bg-surface overflow-hidden animate-pulse">
      {/* Header bar */}
      <div className="bg-ink px-4 py-3 flex items-center justify-between">
        <div className="h-3 w-28 bg-stock/20 rounded" />
        <div className="w-3.5 h-3.5 rounded-full border border-stock/30" />
      </div>

      {/* Body */}
      <div className="p-5 space-y-3">
        <div className="h-5 w-3/4 bg-inktext/10 rounded" />
        <div className="h-3.5 w-1/2 bg-inktext/10 rounded" />
        <div className="space-y-2 pt-1">
          <div className="h-3 w-full bg-inktext/10 rounded" />
          <div className="h-3 w-5/6 bg-inktext/10 rounded" />
        </div>
        <div className="pt-2">
          <div className="h-6 w-16 bg-inktext/10 rounded-full" />
        </div>
      </div>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-dashed border-hairline flex items-center justify-between">
        <div className="h-3 w-20 bg-inktext/10 rounded" />
        <div className="h-3 w-16 bg-inktext/10 rounded" />
      </div>
    </div>
  );
}

export default function JobListPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(Number(searchParams.get("page")) || 1);
  const [search, setSearch] = useState(searchParams.get("search") || "");
  const [source, setSource] = useState(searchParams.get("source") || "");
  const [expRange, setExpRange] = useState(searchParams.get("exp") || "");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isFirstRender = useRef(true);
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    setPage(1);
  }, [search, source, expRange]);

  useEffect(() => {
    const params: Record<string, string> = {};
    if (search) params.search = search;
    if (source) params.source = source;
    if (expRange) params.exp = expRange;
    if (page > 1) params.page = String(page);
    setSearchParams(params, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, source, expRange, page]);

  const activeRange = EXPERIENCE_RANGES.find((r) => r.key === expRange);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    listJobs({
      search,
      source,
      page,
      limit: LIMIT,
      expMin: activeRange?.expMin,
      expMax: activeRange?.expMax,
    })
      .then((res) => {
        if (cancelled) return;
        setJobs(shuffle(res.jobs));
        setTotal(res.total);
      })
      .catch((err) => {
        if (cancelled) return;
        // Clear stale results on failure
        setJobs([]);
        setTotal(0);
        setError(err.message || "Something went wrong");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [search, source, expRange, page]);

  const totalPages = Math.max(1, Math.ceil(total / LIMIT));

  return (
    <div className="min-h-screen">
      {/* Hero */}
      <header className="bg-ink text-stock">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 pt-10 pb-8">
          <div className="mb-6">
            <span className="font-['SF_Pro_Display'] font-semibold text-4xl tracking-[0.15em] text-stock/70">
              Dhe Lavoro
            </span>
          </div>
          <h1 className="font-['SF_Pro_Display'] font-semibold text-base sm:text-lg leading-tight">
            Every open pass across
            <br />
            Kerala's IT parks, in one place.
          </h1>
          <p className="mt-3 text-stock/55 text-xs sm:text-sm font-['SF_Pro_Display'] max-w-xl">
            Aggregated from Infopark and Technopark's own listings. Not
            affiliated with either park.
          </p>

          <div className="mt-6">
            <SearchBar
              value={search}
              onChange={setSearch}
              source={source}
              onSourceChange={setSource}
              expRange={expRange}
              onExpRangeChange={setExpRange}
            />
          </div>

          <p className="mt-3 font-mono text-xs text-stock/50">
            {loading ? "scanning…" : `${total.toLocaleString()} active passes`}
          </p>
        </div>
      </header>

      {/* Results */}
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        {error && (
          <div className="rounded-xl border border-gold/40 bg-gold/10 px-4 py-3 text-sm text-inktext mb-6">
            Couldn't reach the terminal — {error}
          </div>
        )}

        {!loading && !error && jobs.length === 0 && (
          <div className="text-center py-20">
            <p className="font-display text-lg text-inktext/70">
              No passes match that search.
            </p>
            <p className="text-sm text-inktext/50 mt-1">
              Try a different role, company, or park.
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {loading
            ? Array.from({ length: 6 }).map((_, i) => (
                <JobCardSkeleton key={i} />
              ))
            : jobs.map((job) => <JobCard key={job.id} job={job} />)}
        </div>

        {!loading && totalPages > 1 && (
          <div className="mt-10 flex items-center justify-center gap-3 font-mono text-sm">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1.5 rounded-lg border border-hairline disabled:opacity-30 hover:bg-surface"
            >
              ← prev
            </button>
            <span className="text-inktext/60">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1.5 rounded-lg border border-hairline disabled:opacity-30 hover:bg-surface"
            >
              next →
            </button>
          </div>
        )}
      </main>

      {/* ===== Footer ===== */}
      <footer className="mt-16 bg-ink text-stock w-screen relative left-1/2 -translate-x-1/2">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 pt-12 pb-8">
          <div className="pb-10 border-b border-stock/10">
            <div>
              <span className="font-['SF_Pro_Display'] font-semibold text-xl">Dhe Lavoro</span>
            </div>
            <p className="mt-2 text-sm text-stock/50 max-w-sm">
              Every open pass across Kerala's IT parks, aggregated from
              Infopark and Technopark's own listings.
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-8 py-10">
            <div>
              <h3 className="font-mono text-xs uppercase tracking-wider text-stock/40 mb-3">
                Browse
              </h3>
              <ul className="space-y-2 text-sm">
                {BROWSE_LINKS.map((l) => (
                  <li key={l.label}>
                    <Link
                      to={l.to}
                      className="text-stock/70 hover:text-stock transition-colors"
                    >
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h3 className="font-mono text-xs uppercase tracking-wider text-stock/40 mb-3">
                Company
              </h3>
              <ul className="space-y-2 text-sm">
                {COMPANY_LINKS.map((l) => (
                  <li key={l.label}>
                    <Link
                      to={l.to}
                      className="text-stock/70 hover:text-stock transition-colors"
                    >
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h3 className="font-mono text-xs uppercase tracking-wider text-stock/40 mb-3">
                Official Sites
              </h3>
              <ul className="space-y-2 text-sm">
                {OFFICIAL_LINKS.map((l) => (
                  <li key={l.label}>
                    <a
                      href={l.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-stock/70 hover:text-stock transition-colors"
                    >
                      {l.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="pt-6 border-t border-stock/10 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-stock/40">
            <p>
              © {new Date().getFullYear()} Dhe Lavoro. Not affiliated with
              Infopark or Technopark.
            </p>
            <p>Job data sourced from Infopark and Technopark's public listings.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}