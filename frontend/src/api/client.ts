// frontend/src/api/client.ts
import type {
  AppConfig,
  CompareRunsResponse,
  EvalRunDetail,
  LatestMetricsResponse,
  MetricTrendResponse,
  RunsListResponse,
  ThresholdUpdateRequest,
} from "../types";
import { DEMO_RUNS } from "../demoData";

const BASE_URL = import.meta.env.VITE_API_URL ?? "/api";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
    ...options,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try { const body = await response.json(); detail = body.detail ?? detail; } catch {}
    throw new ApiError(response.status, `${response.status}: ${detail}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function requestWithFallback<T>(path: string, fallback: T, options: RequestInit = {}): Promise<T> {
  try {
    return await request<T>(path, options);
  } catch {
    return fallback;
  }
}

export const runsApi = {
  list(page = 1, pageSize = 20): Promise<RunsListResponse> {
    return requestWithFallback<RunsListResponse>(
      `/runs?page=${page}&page_size=${pageSize}`,
      { total: DEMO_RUNS.length, page, page_size: pageSize, items: DEMO_RUNS as any }
    );
  },
  get(runId: number): Promise<EvalRunDetail> {
    return requestWithFallback<EvalRunDetail>(
      `/runs/${runId}`,
      { ...DEMO_RUNS[0], sample_results: [] } as any
    );
  },
  delete(runId: number): Promise<void> {
    return request<void>(`/runs/${runId}`, { method: "DELETE" });
  },
};

export const metricsApi = {
  trend(metric: string, limit = 20): Promise<MetricTrendResponse> {
    const points = DEMO_RUNS.map((r, i) => ({
      run_id: r.id,
      run_uuid: r.run_uuid,
      commit_sha: r.commit_sha,
      recorded_at: r.created_at,
      score: r.metric_scores.find(m => m.metric_name === metric)?.score ?? 0,
      threshold: r.metric_scores.find(m => m.metric_name === metric)?.threshold ?? 0.7,
      passed: r.metric_scores.find(m => m.metric_name === metric)?.passed ?? false,
    }));
    return requestWithFallback<MetricTrendResponse>(
      `/metrics/trend?metric=${encodeURIComponent(metric)}&limit=${limit}`,
      { metric, points }
    );
  },
  latest(): Promise<LatestMetricsResponse> {
    const metrics: any = {};
    DEMO_RUNS[0].metric_scores.forEach(ms => { metrics[ms.metric_name] = ms; });
    return requestWithFallback<LatestMetricsResponse>("/metrics/latest", { metrics });
  },
  compare(runA: number, runB: number): Promise<CompareRunsResponse> {
    return request<CompareRunsResponse>(`/metrics/compare?run_a=${runA}&run_b=${runB}`);
  },
};

export const configApi = {
  get(): Promise<AppConfig> {
    return requestWithFallback<AppConfig>("/config", {
      ollama_url: "http://localhost:11434",
      judge_model: "mistral",
      dataset_path: "example/golden_dataset.json",
      enabled_metrics: ["answer_relevance", "faithfulness", "semantic_similarity"],
      thresholds: { answer_relevance: 0.70, faithfulness: 0.75, semantic_similarity: 0.65 },
      max_concurrent_evals: 5,
      judge_timeout_seconds: 30,
      regression_allowed_delta: 0.05,
      block_on_regression: true,
    });
  },
  updateThresholds(body: ThresholdUpdateRequest): Promise<any> {
    return request("/config/thresholds", { method: "PUT", body: JSON.stringify(body) });
  },
};

export { ApiError };
