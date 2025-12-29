import axios from "axios";

export const api = axios.create({
  baseURL: "/api",
});

export interface CreateRunPayload {
  outlet: string;
  url: string;
  country: string;
  num_articles?: number;
  serpapi_key?: string;
  google_api_key?: string;
}

export interface RunStatus {
  id: number;
  outlet: string;
  country?: string;
  created_at: string;
  status: string;
  message?: string | null;
}

export interface ArticleSummary {
  id: number;
  title: string;
  link?: string | null;
  snippet?: string | null;
  date?: string | null;
}

export interface ReportMeta {
  outlet: string;
  url: string;
  country: string;
  analysis_date: string;
  articles_analyzed: number;
}

export interface ReportResponse {
  id: number;
  outlet: string;
  country?: string | null;
  created_at: string;
  status: string;
  message?: string | null;
  meta?: ReportMeta | null;
  final_report?: string | null;
  articles: ArticleSummary[];
}

export async function createAnalysisRun(payload: CreateRunPayload) {
  const { data } = await api.post<RunStatus>("/analysis-runs", payload);
  return data;
}

export async function fetchRuns() {
  const { data } = await api.get<RunStatus[]>("/analysis-runs");
  return data;
}

export async function fetchRun(reportId: number) {
  const { data } = await api.get<ReportResponse>(`/analysis-runs/${reportId}`);
  return data;
}

export interface ApiStatus {
  serpapi: {
    configured: boolean;
    status: "configured" | "not_configured";
    message: string | null;
  };
  gemini: {
    configured: boolean;
    status: "configured" | "not_configured";
    message: string | null;
  };
}

export async function fetchApiStatus() {
  const { data } = await api.get<ApiStatus>("/api-status");
  return data;
}


