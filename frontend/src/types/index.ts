// frontend/src/types/index.ts

export interface MetricScore {
  id: number;
  metric_name: string;
  score: number;
  threshold: number;
  passed: boolean;
  sample_count: number;
  recorded_at: string;
}

export interface SampleResult {
  id: number;
  sample_index: number;
  query: string;
  context: string;
  expected_answer: string;
  actual_answer: string;
  metric_name: string;
  score: number;
  passed: boolean;
  reasoning: string | null;
  latency_ms: number;
}

export interface EvalRunSummary {
  id: number;
  run_uuid: string;
  prompt_file: string;
  commit_sha: string | null;
  pr_number: string | null;
  pipeline_version: string | null;
  status: RunStatus;
  created_at: string;
  completed_at: string | null;
  total_samples: number;
  error_message: string | null;
  metric_scores: MetricScore[];
}

export interface EvalRunDetail extends EvalRunSummary {
  sample_results: SampleResult[];
}

export type RunStatus = "pending" | "running" | "passed" | "failed" | "regression" | "error";

export interface RunsListResponse {
  total: number;
  page: number;
  page_size: number;
  items: EvalRunSummary[];
}

export interface MetricTrendPoint {
  run_id: number;
  run_uuid: string;
  commit_sha: string | null;
  recorded_at: string;
  score: number;
  threshold: number;
  passed: boolean;
}

export interface MetricTrendResponse {
  metric: string;
  points: MetricTrendPoint[];
}

export interface LatestMetricsResponse {
  metrics: Record<string, MetricScore>;
}

export interface CompareRunsResponse {
  run_a: EvalRunSummary;
  run_b: EvalRunSummary;
  deltas: Record<string, number>;
}

export interface RegressionViolation {
  metric: string;
  baseline: number;
  current: number;
  delta: number;
  threshold: number;
  allowed_delta: number;
}

export interface AppConfig {
  ollama_url: string;
  judge_model: string;
  dataset_path: string;
  enabled_metrics: string[];
  thresholds: Record<string, number>;
  max_concurrent_evals: number;
  judge_timeout_seconds: number;
  regression_allowed_delta: number;
  block_on_regression: boolean;
}

export interface ThresholdUpdateRequest {
  thresholds: Record<string, number>;
}
