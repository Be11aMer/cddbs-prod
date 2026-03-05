import axios from "axios";

export const API_URL = "/api";

export const api = axios.create({
  baseURL: API_URL,
});

export async function wakeUpBackend() {
  try {
    // Ping health endpoint to wake up service
    await fetch(`${API_URL}/health`, {
      method: "GET",
      signal: AbortSignal.timeout(30000), // 30s timeout
    });
  } catch (error) {
    console.log("Backend waking up from cold start...", error);
  }
}

export interface CreateRunPayload {
  outlet: string;
  url: string;
  country: string;
  num_articles?: number;
  serpapi_key?: string;
  google_api_key?: string;
  date_filter?: string;
}

export interface RunStatus {
  id: number;
  outlet: string;
  country?: string;
  created_at: string;
  status: string;
  message?: string | null;
  quality_score?: number | null;
  quality_rating?: string | null;
  narrative_count?: number | null;
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
  tldr_summary?: string | null;
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


// ---------------------------------------------------------------------------
// Sprint 4: Quality & Narrative Types
// ---------------------------------------------------------------------------

export interface QualityDimension {
  score: number;
  max: number;
  issues: string[];
}

export interface QualityResponse {
  report_id: number;
  total_score: number | null;
  max_score: number;
  rating: string | null;
  dimensions: Record<string, QualityDimension> | null;
  prompt_version: string | null;
}

export interface NarrativeMatchItem {
  id: number;
  narrative_id: string;
  narrative_name: string;
  category: string | null;
  confidence: string | null;
  matched_keywords: string[] | null;
  match_count: number;
}

export interface NarrativeInfo {
  id: string;
  name: string;
  category_id: string;
  category_name: string;
  description: string;
  keywords: string[];
  frequency: string;
  active: boolean;
}

export async function fetchQuality(reportId: number) {
  const { data } = await api.get<QualityResponse>(
    `/analysis-runs/${reportId}/quality`
  );
  return data;
}

export async function fetchNarrativeMatches(reportId: number) {
  const { data } = await api.get<NarrativeMatchItem[]>(
    `/analysis-runs/${reportId}/narratives`
  );
  return data;
}

export async function fetchNarrativesDb() {
  const { data } = await api.get<NarrativeInfo[]>("/narratives");
  return data;
}

// ---------------------------------------------------------------------------
// Feedback
// ---------------------------------------------------------------------------

export interface FeedbackPayload {
  tester_name?: string;
  tester_role?: string;
  overall_rating: number;
  accuracy_rating: number;
  usability_rating: number;
  bugs_encountered: string;
  misleading_outputs?: string;
  missing_features?: string;
  ux_pain_points?: string;
  professional_concerns?: string;
  would_recommend?: string;
  additional_comments?: string;
}

export async function submitFeedback(payload: FeedbackPayload) {
  const { data } = await api.post("/feedback", payload);
  return data;
}


// ---------------------------------------------------------------------------
// Monitoring Dashboard
// ---------------------------------------------------------------------------

export interface GlobalStats {
  total_analyses: number;
  countries_monitored: number;
  total_narratives_detected: number;
  active_runs: number;
  completed_runs: number;
  failed_runs: number;
  avg_quality_score: number | null;
}

export interface CountryStatItem {
  country: string;
  run_count: number;
  completed_count: number;
  narrative_count: number;
  avg_quality: number | null;
  risk_score: number;
}

export interface NarrativeTrendItem {
  narrative_id: string;
  narrative_name: string;
  category: string | null;
  total_matches: number;
  report_count: number;
  confidence_high: number;
  confidence_medium: number;
  confidence_low: number;
}

export interface FeedItem {
  title: string;
  url: string;
  domain: string;
  source_country: string | null;
  published: string;
  language: string;
}

export interface MonitoringFeedResponse {
  items: FeedItem[];
  source: string;
  fetched_at: string;
}

export async function fetchGlobalStats() {
  const { data } = await api.get<GlobalStats>("/stats/global");
  return data;
}

export async function fetchStatsByCountry() {
  const { data } = await api.get<CountryStatItem[]>("/stats/by-country");
  return data;
}

export async function fetchNarrativeTrends() {
  const { data } = await api.get<NarrativeTrendItem[]>("/stats/narrative-trends");
  return data;
}

export async function fetchMonitoringFeed() {
  const { data } = await api.get<MonitoringFeedResponse>("/monitoring/feed");
  return data;
}
