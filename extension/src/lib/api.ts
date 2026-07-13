import type { PackResponse, ScanResponse, StatusResponse } from "../types";

const SERVER_BASE = "http://127.0.0.1:8000";

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${SERVER_BASE}${path}`, init);
  } catch {
    throw new ApiError(
      "Can't reach the local server — is it running on 127.0.0.1:8000?"
    );
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.clone().json();
      if (typeof data?.detail === "string") detail = data.detail;
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new ApiError(detail);
  }
  return res.json() as Promise<T>;
}

export function getStatus(): Promise<StatusResponse> {
  return request<StatusResponse>("/status");
}

export function scanRepo(repoPath: string): Promise<ScanResponse> {
  return request<ScanResponse>("/scan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_path: repoPath }),
  });
}

export function packContext(
  repoId: string,
  task: string,
  tokenBudget: number
): Promise<PackResponse> {
  return request<PackResponse>("/pack", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_id: repoId, task, token_budget: tokenBudget }),
  });
}
