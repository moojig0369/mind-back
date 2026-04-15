-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.deep_insights (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL,
  insight_text text NOT NULL,
  recommendations jsonb NOT NULL DEFAULT '[]'::jsonb,
  generated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT deep_insights_pkey PRIMARY KEY (id),
  CONSTRAINT deep_insights_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.detected_patterns (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL,
  rule_id uuid,
  pattern_type text NOT NULL,
  pattern_data jsonb NOT NULL,
  strength_score numeric DEFAULT 0.0,
  detected_at timestamp with time zone DEFAULT now(),
  acknowledged boolean DEFAULT false,
  run_id uuid,
  related_node_ids ARRAY,
  related_entry_ids ARRAY,
  window_days integer,
  CONSTRAINT detected_patterns_pkey PRIMARY KEY (id),
  CONSTRAINT detected_patterns_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT detected_patterns_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES public.pattern_rules(id),
  CONSTRAINT detected_patterns_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.pattern_runs(id)
);
CREATE TABLE public.emotions (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  value_node_id uuid NOT NULL UNIQUE,
  dominant_primary text,
  dominant_primary_score double precision,
  dominant_dyad text,
  dominant_dyad_score double precision,
  total_entries integer NOT NULL DEFAULT 0,
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT emotions_pkey PRIMARY KEY (id),
  CONSTRAINT emotions_value_node_id_fkey FOREIGN KEY (value_node_id) REFERENCES public.value_nodes(id),
  CONSTRAINT emotions_dominant_primary_fkey FOREIGN KEY (dominant_primary) REFERENCES public.ref_plutchik(emotion_key)
);
CREATE TABLE public.emotions_tracker (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  emotion_id uuid NOT NULL,
  entry_id uuid,
  plutchik_primary text NOT NULL,
  primary_score double precision NOT NULL CHECK (primary_score >= 0::double precision AND primary_score <= 1::double precision),
  plutchik_dyad text,
  dyad_score double precision CHECK (dyad_score >= 0::double precision AND dyad_score <= 1::double precision),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  is_conflict boolean NOT NULL DEFAULT false,
  CONSTRAINT emotions_tracker_pkey PRIMARY KEY (id),
  CONSTRAINT emotions_tracker_emotion_id_fkey FOREIGN KEY (emotion_id) REFERENCES public.emotions(id),
  CONSTRAINT emotions_tracker_entry_id_fkey FOREIGN KEY (entry_id) REFERENCES public.journal_entries(id),
  CONSTRAINT emotions_tracker_plutchik_primary_fkey FOREIGN KEY (plutchik_primary) REFERENCES public.ref_plutchik(emotion_key)
);
CREATE TABLE public.human_insights (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL,
  pattern_run_id uuid,
  insight_text text NOT NULL,
  highlight_type text,
  strength_score numeric DEFAULT 0,
  generated_at timestamp with time zone DEFAULT now(),
  acknowledged boolean DEFAULT false,
  CONSTRAINT human_insights_pkey PRIMARY KEY (id),
  CONSTRAINT human_insights_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT human_insights_pattern_run_id_fkey FOREIGN KEY (pattern_run_id) REFERENCES public.pattern_runs(id)
);
CREATE TABLE public.journal_analyses (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  entry_id uuid NOT NULL UNIQUE,
  maslow jsonb NOT NULL DEFAULT '[]'::jsonb,
  plutchik_primary text,
  plutchik_dyad text,
  plutchik_intensity double precision CHECK (plutchik_intensity >= 0::double precision AND plutchik_intensity <= 1::double precision),
  hawkins_label text,
  hawkins_level integer,
  hawkins_score double precision CHECK (hawkins_score >= 0::double precision AND hawkins_score <= 1::double precision),
  processed_at timestamp with time zone,
  CONSTRAINT journal_analyses_pkey PRIMARY KEY (id),
  CONSTRAINT journal_analyses_entry_id_fkey FOREIGN KEY (entry_id) REFERENCES public.journal_entries(id),
  CONSTRAINT journal_analyses_plutchik_primary_fkey FOREIGN KEY (plutchik_primary) REFERENCES public.ref_plutchik(emotion_key),
  CONSTRAINT journal_analyses_hawkins_label_fkey FOREIGN KEY (hawkins_label) REFERENCES public.ref_hawkins(label_en)
);
CREATE TABLE public.journal_entries (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL,
  surface_text text,
  inner_reaction_text text,
  meaning_text text,
  surface_text_enc bytea,
  inner_reaction_text_enc bytea,
  meaning_text_enc bytea,
  is_encrypted boolean NOT NULL DEFAULT false,
  is_text_saved boolean NOT NULL DEFAULT true,
  embedding USER-DEFINED,
  entry_index integer NOT NULL DEFAULT 0,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT journal_entries_pkey PRIMARY KEY (id),
  CONSTRAINT journal_entries_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.orders (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL,
  plan_id uuid NOT NULL,
  amount numeric NOT NULL,
  status text NOT NULL DEFAULT 'completed'::text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT orders_pkey PRIMARY KEY (id),
  CONSTRAINT orders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT orders_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.plans(id)
);
CREATE TABLE public.pattern_rules (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  rule_name text NOT NULL UNIQUE,
  rule_type text NOT NULL,
  description text,
  pattern_config jsonb DEFAULT '{}'::jsonb,
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  window_days integer DEFAULT 7,
  CONSTRAINT pattern_rules_pkey PRIMARY KEY (id)
);
CREATE TABLE public.pattern_runs (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL,
  run_started_at timestamp with time zone DEFAULT now(),
  run_finished_at timestamp with time zone,
  status text NOT NULL DEFAULT 'running'::text CHECK (status = ANY (ARRAY['running'::text, 'completed'::text, 'failed'::text])),
  CONSTRAINT pattern_runs_pkey PRIMARY KEY (id),
  CONSTRAINT pattern_runs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.plans (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  name text NOT NULL UNIQUE,
  duration_days integer,
  price numeric NOT NULL DEFAULT 0,
  currency text NOT NULL DEFAULT 'MNT'::text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  type text,
  CONSTRAINT plans_pkey PRIMARY KEY (id)
);
CREATE TABLE public.ref_hawkins (
  level integer NOT NULL,
  band_code text NOT NULL,
  label_mn text NOT NULL,
  label_en text NOT NULL UNIQUE,
  emotion_mn text,
  description text,
  is_power_level boolean NOT NULL DEFAULT false,
  calibration_note text,
  CONSTRAINT ref_hawkins_pkey PRIMARY KEY (level),
  CONSTRAINT ref_hawkins_band_code_fkey FOREIGN KEY (band_code) REFERENCES public.ref_hawkins_bands(code)
);
CREATE TABLE public.ref_hawkins_bands (
  code text NOT NULL,
  label_mn text NOT NULL,
  label_en text NOT NULL,
  level_min integer NOT NULL,
  level_max integer NOT NULL,
  description text,
  color_hex text,
  CONSTRAINT ref_hawkins_bands_pkey PRIMARY KEY (code)
);
CREATE TABLE public.ref_maslow (
  code text NOT NULL,
  level integer NOT NULL UNIQUE CHECK (level >= 1 AND level <= 5),
  label_mn text NOT NULL,
  label_en text NOT NULL,
  description text,
  color_hex text,
  icon text,
  CONSTRAINT ref_maslow_pkey PRIMARY KEY (code)
);
CREATE TABLE public.ref_plutchik (
  emotion_key text NOT NULL,
  label_mn text NOT NULL,
  full_name_mn text NOT NULL,
  label_en text NOT NULL,
  emoji text,
  band text NOT NULL CHECK (band = ANY (ARRAY['lower'::text, 'upper'::text])),
  wheel_order integer NOT NULL,
  color_hex text,
  opposite_emotion text,
  description text,
  CONSTRAINT ref_plutchik_pkey PRIMARY KEY (emotion_key),
  CONSTRAINT ref_plutchik_opposite_emotion_fkey FOREIGN KEY (opposite_emotion) REFERENCES public.ref_plutchik(emotion_key)
);
CREATE TABLE public.ref_plutchik_dyads (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  emotion_a text NOT NULL,
  emotion_b text NOT NULL,
  dyad_name_en text NOT NULL,
  dyad_name_mn text NOT NULL,
  CONSTRAINT ref_plutchik_dyads_pkey PRIMARY KEY (id),
  CONSTRAINT ref_plutchik_dyads_emotion_a_fkey FOREIGN KEY (emotion_a) REFERENCES public.ref_plutchik(emotion_key),
  CONSTRAINT ref_plutchik_dyads_emotion_b_fkey FOREIGN KEY (emotion_b) REFERENCES public.ref_plutchik(emotion_key)
);
CREATE TABLE public.seed_insights (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  entry_id uuid NOT NULL UNIQUE,
  mirror text NOT NULL,
  reframe text NOT NULL,
  relief text NOT NULL,
  summary text NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT seed_insights_pkey PRIMARY KEY (id),
  CONSTRAINT seed_insights_entry_id_fkey FOREIGN KEY (entry_id) REFERENCES public.journal_entries(id)
);
CREATE TABLE public.subscriptions (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL UNIQUE,
  plan_id uuid NOT NULL,
  started_at timestamp with time zone NOT NULL DEFAULT now(),
  expires_at timestamp with time zone,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT subscriptions_pkey PRIMARY KEY (id),
  CONSTRAINT subscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT subscriptions_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.plans(id)
);
CREATE TABLE public.user_badges (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL,
  badge_id text NOT NULL,
  earned_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT user_badges_pkey PRIMARY KEY (id),
  CONSTRAINT user_badges_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.users (
  id uuid NOT NULL,
  email text NOT NULL,
  display_name text,
  avatar_url text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  tier text NOT NULL DEFAULT 'free'::text CHECK (tier = ANY (ARRAY['free'::text, 'premium'::text, 'pro'::text, 'admin'::text])),
  tier_expires_at timestamp with time zone,
  CONSTRAINT users_pkey PRIMARY KEY (id),
  CONSTRAINT users_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id)
);
CREATE TABLE public.value_edges (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  node_a_id uuid NOT NULL,
  node_b_id uuid NOT NULL,
  hawkins_level_avg double precision NOT NULL DEFAULT 0,
  hawkins_score_avg double precision NOT NULL DEFAULT 0,
  interaction_count integer NOT NULL DEFAULT 1,
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  edge_type text DEFAULT 'correlate'::text CHECK (edge_type = ANY (ARRAY['reinforce'::text, 'conflict'::text, 'cause'::text, 'correlate'::text])),
  CONSTRAINT value_edges_pkey PRIMARY KEY (id),
  CONSTRAINT value_edges_node_a_id_fkey FOREIGN KEY (node_a_id) REFERENCES public.value_nodes(id),
  CONSTRAINT value_edges_node_b_id_fkey FOREIGN KEY (node_b_id) REFERENCES public.value_nodes(id)
);
CREATE TABLE public.value_edges_tracker (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  edge_id uuid NOT NULL,
  entry_id uuid,
  hawkins_level integer NOT NULL,
  hawkins_score double precision NOT NULL CHECK (hawkins_score >= 0::double precision AND hawkins_score <= 1::double precision),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT value_edges_tracker_pkey PRIMARY KEY (id),
  CONSTRAINT value_edges_tracker_edge_id_fkey FOREIGN KEY (edge_id) REFERENCES public.value_edges(id),
  CONSTRAINT value_edges_tracker_entry_id_fkey FOREIGN KEY (entry_id) REFERENCES public.journal_entries(id)
);
CREATE TABLE public.value_nodes (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL,
  maslow_category text NOT NULL,
  maslow_value text NOT NULL,
  mention_count integer NOT NULL DEFAULT 1,
  confidence_sum double precision NOT NULL DEFAULT 0.0,
  weight double precision NOT NULL DEFAULT 0.0,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  hawkins_level_sum numeric DEFAULT 0,
  hawkins_entry_count integer DEFAULT 0,
  hawkins_level_avg numeric,
  CONSTRAINT value_nodes_pkey PRIMARY KEY (id),
  CONSTRAINT value_nodes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT value_nodes_maslow_category_fkey FOREIGN KEY (maslow_category) REFERENCES public.ref_maslow(code)
);