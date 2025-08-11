ALTER TABLE public.notifications_queue
  ADD COLUMN IF NOT EXISTS provider text,
  ADD COLUMN IF NOT EXISTS provider_message_id text,
  ADD COLUMN IF NOT EXISTS provider_status text,
  ADD COLUMN IF NOT EXISTS webhook_payload jsonb,
  ADD COLUMN IF NOT EXISTS webhook_received_at timestamp,
  ADD COLUMN IF NOT EXISTS attempt_count int NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS next_attempt_at timestamp,
  ADD COLUMN IF NOT EXISTS interaction_kind text
    CHECK (interaction_kind IN ('ask_details')),
  ADD COLUMN IF NOT EXISTS responded boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS response_value text,
  ADD COLUMN IF NOT EXISTS response_at timestamp,
  ADD COLUMN IF NOT EXISTS correlation_id uuid DEFAULT gen_random_uuid();

CREATE INDEX IF NOT EXISTS idx_nq_provider_msg_id
  ON public.notifications_queue(provider_message_id);

CREATE INDEX IF NOT EXISTS idx_nq_correlation
  ON public.notifications_queue(correlation_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_nq_dedup
ON public.notifications_queue (user_id, channel, alert_type, entity_type, entity_id, saved_search_id)
WHERE status IN ('pending','sent');
