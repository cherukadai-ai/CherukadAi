/** Centralized, validated access to public runtime configuration. */

function requireEnv(name: string, fallback?: string): string {
  const value = process.env[name] ?? fallback;
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

export const env = {
  apiBaseUrl: requireEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1"),
  appName: requireEnv("NEXT_PUBLIC_APP_NAME", "CherukadAI Platform"),
} as const;
