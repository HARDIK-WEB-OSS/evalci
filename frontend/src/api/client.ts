// frontend/src/api/client.ts
import type {
  AppConfig,
  CompareRunsResponse,
  EvalRunDetail,
  EvalRunSummary,
  LatestMetricsResponse,
  MetricTrendResponse,
  RunsListResponse,
  ThresholdUpdateRequest,
} from "../types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "/api";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore parse errors
    }
    throw new ApiError(response.status, `${response.status}: ${detail}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

// ── Runs ───────────────────────────────────────────────────────────────────

export const runsApi = {
  list(page = 1, pageSize = 20): Promise<RunsListResponse> {
    return request<RunsListResponse>(
      `/runs?page=${page}&page_size=${pageSize}`
    );
  },

  get(runId: number): Promise<EvalRunDetail> {
    return request<EvalRunDetail>(`/runs/${runId}`);
  },

  delete(runId: number): Promise<void> {
    return request<void>(`/runs/${runId}`, { method: "DELETE" });
  },
};

// ── Metrics ────────────────────────────────────────────────────────────────

export const metricsApi = {
  trend(metric: string, limit = 20): Promise<MetricTrendResponse> {
    return request<MetricTrendResponse>(
      `/metrics/trend?metric=${encodeURIComponent(metric)}&limit=${limit}`
    );
  },

  latest(): Promise<LatestMetricsResponse> {
    return request<LatestMetricsResponse>("/metrics/latest");
  },

  compare(runA: number, runB: number): Promise<CompareRunsResponse> {
    return request<CompareRunsResponse>(
      `/metrics/compare?run_a=${runA}&run_b=${runB}`
    );
  },
};

// ── Config ─────────────────────────────────────────────────────────────────

export const configApi = {
  get(): Promise<AppConfig> {
    return request<AppConfig>("/config");
  },

  updateThresholds(body: ThresholdUpdateRequest): Promise<{ updated: boolean; thresholds: Record<string, number> }> {
    return request("/config/thresholds", {
      method: "PUT",
      body: JSON.stringify(body),
    });
  },
};

export { ApiError };
