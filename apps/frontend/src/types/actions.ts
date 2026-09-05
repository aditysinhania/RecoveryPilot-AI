export const ACTION_CHIPS = ["Scheduled", "Link Sent", "Retrying", "Delivered", "Failed"] as const;

export type ActionChip = (typeof ACTION_CHIPS)[number];

export interface ActionDelivery {
  channel: string;
  status: string;
  provider: string;
  provider_message_id?: string | null;
  rate_limited?: boolean;
  skipped_reason?: string | null;
  sent_at?: string | null;
}

export interface ActionExecution {
  execution_id: string;
  recovery_case_id: string;
  idempotency_key: string;
  planner_strategy: string;
  action_type: string;
  display_status: string;
  execution_status: string;
  action_chip: ActionChip | string;
  scheduled_time?: string | null;
  executed_time?: string | null;
  retry_attempts: number;
  payment_link?: string | null;
  delivery_status?: string | null;
  deliveries: ActionDelivery[];
  request_id: string;
  correlation_id: string;
  replayed: boolean;
  dead_lettered: boolean;
  policy_reason?: string | null;
  razorpay_resource_id?: string | null;
  metadata: Record<string, unknown>;
}

export interface ActionStatus {
  recovery_case_id: string;
  latest: ActionExecution | null;
  history: ActionExecution[];
  active_scheduler_queue: number;
  scheduler_queue?: SchedulerQueueMetrics;
}

export interface SchedulerQueueMetrics {
  scheduled: number;
  running: number;
  delayed: number;
  dead_letter: number;
}

export interface ActionDashboardSummary {
  scheduled_actions_today: number;
  payment_links_sent: number;
  successful_retries: number;
  failed_deliveries: number;
  active_scheduler_queue: number;
  scheduler_queue?: SchedulerQueueMetrics;
  chips: Record<string, string>;
}
