export interface OpsProbe {
  name: string;
  status: string;
  detail: string;
  mode?: string | null;
}

export interface OpsScheduler {
  status: string;
  enabled: boolean;
  thread_alive: boolean;
  scheduled: number;
  running: number;
  dead_letter: number;
  detail: string;
}

export interface OpsWebhooks {
  received: number;
  processed: number;
  replayed: number;
  failed: number;
}

export interface OpsHttp {
  request_count: number;
  latency_p50_ms: number;
  latency_p95_ms: number;
}

export interface OpsStatus {
  status: string;
  environment: string;
  version: string;
  api_version: string;
  build_sha: string;
  app_name: string;
  timestamp: string;
  api: OpsProbe;
  database: OpsProbe;
  scheduler: OpsScheduler;
  gemini: OpsProbe;
  razorpay: OpsProbe;
  webhooks: OpsWebhooks;
  http: OpsHttp;
  payment_links_sent: number;
  successful_retries: number;
  recovery_actions_executed: number;
}
