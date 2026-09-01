import type { Job, JobListResponse } from "../types";

// Configure via .env: VITE_API_BASE_URL=http://localhost:5000
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

export interface ListJobsParams {
  search?: string;
  source?: string;
  page?: number;
  limit?: number;
}

export async function listJobs(params: ListJobsParams = {}): Promise<JobListResponse> {
  const query = new URLSearchParams();
  if (params.search) query.set("search", params.search);
  if (params.source) query.set("source", params.source);
  if (params.page) query.set("page", String(params.page));
  if (params.limit) query.set("limit", String(params.limit));
  
  // Cache-buster parameter guarantees a fresh request even if browser cache ignores headers
  query.set("_t", String(Date.now()));

  const res = await fetch(`${API_BASE_URL}/api/jobs?${query.toString()}`, {
    cache: "no-store", // Prevents the browser from caching the response
    headers: {
      "Pragma": "no-cache",
      "Cache-Control": "no-cache",
    },
  });
  
  if (!res.ok) {
    throw new Error(`Failed to fetch jobs: ${res.status}`);
  }
  return res.json();
}

export async function getJob(id: number | string): Promise<Job> {
  const res = await fetch(`${API_BASE_URL}/api/jobs/${id}`, {
    cache: "no-store",
  });
  if (res.status === 404) {
    throw new Error("Job not found");
  }
  if (!res.ok) {
    throw new Error(`Failed to fetch job: ${res.status}`);
  }
  return res.json();
}