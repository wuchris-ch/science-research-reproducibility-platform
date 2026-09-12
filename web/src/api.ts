import type { components } from "./contracts";
export type Parameters = components["schemas"]["Parameters"];
export type Plan = {
  id: string;
  workspace_id: string;
  revision: number;
  state: string;
  body: {
    title: string;
    dataset_id: string;
    recipe: string;
    parameters: Parameters;
    parent_id: string | null;
    reason: string;
    environment: string;
    adaptations: string[];
    plan_hash?: string;
    source_sha256: string;
  };
  history?: unknown[];
};
export type Artifact = { sha256: string; bytes: number };
export type Check = {
  key: string;
  expected: unknown;
  actual: unknown;
  passed: boolean;
  basis: string;
};
export type Run = {
  id: string;
  workspace_id: string;
  plan_id: string;
  state: string;
  epoch: number;
  created: number;
  body: {
    plan: Plan["body"];
    image_id: string;
    artifacts: Record<string, Artifact>;
    diagnostic?: string;
    duration_seconds?: number;
    cached_from?: string;
    comparison?: {
      status: string;
      checks: Check[];
      limitations: string[];
      metrics: Record<string, unknown>;
    };
  };
  reviews?: {
    actor: string;
    body: { status: string; note: string };
    created: number;
  }[];
};
export type Segment = { id: string; kind: string; text: string };
export type Source = {
  id: string;
  title: string;
  authors: string;
  doi: string;
  version: number;
  year: number;
  accession: string;
  recipes: string[];
  sha256: string;
  segments: Segment[];
  geometry?: { page: number; page_size_points: [number,number]; figure_bbox: number[]; caption_bbox: number[]; method_bbox: number[] | null };
};
export type Workspace = { id: string; name: string; role: string };
export type Event = {
  id: number;
  kind: string;
  actor: string;
  created: number;
  run_id?: string;
  body: Record<string, unknown>;
};
let csrf = "";
let bearer = sessionStorage.getItem("oidc-token") || "";
export function setToken(value: string) {
  bearer = value;
  sessionStorage.setItem("oidc-token", value);
}
export async function api<T>(
  path: string,
  body?: unknown,
  method = "POST",
): Promise<T> {
  const response = await fetch("/api" + path, {
    method: body === undefined ? "GET" : method,
    credentials: "same-origin",
    headers: {
      ...(body === undefined
        ? {}
        : {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrf,
            "Idempotency-Key": crypto.randomUUID(),
          }),
      ...(bearer ? { Authorization: "Bearer " + bearer } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `Request failed (${response.status})`);
  }
  return response.json();
}
export async function session() {
  const health = await api<{ identity_mode: string }>("/health");
  if (health.identity_mode === "oidc") {
    await api("/me");
    return "oidc";
  }
  const s = await api<{ csrf: string }>("/session");
  csrf = s.csrf;
  return "local";
}
export async function asset(path: string): Promise<string> {
  const response = await fetch("/api" + path, {
    credentials: "same-origin",
    headers: bearer ? { Authorization: "Bearer " + bearer } : {},
  });
  if (!response.ok) throw new Error("Artifact unavailable");
  return URL.createObjectURL(await response.blob());
}
export async function download(path: string, name: string) {
  const url = await asset(path);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
