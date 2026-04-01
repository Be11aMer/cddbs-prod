import axios from "axios";

// On Cloudflare Pages set VITE_API_URL to the Fly.io backend URL.
// Locally and on Render, falls back to /api (nginx proxy handles it).
export const API_URL = import.meta.env.VITE_API_URL || "/api";

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

/** Machine-readable AI provenance — EU AI Act Art. 50 compliance. */
export interface AIMetadata {
  model_id: string;
  prompt_version: string | null;
  generated_at: string;
  quality_score: number | null;
  quality_rating: string | null;
  requires_human_review: boolean;
  disclosure: string;
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
  ai_metadata?: AIMetadata | null;
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
  key_claims: string[] | null;           // specific claims made by this outlet
  omissions: string[] | null;            // key facts from baseline omitted by this outlet
  article_links: { title: string; url: string; date: string }[] | null;
}

export interface CoordinationDetail {
  shared_techniques: string[];
  coordinated_outlets: string[];
  high_divergence_outlet_count: number;
  total_outlet_count: number;
}

export interface TopicRunDetail extends TopicRunStatus {
  baseline_summary: string | null;
  coordination_signal: number | null;    // 0.0-1.0 — coordinated narrative pushing score
  coordination_detail: CoordinationDetail | null;
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

// ---------------------------------------------------------------------------
// Sprint 6: Webhook Configuration
// ---------------------------------------------------------------------------

export interface WebhookConfig {
  id: number;
  url: string;
  events: string[];
  active: boolean;
  created_at: string;
  last_triggered_at: string | null;
  failure_count: number;
}

export interface WebhookCreatePayload {
  url: string;
  events?: string[];
  secret?: string;
}

export async function fetchWebhooks() {
  const { data } = await api.get<WebhookConfig[]>("/webhooks");
  return data;
}

export async function createWebhook(payload: WebhookCreatePayload) {
  const { data } = await api.post<WebhookConfig>("/webhooks", payload);
  return data;
}

export async function deleteWebhook(id: number) {
  const { data } = await api.delete<{ status: string; id: number }>(
    `/webhooks/${id}`
  );
  return data;
}

export async function testWebhook(id: number) {
  const { data } = await api.post<{ delivered: number; webhook_id: number }>(
    `/webhooks/test/${id}`
  );
  return data;
}


// ---------------------------------------------------------------------------
// Threat Briefings (SitReps, Framing, Digests, Quarterly Reports)
// ---------------------------------------------------------------------------

export interface ThreatBriefingItem {
  id: number;
  cluster_id: number | null;
  briefing_type: string; // sitrep | daily_digest | quarterly_report
  title: string | null;
  executive_summary: string | null;
  articles_analyzed: number;
  sources_compared: number;
  quality_score: number | null;
  quality_rating: string | null;
  period_start: string | null;
  period_end: string | null;
  created_at: string | null;
  has_framing_analysis: boolean;
}

export interface SourceFraming {
  source_domain: string;
  source_type: string;
  framing_summary: string;
  key_claims: string[];
  omitted_facts: string[];
  emotional_language_score: number;
  bias_direction: string;
}

export interface FramingDiscrepancy {
  topic: string;
  source_a: string;
  source_b: string;
  assessment: string;
}

export interface FramingAnalysis {
  source_framings: SourceFraming[];
  discrepancies: FramingDiscrepancy[];
  coordination_indicators: string[];
  framing_divergence_score: number;
}

export interface ThreatBriefingDetail extends ThreatBriefingItem {
  briefing_json: Record<string, unknown> | null;
  framing_analysis: FramingAnalysis | null;
}

export interface SchedulerJobStatus {
  name: string;
  description: string;
  interval_hours: number;
  last_run: string | null;
  next_run: string | null;
  run_count: number;
  last_error: string | null;
  is_running: boolean;
}

export async function fetchThreatBriefings(params?: {
  briefing_type?: string;
  limit?: number;
  offset?: number;
}) {
  const { data } = await api.get<ThreatBriefingItem[]>("/threat-briefings", { params });
  return data;
}

export async function fetchLatestThreatBriefings(n = 5) {
  const { data } = await api.get<ThreatBriefingItem[]>("/threat-briefings/latest", {
    params: { n },
  });
  return data;
}

export async function fetchThreatBriefing(id: number) {
  const { data } = await api.get<ThreatBriefingDetail>(`/threat-briefings/${id}`);
  return data;
}

export async function triggerQuarterlyReport(year: number, quarter: number) {
  const { data } = await api.post<ThreatBriefingDetail>("/threat-briefings/quarterly", {
    year,
    quarter,
  });
  return data;
}

export async function fetchSchedulerStatus() {
  const { data } = await api.get<{ jobs: SchedulerJobStatus[] }>("/scheduler/status");
  return data.jobs;
}
