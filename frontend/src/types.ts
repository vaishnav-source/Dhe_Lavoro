export interface Job {
  id: number;
  source: string;
  source_job_id: string;
  job_title: string;
  company: string;
  posted_date: string | null;
  closing_date: string | null;
  detail_url: string | null;
  description: string | null;
  short_description: string | null;
  contact_email: string | null;
  status: string;
  experience_min: number | null;
  experience_max: number | null;
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
  page: number;
  limit: number;
}