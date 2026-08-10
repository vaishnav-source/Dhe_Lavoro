import { useEffect, useState } from "react";
import { listJobs } from "../api/client";
import type { Job } from "../types";
import JobCard from "../components/JobCard";
import SearchBar from "../components/SearchBar";

const LIMIT = 20;

export default function JobListPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [source, setSource] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setPage(1);
  }, [search, source]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    listJobs({ search, source, page, limit: LIMIT })
      .then((res) => {
        if (cancelled) return;
        setJobs(res.jobs);
        setTotal(res.total);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message || "Something went wrong");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [search, source, page]);

  const totalPages = Math.max(1, Math.ceil(total / LIMIT));

  return (
    <div className="min-h-screen">
      {/* Hero / access terminal */}
      <header className="bg-ink text-stock">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 pt-10 pb-8">
          <div className="flex items-center gap-2 mb-6">
            <span className="w-3 h-3 rounded-full bg-gold" aria-hidden="true" />
            <span className="font-mono text-xs uppercase tracking-[0.2em] text-stock/60">
              access terminal
            </span>
          </div>
          <h1 className="font-display font-semibold text-3xl sm:text-4xl leading-tight">
            Every open pass across
            <br />
            Kerala's IT parks, in one place.
          </h1>
          <p className="mt-3 text-stock/60 text-sm font-body max-w-xl">
            Aggregated from Infopark and Technopark's own listings. Not
            affiliated with either park.
          </p>

          <div className="mt-6">
            <SearchBar
              value={search}
              onChange={setSearch}
              source={source}
              onSourceChange={setSource}
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
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </div>

        {totalPages > 1 && (
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
    </div>
  );
}