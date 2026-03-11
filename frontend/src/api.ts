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

export interface ArticleAnalysis {
  propaganda_score?: number | null;
  sentiment?: string | null;
  framing?: string | null;
  key_claims?: string[] | null;
  key_actors?: string[] | null;
  narrative_themes?: string[] | null;
  unverified_statements?: string[] | null;
  analysis_notes?: string | null;
}

export interface ArticleSummary {
  id: number;
  title: string;
  link?: string | null;
  snippet?: string | null;
  date?: string | null;
  analysis?: ArticleAnalysis | null;
}

export interface ReportMeta {
  outlet: string;
  url: string;
  country: string;
  analysis_date: string;
  articles_analyzed: number;
}

export interface StructuredBriefing {
  executive_summary?: string;
  key_findings?: {
    finding: string;
    confidence: string;
    evidence_type: string;
    evidence: string;
  }[];
  subject_profile?: Record<string, unknown>;
  narrative_analysis?: {
    primary_narratives?: {
      narrative: string;
      frequency: string;
      alignment: string;
    }[];
    behavioral_indicators?: {
      indicator: string;
      value: string;
    }[];
    network_context?: {
      label: string;
      value: string;
    }[];
    source_attribution?: {
      role: string;
      content_origin: string;
      amplification_chain: string;
    };
  };
  confidence_assessment?: {
    overall: string;
    factors?: {
      factor: string;
      level: string;
      notes: string;
    }[];
  };
  limitations?: string[];
  methodology?: Record<string, unknown>;
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
  structured_briefing?: StructuredBriefing | null;
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
  // Event intelligence pipeline
  active_events: number;
  active_bursts: number;
  articles_ingested: number;
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


// ---------------------------------------------------------------------------
// v1.3 Network Graph
// ---------------------------------------------------------------------------

export interface NetworkNode {
  id: string;
  label: string;
  type: string;
  size: number;
  color?: string | null;
}

export interface NetworkEdge {
  source: string;
  target: string;
  weight: number;
  label?: string | null;
}

export interface NetworkGraphData {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

export async function fetchOutletNetwork() {
  const { data } = await api.get<NetworkGraphData>("/stats/outlet-network");
  return data;
}


// ---------------------------------------------------------------------------
// Topic Mode
// ---------------------------------------------------------------------------

export interface CreateTopicRunPayload {
  topic: string;
  num_outlets?: number;    // 1-10, default 5
  date_filter?: string;    // h/d/w/m/y, default "m"
  serpapi_key?: string;
  google_api_key?: string;
}

export interface TopicRunStatus {
  id: number;
  topic: string;
  num_outlets: number;
  date_filter: string;
  status: string;          // pending/running/completed/failed
  created_at: string;
  completed_at?: string | null;
  error?: string | null;
  outlets_found: number;
}

export interface TopicOutletResult {
  id: number;
  outlet_name: string;
  outlet_domain: string | null;
  articles_analyzed: number;
  divergence_score: number | null;
  amplification_signal: string | null;   // low/medium/high
  propaganda_techniques: string[] | null;
  framing_summary: string | null;
  divergence_explanation: string | null;
  article_links: { title: string; url: string; date: string }[] | null;
}

export interface TopicRunDetail extends TopicRunStatus {
  baseline_summary: string | null;
  outlet_results: TopicOutletResult[];
}

export async function createTopicRun(payload: CreateTopicRunPayload) {
  const { data } = await api.post<TopicRunStatus>("/topic-runs", payload);
  return data;
}

export async function fetchTopicRuns() {
  const { data } = await api.get<TopicRunStatus[]>("/topic-runs");
  return data;
}

export async function fetchTopicRun(id: number) {
  const { data } = await api.get<TopicRunDetail>(`/topic-runs/${id}`);
  return data;
}


// ---------------------------------------------------------------------------
// Event Intelligence Pipeline
// ---------------------------------------------------------------------------

export interface EventClusterItem {
  id: number;
  title: string | null;
  event_type: string | null;
  countries: string[] | null;
  keywords: string[] | null;
  first_seen: string | null;
  last_seen: string | null;
  article_count: number;
  source_count: number;
  burst_score: number;
  narrative_risk_score: number;
  status: string;
  created_at: string | null;
}

export interface EventClusterDetail extends EventClusterItem {
  entities: Record<string, string[]> | null;
  articles: {
    id: number;
    title: string;
    url: string;
    source_name: string;
    source_domain: string;
    source_type: string;
    published_at: string | null;
    country: string | null;
  }[];
}

export interface NarrativeBurstItem {
  id: number;
  keyword: string;
  baseline_frequency: number | null;
  current_frequency: number | null;
  z_score: number | null;
  cluster_id: number | null;
  detected_at: string | null;
  resolved_at: string | null;
}

export interface EventMapItem {
  country: string;
  event_count: number;
  avg_risk_score: number;
  top_event_type: string | null;
}

export interface CollectorStatusItem {
  name: string;
  last_run: string | null;
  last_article_count: number;
  total_articles_collected: number;
  last_error: string | null;
  is_running: boolean;
}

export async function fetchEventClusters(params?: {
  event_type?: string;
  status?: string;
  min_risk?: number;
  limit?: number;
}) {
  const { data } = await api.get<EventClusterItem[]>("/events", { params });
  return data;
}

export async function fetchEventDetail(id: number) {
  const { data } = await api.get<EventClusterDetail>(`/events/${id}`);
  return data;
}

export async function fetchEventMap() {
  const { data } = await api.get<EventMapItem[]>("/events/map");
  return data;
}

export async function fetchNarrativeBursts() {
  const { data } = await api.get<NarrativeBurstItem[]>("/events/bursts");
  return data;
}

export async function fetchCollectorStatus() {
  const { data } = await api.get<{ collectors: CollectorStatusItem[] }>(
    "/collector/status"
  );
  return data.collectors;
}


// ---------------------------------------------------------------------------
// v1.2 Charts: Activity Timeline & Narrative Frequency
// ---------------------------------------------------------------------------

export interface TimelineBucket {
  hour: string;
  count: number;
  rss: number;
  gdelt: number;
}

export interface NarrativeFrequencyItem {
  narrative_name: string;
  category: string | null;
  total_matches: number;
  high: number;
  medium: number;
  low: number;
}

export async function fetchActivityTimeline(hours = 48) {
  const { data } = await api.get<TimelineBucket[]>("/stats/activity-timeline", {
    params: { hours },
  });
  return data;
}

export async function fetchNarrativeFrequency(limit = 15) {
  const { data } = await api.get<NarrativeFrequencyItem[]>(
    "/stats/narrative-frequency",
    { params: { limit } }
  );
  return data;
}


// ---------------------------------------------------------------------------
// Social Media Analysis
// ---------------------------------------------------------------------------

export interface SocialMediaRunPayload {
  platform: "twitter" | "telegram";
  handle: string;
  google_api_key?: string;
}

export interface SocialMediaRunStatus {
  id: number;
  platform: string;
  handle: string;
  status: string;
  created_at: string;
  message?: string | null;
}

export async function createSocialMediaRun(payload: SocialMediaRunPayload) {
  const { data } = await api.post<SocialMediaRunStatus>(
    "/social-media/analyze",
    payload
  );
  return data;
}

export interface ApiStatusExtended {
  serpapi: { configured: boolean; status: string; message: string | null };
  gemini: { configured: boolean; status: string; message: string | null };
  twitter: { configured: boolean; status: string; message: string | null };
  telegram: { configured: boolean; status: string; message: string | null };
}


// ---------------------------------------------------------------------------
// JSON Export
// ---------------------------------------------------------------------------

export async function exportAnalysisRun(reportId: number): Promise<void> {
  const response = await api.get(`/analysis-runs/${reportId}/export`, {
    responseType: "blob",
  });
  const blob = new Blob([response.data], { type: "application/json" });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const disposition = response.headers["content-disposition"] || "";
  const match = disposition.match(/filename="(.+)"/);
  a.download = match ? match[1] : `cddbs-export-${reportId}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}


// ---------------------------------------------------------------------------
// Metrics
// ---------------------------------------------------------------------------

export interface PlatformMetrics {
  total_analyses: number;
  completed_analyses: number;
  failed_analyses: number;
  success_rate: number | null;
  avg_quality_score: number | null;
  avg_duration_seconds: number | null;
  total_narratives_matched: number;
  total_articles_ingested: number;
  active_event_clusters: number;
  active_narrative_bursts: number;
  top_countries: { country: string; count: number }[];
  top_narratives: { narrative_id: string; name: string; total_matches: number }[];
}

export async function fetchMetrics() {
  const { data } = await api.get<PlatformMetrics>("/metrics");
  return data;
}


// ---------------------------------------------------------------------------
// Quality Trends
// ---------------------------------------------------------------------------

export interface QualityTrendPoint {
  report_id: number;
  outlet: string;
  created_at: string;
  quality_score: number | null;
  quality_rating: string | null;
}

export interface QualityTrendsData {
  trends: QualityTrendPoint[];
  outlet_averages: Record<string, number>;
}

export async function fetchQualityTrends(outlet?: string) {
  const { data } = await api.get<QualityTrendsData>("/stats/quality-trends", {
    params: outlet ? { outlet } : undefined,
  });
  return data;
}
