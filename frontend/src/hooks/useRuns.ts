// frontend/src/hooks/useRuns.ts
import { useCallback, useEffect, useState } from "react";
import { runsApi } from "../api/client";
import type { EvalRunDetail, EvalRunSummary, RunsListResponse } from "../types";

interface UseRunsState {
  runs: EvalRunSummary[];
  total: number;
  page: number;
  pageSize: number;
  loading: boolean;
  error: string | null;
}

interface UseRunsReturn extends UseRunsState {
  setPage: (page: number) => void;
  refresh: () => void;
  deleteRun: (id: number) => Promise<void>;
}

export function useRuns(initialPage = 1, pageSize = 20): UseRunsReturn {
  const [state, setState] = useState<UseRunsState>({
    runs: [],
    total: 0,
    page: initialPage,
    pageSize,
    loading: false,
    error: null,
  });

  const fetchRuns = useCallback(async (page: number) => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data: RunsListResponse = await runsApi.list(page, pageSize);
      setState((s) => ({
        ...s,
        runs: data.items,
        total: data.total,
        page: data.page,
        loading: false,
      }));
    } catch (err) {
      setState((s) => ({
        ...s,
        loading: false,
        error: err instanceof Error ? err.message : "Failed to fetch runs",
      }));
    }
  }, [pageSize]);

  useEffect(() => {
    fetchRuns(state.page);
  }, [state.page, fetchRuns]);

  const setPage = useCallback((page: number) => {
    setState((s) => ({ ...s, page }));
  }, []);

  const refresh = useCallback(() => {
    fetchRuns(state.page);
  }, [fetchRuns, state.page]);

  const deleteRun = useCallback(async (id: number) => {
    await runsApi.delete(id);
    fetchRuns(state.page);
  }, [fetchRuns, state.page]);

  return { ...state, setPage, refresh, deleteRun };
}

interface UseRunDetailState {
  run: EvalRunDetail | null;
  loading: boolean;
  error: string | null;
}

export function useRunDetail(runId: number | null): UseRunDetailState & { refresh: () => void } {
  const [state, setState] = useState<UseRunDetailState>({
    run: null,
    loading: false,
    error: null,
  });

  const fetchRun = useCallback(async () => {
    if (runId === null) return;
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await runsApi.get(runId);
      setState({ run: data, loading: false, error: null });
    } catch (err) {
      setState({
        run: null,
        loading: false,
        error: err instanceof Error ? err.message : "Failed to fetch run",
      });
    }
  }, [runId]);

  useEffect(() => {
    fetchRun();
  }, [fetchRun]);

  return { ...state, refresh: fetchRun };
}
