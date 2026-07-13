export interface RepoInfo {
  repo_id: string;
  repo_path: string;
  last_scanned_at: string;
  file_count: number;
  chunk_count: number;
}

export interface StatusResponse {
  status: string;
  indexed_repos: RepoInfo[];
}

export interface ScanResponse {
  repo_id: string;
  repo_path: string;
  files_scanned: number;
  files_skipped: number;
  chunks_indexed: number;
}

export interface PackedFileInfo {
  path: string;
  chunk_count: number;
  token_count: number;
  relevance_score: number;
  content: string;
}

export interface PackResponse {
  bundle: string;
  token_count: number;
  token_budget: number;
  task: string;
  files: PackedFileInfo[];
}

export const TOKEN_BUDGET_PRESETS = [
  { label: "8k", value: 8192 },
  { label: "32k", value: 32768 },
  { label: "100k", value: 100000 },
] as const;
