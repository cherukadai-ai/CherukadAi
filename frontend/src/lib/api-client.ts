import { env } from "@/lib/env";

/** Problem+json shape returned by the backend's centralized error handler. */
export interface ApiProblemDetails {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  [key: string]: unknown;
}

export class ApiError extends Error {
  readonly status: number;
  readonly problem: ApiProblemDetails | null;

  constructor(status: number, message: string, problem: ApiProblemDetails | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.problem = problem;
  }
}

export interface ApiRequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  /** Skip JSON.stringify for FormData/Blob/etc. payloads. */
  rawBody?: boolean;
}

/**
 * Thin fetch abstraction around the backend API.
 *
 * - Always sends HTTP-only session cookies (`credentials: "include"`), never reads
 *   or stores tokens in JS-accessible storage.
 * - Normalizes non-2xx responses into a typed `ApiError`.
 * - Works from both Server Components/Route Handlers and Client Components.
 */
export async function apiFetch<TResponse>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<TResponse> {
  const { body, rawBody, headers, ...rest } = options;

  const response = await fetch(`${env.apiBaseUrl}${path}`, {
    ...rest,
    credentials: "include",
    headers: {
      ...(rawBody ? {} : { "Content-Type": "application/json" }),
      Accept: "application/json",
      ...headers,
    },
    body: body === undefined ? undefined : rawBody ? (body as BodyInit) : JSON.stringify(body),
  });

  if (!response.ok) {
    let problem: ApiProblemDetails | null = null;
    try {
      problem = await response.json();
    } catch {
      problem = null;
    }
    throw new ApiError(
      response.status,
      problem?.detail ?? `Request to ${path} failed with status ${response.status}`,
      problem,
    );
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }

  return (await response.json()) as TResponse;
}

export const apiClient = {
  get: <T>(path: string, options?: ApiRequestOptions) =>
    apiFetch<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: ApiRequestOptions) =>
    apiFetch<T>(path, { ...options, method: "POST", body }),
  patch: <T>(path: string, body?: unknown, options?: ApiRequestOptions) =>
    apiFetch<T>(path, { ...options, method: "PATCH", body }),
  put: <T>(path: string, body?: unknown, options?: ApiRequestOptions) =>
    apiFetch<T>(path, { ...options, method: "PUT", body }),
  delete: <T>(path: string, options?: ApiRequestOptions) =>
    apiFetch<T>(path, { ...options, method: "DELETE" }),
};
