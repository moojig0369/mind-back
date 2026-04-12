-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- 2. REFERENCE TABLES (AI-ийн саналаас авсан лавлах өгөгдлүүд)
-- UI дээр өнгө, дүрс харуулах болон өгөгдлийн алдаанаас сэргийлнэ.
-- ============================================================

CREATE TABLE public.ref_maslow (
  code text PRIMARY KEY,
  level integer NOT NULL UNIQUE CHECK (level between 1 and 5),
  label_mn text NOT NULL,
  label_en text NOT NULL,
  description text,
  color_hex text,
  icon text
);

CREATE TABLE public.ref_plutchik (
  emotion_key text PRIMARY KEY,
  label_mn text NOT NULL,
  full_name_mn text NOT NULL,
  label_en text NOT NULL,
  emoji text,
  band text NOT NULL CHECK (band in ('lower', 'upper')),
  wheel_order integer NOT NULL,
  color_hex text,
  opposite_emotion text REFERENCES public.ref_plutchik(emotion_key),
  description text
);

CREATE TABLE public.ref_plutchik_dyads (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  emotion_a text NOT NULL REFERENCES public.ref_plutchik(emotion_key),
  emotion_b text NOT NULL REFERENCES public.ref_plutchik(emotion_key),
  dyad_name_en text NOT NULL,
  dyad_name_mn text NOT NULL,
  CONSTRAINT plutchik_dyad_unique UNIQUE (emotion_a, emotion_b)
);

CREATE TABLE public.ref_hawkins_bands (
  code text PRIMARY KEY,
  label_mn text NOT NULL,
  label_en text NOT NULL,
  level_min integer NOT NULL,
  level_max integer NOT NULL,
  description text,
  color_hex text
);

CREATE TABLE public.ref_hawkins (
  level integer PRIMARY KEY,
  band_code text NOT NULL REFERENCES public.ref_hawkins_bands(code),
  label_mn text NOT NULL,
  label_en text NOT NULL,
  emotion_mn text,
  description text,
  is_power_level boolean NOT NULL DEFAULT false,
  calibration_note text
);

-- ============================================================
-- 3. CORE TABLES (Таны үндсэн хүснэгтүүд + Гадаад түлхүүрийн холболтууд)
-- ============================================================

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

CREATE TABLE public.subscriptions (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL UNIQUE REFERENCES public.users(id),
  plan_id uuid NOT NULL REFERENCES public.plans(id),
  started_at timestamp with time zone NOT NULL DEFAULT now(),
  expires_at timestamp with time zone,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT subscriptions_pkey PRIMARY KEY (id)
);

CREATE TABLE public.orders (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES public.users(id),
  plan_id uuid NOT NULL REFERENCES public.plans(id),
  amount numeric NOT NULL,
  status text NOT NULL DEFAULT 'completed'::text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT orders_pkey PRIMARY KEY (id)
);

CREATE TABLE public.user_badges (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES public.users(id),
  badge_id text NOT NULL,
  earned_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT user_badges_pkey PRIMARY KEY (id)
);

CREATE TABLE public.journal_entries (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES public.users(id),
  surface_text text,
  inner_reaction_text text,
  meaning_text text,
  is_encrypted boolean NOT NULL DEFAULT false,
  is_text_saved boolean NOT NULL DEFAULT true,
  embedding vector(768), -- Vector төрлийг тодорхой болгов
  entry_index integer NOT NULL DEFAULT 0,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT journal_entries_pkey PRIMARY KEY (id)
);

-- ============================================================
-- 4. ANALYSIS & GRAPH TABLES (Лавлах хүснэгтүүдтэй холбосон)
-- ============================================================

CREATE TABLE public.journal_analyses (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  entry_id uuid NOT NULL UNIQUE REFERENCES public.journal_entries(id) ON DELETE CASCADE,
  maslow jsonb NOT NULL DEFAULT '[]'::jsonb, 
  plutchik_primary text REFERENCES public.ref_plutchik(emotion_key), -- Гадаад түлхүүр
  plutchik_dyad text, 
  plutchik_intensity double precision CHECK (plutchik_intensity >= 0 AND plutchik_intensity <= 1),
  hawkins_label text,
  hawkins_level integer REFERENCES public.ref_hawkins(level), -- Гадаад түлхүүр
  hawkins_score double precision CHECK (hawkins_score >= 0 AND hawkins_score <= 1),
  processed_at timestamp with time zone,
  CONSTRAINT journal_analyses_pkey PRIMARY KEY (id)
);

CREATE TABLE public.value_nodes (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES public.users(id),
  maslow_category text NOT NULL REFERENCES public.ref_maslow(code), -- Type-г text болгож reference татав
  maslow_value text NOT NULL,
  mention_count integer NOT NULL DEFAULT 1,
  confidence_sum double precision NOT NULL DEFAULT 0.0,
  weight double precision NOT NULL DEFAULT 0.0,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  hawkins_level_sum numeric DEFAULT 0,
  hawkins_entry_count integer DEFAULT 0,
  hawkins_level_avg numeric DEFAULT NULL,
  CONSTRAINT value_nodes_pkey PRIMARY KEY (id)
);

CREATE TABLE public.value_edges (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  node_a_id uuid NOT NULL REFERENCES public.value_nodes(id) ON DELETE CASCADE,
  node_b_id uuid NOT NULL REFERENCES public.value_nodes(id) ON DELETE CASCADE,
  hawkins_level_avg double precision NOT NULL DEFAULT 0,
  hawkins_score_avg double precision NOT NULL DEFAULT 0,
  interaction_count integer NOT NULL DEFAULT 1,
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT value_edges_pkey PRIMARY KEY (id)
);

CREATE TABLE public.value_edges_tracker (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  edge_id uuid NOT NULL REFERENCES public.value_edges(id) ON DELETE CASCADE,
  entry_id uuid REFERENCES public.journal_entries(id) ON DELETE CASCADE,
  hawkins_level integer NOT NULL REFERENCES public.ref_hawkins(level),
  hawkins_score double precision NOT NULL CHECK (hawkins_score >= 0 AND hawkins_score <= 1),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT value_edges_tracker_pkey PRIMARY KEY (id)
);

CREATE TABLE public.emotions (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  value_node_id uuid NOT NULL UNIQUE REFERENCES public.value_nodes(id) ON DELETE CASCADE,
  dominant_primary text REFERENCES public.ref_plutchik(emotion_key),
  dominant_primary_score double precision,
  dominant_dyad text,
  dominant_dyad_score double precision,
  total_entries integer NOT NULL DEFAULT 0,
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT emotions_pkey PRIMARY KEY (id)
);

CREATE TABLE public.emotions_tracker (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  emotion_id uuid NOT NULL REFERENCES public.emotions(id) ON DELETE CASCADE,
  entry_id uuid REFERENCES public.journal_entries(id) ON DELETE CASCADE,
  plutchik_primary text NOT NULL REFERENCES public.ref_plutchik(emotion_key),
  primary_score double precision NOT NULL CHECK (primary_score >= 0 AND primary_score <= 1),
  plutchik_dyad text,
  dyad_score double precision CHECK (dyad_score >= 0 AND dyad_score <= 1),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  is_conflict boolean NOT NULL DEFAULT false,
  CONSTRAINT emotions_tracker_pkey PRIMARY KEY (id)
);

-- ============================================================
-- 5. INSIGHTS & PATTERN DETECTION (Шинээр нэмэгдсэн хэсэг)
-- ============================================================

CREATE TABLE public.seed_insights (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  entry_id uuid NOT NULL UNIQUE REFERENCES public.journal_entries(id) ON DELETE CASCADE,
  mirror text NOT NULL,
  reframe text NOT NULL,
  relief text NOT NULL,
  summary text NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT seed_insights_pkey PRIMARY KEY (id)
);

CREATE TABLE public.deep_insights (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES public.users(id),
  insight_text text NOT NULL,
  recommendations jsonb NOT NULL DEFAULT '[]'::jsonb,
  generated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT deep_insights_pkey PRIMARY KEY (id)
);

-- ШИНЭ: Хэв маяг, дүрэм бүртгэх хүснэгт
CREATE TABLE public.pattern_rules (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  rule_name text UNIQUE NOT NULL,
  rule_type text NOT NULL,
  description text,
  pattern_config jsonb DEFAULT '{}',
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

-- ШИНЭ: Олдсон хэв маягуудыг хадгалах
CREATE TABLE public.detected_patterns (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES public.users(id),
  rule_id uuid REFERENCES public.pattern_rules(id),
  pattern_type text NOT NULL,
  pattern_data jsonb NOT NULL,
  strength_score numeric(5,4) DEFAULT 0.0,
  detected_at timestamp with time zone DEFAULT now(),
  acknowledged boolean DEFAULT false
);

-- ============================================================
-- 6. INDEXES & RLS (Performance & Security)
-- ============================================================

CREATE INDEX idx_journal_entries_user_id ON public.journal_entries(user_id);
CREATE INDEX idx_journal_entries_embedding ON public.journal_entries USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_value_nodes_maslow ON public.value_nodes(maslow_category);
CREATE INDEX idx_emotions_dominant ON public.emotions(dominant_primary);

-- RLS Идэвхжүүлэх (Жишээ)
ALTER TABLE public.journal_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.value_nodes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only access their own entries" 
ON public.journal_entries FOR ALL 
USING (auth.uid() = user_id);

CREATE POLICY "Users can only access their own nodes" 
ON public.value_nodes FOR ALL 
USING (auth.uid() = user_id);