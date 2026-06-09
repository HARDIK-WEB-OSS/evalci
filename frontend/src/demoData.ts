export const DEMO_RUNS = [
  {
    id: 1,
    run_uuid: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    prompt_file: "example/prompts/rag_answer.txt",
    commit_sha: "40a0a6b",
    pr_number: "3",
    status: "passed",
    created_at: new Date(Date.now() - 3600000).toISOString(),
    completed_at: new Date(Date.now() - 3540000).toISOString(),
    total_samples: 10,
    error_message: null,
    pipeline_version: "0.1.0",
    metric_scores: [
      { id: 1, metric_name: "answer_relevance", score: 0.97, threshold: 0.70, passed: true, sample_count: 10, recorded_at: new Date().toISOString() },
      { id: 2, metric_name: "faithfulness", score: 0.96, threshold: 0.75, passed: true, sample_count: 10, recorded_at: new Date().toISOString() },
      { id: 3, metric_name: "semantic_similarity", score: 0.83, threshold: 0.65, passed: true, sample_count: 10, recorded_at: new Date().toISOString() },
    ]
  },
  {
    id: 2,
    run_uuid: "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    prompt_file: "example/prompts/summarizer.txt",
    commit_sha: "1ba9c9f",
    pr_number: "2",
    status: "passed",
    created_at: new Date(Date.now() - 7200000).toISOString(),
    completed_at: new Date(Date.now() - 7140000).toISOString(),
    total_samples: 10,
    error_message: null,
    pipeline_version: "0.1.0",
    metric_scores: [
      { id: 4, metric_name: "answer_relevance", score: 0.96, threshold: 0.70, passed: true, sample_count: 10, recorded_at: new Date().toISOString() },
      { id: 5, metric_name: "faithfulness", score: 1.00, threshold: 0.75, passed: true, sample_count: 10, recorded_at: new Date().toISOString() },
      { id: 6, metric_name: "semantic_similarity", score: 0.80, threshold: 0.65, passed: true, sample_count: 10, recorded_at: new Date().toISOString() },
    ]
  },
  {
    id: 3,
    run_uuid: "c3d4e5f6-a7b8-9012-cdef-123456789012",
    prompt_file: "example/prompts/rag_answer.txt",
    commit_sha: "339b49f",
    pr_number: "1",
    status: "failed",
    created_at: new Date(Date.now() - 86400000).toISOString(),
    completed_at: new Date(Date.now() - 86340000).toISOString(),
    total_samples: 10,
    error_message: null,
    pipeline_version: "0.1.0",
    metric_scores: [
      { id: 7, metric_name: "answer_relevance", score: 0.61, threshold: 0.70, passed: false, sample_count: 10, recorded_at: new Date().toISOString() },
      { id: 8, metric_name: "faithfulness", score: 0.58, threshold: 0.75, passed: false, sample_count: 10, recorded_at: new Date().toISOString() },
      { id: 9, metric_name: "semantic_similarity", score: 0.71, threshold: 0.65, passed: true, sample_count: 10, recorded_at: new Date().toISOString() },
    ]
  }
];
