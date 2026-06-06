// frontend/src/hooks/useMetricTrend.ts
import { useCallback, useEffect, useState } from "react";
import { metricsApi } from "../api/client";
import type { AppConfig, LatestMetricsResponse, MetricTrendResponse } from "../types";
import { configApi } from "../api/client";

interface UseMetricTrendState {
  data: MetricTrendResponse | null;
  loading: boolean;
  error: string | null;
}

export function useMetricTrend(
  metric: string,
  limit = 20
): UseMetricTrendState & { refresh: () => void } {
  const [state, setState] = useState<UseMetricTrendState>({
    data: null,
    loading: false,
    error: null,
  });

  const fetchTrend = useCallback(async () => {
    if (!metric) return;
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await metricsApi.trend(metric, limit);
      setState({ data, loading: false, error: null });
    } catch (err) {
      setState({
        data: null,
        loading: false,
        error: err instanceof Error ? err.message : "Failed to fetch trend",
      });
    }
  }, [metric, limit]);

  useEffect(() => {
    fetchTrend();
  }, [fetchTrend]);

  return { ...state, refresh: fetchTrend };
}

interface UseLatestMetricsState {
  data: LatestMetricsResponse | null;
  loading: boolean;
  error: string | null;
}

export function useLatestMetrics(): UseLatestMetricsState & { refresh: () => void } {
  const [state, setState] = useState<UseLatestMetricsState>({
    data: null,
    loading: false,
    error: null,
  });

  const fetchLatest = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await metricsApi.latest();
      setState({ data, loading: false, error: null });
    } catch (err) {
      setState({
        data: null,
        loading: false,
        error: err instanceof Error ? err.message : "Failed to fetch latest metrics",
      });
    }
  }, []);

  useEffect(() => {
    fetchLatest();
  }, [fetchLatest]);

  return { ...state, refresh: fetchLatest };
}

interface UseConfigState {
  config: AppConfig | null;
  loading: boolean;
  error: string | null;
}

export function useConfig(): UseConfigState & { refresh: () => void } {
  const [state, setState] = useState<UseConfigState>({
    config: null,
    loading: false,
    error: null,
  });

  const fetchConfig = useCallback(async () => {
    setState((s) => ({ ...s, loading: true }));
    try {
      const config = await configApi.get();
      setState({ config, loading: false, error: null });
    } catch (err) {
      setState({
        config: null,
        loading: false,
        error: err instanceof Error ? err.message : "Failed to load config",
      });
    }
  }, []);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  return { ...state, refresh: fetchConfig };
}
