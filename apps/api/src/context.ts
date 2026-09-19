import type { Db } from "@interviewpilot/database";
import type { EnvConfig } from "@interviewpilot/config";
import type { AIProvider } from "@interviewpilot/ai";

export interface AppContext {
  config: EnvConfig;
  db: Db;
  ai: AIProvider;
  startedAt: number;
  requestCount: number;
  errors: Array<{ at: string; message: string }>;
}

export function createAppContext(input: {
  config: EnvConfig;
  db: Db;
  ai: AIProvider;
}): AppContext {
  return {
    ...input,
    startedAt: Date.now(),
    requestCount: 0,
    errors: [],
  };
}
