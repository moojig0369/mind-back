-- ============================================================
-- SEED.SQL - MINDSTEPS JOURNAL GRAPH SYSTEM
-- Combined migrations V4 & V5 with initial seed data
-- Run this on a fresh database to set up all tables and reference data
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- 1. REFERENCE TABLES (from migration_v4.sql)
-- ============================================================

-- Maslow's Hierarchy of Needs
create table if not exists public.ref_maslow (
  code         text    primary key,
  level        integer not null unique check (level between 1 and 5),
  label_mn     text    not null,
  label_en     text    not null,
  description  text,
  color_hex    text,
  icon         text
);

insert into public.ref_maslow
  (code, level, label_mn, label_en, description, color_hex, icon)
values
  ('physiological',      1, 'Физиологийн хэрэгцээ',      'Physiological',      'Хоол, ус, нойр, дулаан',                      '#ef4444', '🍎'),
  ('safety',             2, 'Аюулгүй байдал',             'Safety',             'Аюулгүй орчин, тогтвортой байдал',            '#f97316', '🛡️'),
  ('social',             3, 'Нийгмийн хэрэгцээ',          'Social',             'Харилцаа, хайр, хамт олон',                   '#eab308', '🤝'),
  ('esteem',             4, 'Хүндлэл',                    'Esteem',             'Өөрийгөө үнэлэх, нийгмийн хүлээн зөвшөөрөлт','#22c55e', '⭐'),
  ('self_actualization', 5, 'Өөрийгөө бүрэн илэрхийлэх', 'Self-Actualization', 'Чадавх, зорилго, утга учир',                  '#8b5cf6', '🔮')
on conflict (code) do nothing;

-- Plutchik's Wheel of Emotions
create table if not exists public.ref_plutchik (
  emotion_key      text    primary key,
  label_mn         text    not null,
  full_name_mn     text    not null,
  label_en         text    not null,
  emoji            text,
  band             text    not null check (band in ('lower', 'upper')),
  wheel_order      integer not null,
  color_hex        text,
  opposite_emotion text,
  description      text
);

insert into public.ref_plutchik
  (emotion_key, label_mn, full_name_mn, label_en, emoji, band, wheel_order, color_hex, opposite_emotion, description)
values
  ('joy',          'Баяр',     'Баяр баясгалан', 'Joy',          '😊', 'upper', 1, '#FFD700', 'sadness',      'Эерэг сэтгэл хөдлөл'),
  ('trust',        'Итгэл',    'Итгэл найдвар',  'Trust',        '🤝', 'upper', 2, '#90EE90', 'disgust',      'Нийгмийн холбоо'),
  ('fear',         'Айдас',    'Айдас',           'Fear',         '😨', 'lower', 3, '#008000', 'anger',        'Хамгаалалтын сэтгэл хөдлөл'),
  ('surprise',     'Гайхшрал', 'Гайхшрал',        'Surprise',     '😮', 'upper', 4, '#00BFFF', 'anticipation', 'Шинэ зүйлд хандах хариу үйлдэл'),
  ('sadness',      'Гуниг',    'Гуниг',           'Sadness',      '😢', 'lower', 5, '#00008B', 'joy',          'Алдагдлын сэтгэл хөдлөл'),
  ('anger',        'Уур',      'Уур хилэн',       'Anger',        '😠', 'lower', 6, '#FF0000', 'fear',         'Саад тотгорт хандах хариу үйлдэл'),
  ('disgust',      'Жигшил',   'Жигшил',          'Disgust',      '🤢', 'lower', 7, '#8B4513', 'trust',        'Тэвчихгүй байдлын сэтгэл хөдлөл'),
  ('anticipation', 'Хүлээлт',  'Хүлээлт',         'Anticipation', '👀', 'upper', 8, '#FFA500', 'surprise',     'Ирээдүйд чиглэсэн сэтгэл хөдлөл')
on conflict (emotion_key) do nothing;

-- Add FK constraint for opposite emotions
alter table public.ref_plutchik
  add constraint fk_ref_plutchik_opposite
  foreign key (opposite_emotion)
  references public.ref_plutchik(emotion_key);

-- Plutchik Dyads (compound emotions)
create table if not exists public.ref_plutchik_dyads (
  id             uuid primary key default uuid_generate_v4(),
  emotion_a      text not null references public.ref_plutchik(emotion_key),
  emotion_b      text not null references public.ref_plutchik(emotion_key),
  dyad_name_en   text not null,
  dyad_name_mn   text not null,
  constraint plutchik_dyad_unique unique (emotion_a, emotion_b)
);

insert into public.ref_plutchik_dyads (emotion_a, emotion_b, dyad_name_en, dyad_name_mn) values
  ('joy',      'trust',        'Love',        'Хайр'),
  ('trust',    'fear',         'Submission',  'Дагаж мөрдөх'),
  ('fear',     'surprise',     'Awe',         'Гайхширч айх'),
  ('surprise', 'sadness',      'Disapproval', 'Зөвшөөрөхгүй байх'),
  ('sadness',  'disgust',      'Remorse',     'Гэмшил'),
  ('disgust',  'anger',        'Contempt',    'Үл хүндэтгэх'),
  ('anger',    'anticipation', 'Aggressiveness','Түрэмгийлэл'),
  ('anticipation','joy',       'Optimism',    'Өөдрөг үзэл')
on conflict (emotion_a, emotion_b) do nothing;

-- Hawkins Bands
create table if not exists public.ref_hawkins_bands (
  code         text primary key,
  label_mn     text not null,
  label_en     text not null,
  level_min    integer not null,
  level_max    integer not null,
  description  text,
  color_hex    text
);

insert into public.ref_hawkins_bands
  (code, label_mn, label_en, level_min, level_max, description, color_hex)
values
  ('ego',         'Эго',        'Ego',         20,  199, 'Хүч алдагдуулдаг түвшин — айдас, уур, гуниг',         '#ef4444'),
  ('observer',    'Ажиглагч',   'Observer',    200, 499, 'Шилжилтийн түвшин — зориг, хүлцэл, оюун ухаан',       '#f97316'),
  ('enlightened', 'Гэгээрсэн',  'Enlightened', 500, 700, 'Хүч өгдөг түвшин — хайр, тайван байдал, гэгээрэл',   '#8b5cf6')
on conflict (code) do nothing;

-- Hawkins Levels
create table if not exists public.ref_hawkins (
  level              integer primary key,
  band_code          text    not null references public.ref_hawkins_bands(code),
  label_mn           text    not null,
  label_en           text    not null,
  emotion_mn         text,
  description        text,
  is_power_level     boolean not null default false,
  calibration_note   text
);

insert into public.ref_hawkins
  (level, band_code, label_mn, label_en, emotion_mn, description, is_power_level, calibration_note)
values
  (20,  'ego',         'Ичих',              'Shame',         'Өөрийгөө үзэн ядах',    'Хамгийн доод түвшин',          false, 'Аминдаа занал болох хандлагатай'),
  (30,  'ego',         'Гэм хийх',          'Guilt',         'Гэм буруугийн мэдрэмж', 'Дотоод ялтгалзал',             false, 'Манипуляци, золиослолтой холбоотой'),
  (50,  'ego',         'Апати',             'Apathy',        'Хоосон дутуу мэдрэмж',  'Итгэл алдарсан байдал',        false, 'Ядуурал, гачигдалтай холбоотой'),
  (75,  'ego',         'Уй гашуу',          'Grief',         'Гуниг',                  'Алдагдлын боловсруулалт',     false, 'Хайрлах чадвар хадгалагдсан хэвээр'),
  (100, 'ego',         'Айдас',             'Fear',          'Айдас, түгшүүр',         'Хамгаалалт хайх байдал',      false, 'Телевиз, медиагаар өдөөгддөг'),
  (125, 'ego',         'Хүсэл тачаал',      'Desire',        'Хүсэл',                  'Гадаад зүйлд эрэлхийлэх',    false, 'Зар сурталчилгааны гол бай'),
  (150, 'ego',         'Уур хилэн',         'Anger',         'Уур',                    'Саад тотгорт хариу үйлдэл',  false, 'Хоёр тийш чиглэж болно — устгал ч, өөрчлөлт ч'),
  (175, 'ego',         'Бардамнал',         'Pride',         'Бардамнал',              'Зэвүүцэл, хэт өөртөө итгэх', false, '200-аас 1 алхам доор, буцах эрсдэлтэй'),
  (200, 'observer',    'Зориг',             'Courage',       'Тэвчээр',                'Шилжилтийн эгшиг түвшин',    true,  'Амьдрал бүтээлч болж эхэлдэг цэг'),
  (250, 'observer',    'Тэнцвэр',           'Neutrality',    'Тайван байдал',          'Уян хатан байдал',            true,  'Хэн нэгнийг буруутгахаа больдог'),
  (310, 'observer',    'Хүлцэл',            'Willingness',   'Тэвчээрлэл',             'Оролцох хүсэл',               true,  'Амжилттай хүмүүсийн олонх энд байдаг'),
  (350, 'observer',    'Хүлээн зөвшөөрөх', 'Acceptance',    'Хүлээн авах',            'Бодит байдлыг харах',         true,  'Өөрийн хариуцлагыг бүрэн хүлээдэг'),
  (400, 'observer',    'Оюун ухаан',        'Reason',        'Ойлголт',                'Аналитик сэтгэлгээ',          true,  'Einstein, Freud зэрэг хүмүүс энд байсан гэж тооцдог'),
  (500, 'enlightened', 'Хайр',              'Love',          'Хайр',                   'Болзолгүй хайр, нэгдэл',     true,  'Дэлхийн хүн амын 0.4% л энд хүрдэг'),
  (540, 'enlightened', 'Баяр хөөр',         'Joy',           'Баяр',                   'Дотоод тайван, нигүүлсэл',   true,  'Гэгээнтнүүдэд тохиолддог байнгын байдал'),
  (600, 'enlightened', 'Амар тайван',       'Peace',         'Тайван байдал',          'Гүн ухамсар',                 true,  'Мэдэгдэхүйц мэдрэгддэг энерги'),
  (700, 'enlightened', 'Гэгээрэл',          'Enlightenment', 'Нэгдэл',                 'Хамгийн дээд түвшин',         true,  'Буддагийн гэгээрлийн түвшин')
on conflict (level) do nothing;

-- ============================================================
-- 2. CORE APPLICATION TABLES
-- ============================================================

-- Users table (basic structure, typically managed by Supabase Auth)
create table if not exists public.users (
  id         uuid primary key default uuid_generate_v4(),
  email      text unique,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Journal Entries
create table if not exists public.journal_entries (
  id            uuid primary key default uuid_generate_v4(),
  user_id       uuid not null references public.users(id),
  content       text not null,
  title         text,
  mood          text,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now(),
  is_encrypted  boolean default false,
  embedding     vector(768)
);

create index if not exists idx_journal_entries_user_id on public.journal_entries(user_id);
create index if not exists idx_journal_entries_created_at on public.journal_entries(created_at);
create index if not exists idx_journal_entries_embedding 
  on public.journal_entries using ivfflat (embedding vector_cosine_ops);

-- Value Nodes
create table if not exists public.value_nodes (
  id                uuid primary key default uuid_generate_v4(),
  journal_entry_id  uuid references public.journal_entries(id),
  user_id           uuid not null references public.users(id),
  value_label       text not null,
  value_category    text,
  maslow_code       text references public.ref_maslow(code),
  dominant_primary  text references public.ref_plutchik(emotion_key),
  confidence_score  numeric(5,4) default 0.0,
  metadata          jsonb default '{}',
  created_at        timestamptz default now(),
  updated_at        timestamptz default now()
);

create index if not exists idx_value_nodes_user_id on public.value_nodes(user_id);
create index if not exists idx_value_nodes_journal_id on public.value_nodes(journal_entry_id);
create index if not exists idx_value_nodes_maslow on public.value_nodes(maslow_code);

-- Value Graph Edges
create table if not exists public.value_graph_edges (
  id              uuid primary key default uuid_generate_v4(),
  user_id         uuid not null references public.users(id),
  source_node_id  uuid not null references public.value_nodes(id),
  target_node_id  uuid not null references public.value_nodes(id),
  edge_type       text not null,
  weight          numeric(10,6) default 0.0,
  co_occurrence_count integer default 1,
  metadata        jsonb default '{}',
  created_at      timestamptz default now(),
  updated_at      timestamptz default now(),
  constraint source_target_unique unique (source_node_id, target_node_id, user_id)
);

create index if not exists idx_value_graph_edges_user_id on public.value_graph_edges(user_id);
create index if not exists idx_value_graph_edges_source on public.value_graph_edges(source_node_id);
create index if not exists idx_value_graph_edges_target on public.value_graph_edges(target_node_id);

-- Psychometric Analyses
create table if not exists public.psychometric_analyses (
  id                uuid primary key default uuid_generate_v4(),
  journal_entry_id  uuid not null references public.journal_entries(id),
  user_id           uuid not null references public.users(id),
  hawkins_level     integer references public.ref_hawkins(level),
  hawkins_label     text,
  maslow_categories text[],
  emotions          text[],
  analysis_metadata jsonb default '{}',
  created_at        timestamptz default now(),
  updated_at        timestamptz default now()
);

create index if not exists idx_psychometric_user_id on public.psychometric_analyses(user_id);
create index if not exists idx_psychometric_journal_id on public.psychometric_analyses(journal_entry_id);
create index if not exists idx_psychometric_hawkins_level on public.psychometric_analyses(hawkins_level);
create index if not exists idx_psychometric_emotions 
  on public.psychometric_analyses using gin (emotions);
create index if not exists idx_psychometric_maslow_categories 
  on public.psychometric_analyses using gin (maslow_categories);

-- Pattern Rules
create table if not exists public.pattern_rules (
  id              uuid primary key default uuid_generate_v4(),
  rule_name       text unique not null,
  rule_type       text not null,
  description     text,
  pattern_config  jsonb default '{}',
  is_active       boolean default true,
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

-- Detected Patterns
create table if not exists public.detected_patterns (
  id              uuid primary key default uuid_generate_v4(),
  user_id         uuid not null references public.users(id),
  rule_id         uuid references public.pattern_rules(id),
  pattern_type    text not null,
  pattern_data    jsonb not null,
  strength_score  numeric(5,4) default 0.0,
  detected_at     timestamptz default now(),
  acknowledged    boolean default false
);

create index if not exists idx_detected_patterns_user_id on public.detected_patterns(user_id);
create index if not exists idx_detected_patterns_rule_id on public.detected_patterns(rule_id);
create index if not exists idx_detected_patterns_detected_at on public.detected_patterns(detected_at);

-- Value Node Maslow Trackers
create table if not exists public.value_node_maslow_trackers (
  id              uuid primary key default uuid_generate_v4(),
  value_node_id   uuid not null references public.value_nodes(id),
  user_id         uuid not null references public.users(id),
  maslow_code     text references public.ref_maslow(code),
  previous_code   text references public.ref_maslow(code),
  changed_at      timestamptz default now(),
  change_reason   text
);

create index if not exists idx_value_node_maslow_tracker_node_id on public.value_node_maslow_trackers(value_node_id);
create index if not exists idx_value_node_maslow_tracker_user_id on public.value_node_maslow_trackers(user_id);

-- Value Node Emotion Trackers
create table if not exists public.value_node_emotion_trackers (
  id                  uuid primary key default uuid_generate_v4(),
  value_node_id       uuid not null references public.value_nodes(id),
  user_id             uuid not null references public.users(id),
  primary_emotion     text references public.ref_plutchik(emotion_key),
  secondary_emotion   text references public.ref_plutchik(emotion_key),
  intensity_score     numeric(5,4) default 0.0,
  tracked_at          timestamptz default now()
);

create index if not exists idx_value_node_emotion_tracker_node_id on public.value_node_emotion_trackers(value_node_id);
create index if not exists idx_value_node_emotion_tracker_user_id on public.value_node_emotion_trackers(user_id);

-- ============================================================
-- 3. SEED DATA - PATTERN RULES
-- ============================================================

insert into public.pattern_rules (rule_name, rule_type, description, is_active)
values
  ('value_co_occurrence', 'value_co_occurrence', 'Хоёр утга хамт давтагдах хэв маяг', true),
  ('emotion_trend', 'emotion_trend', 'Сэтгэлийн хөдлөлийн чиг хандлага', true),
  ('hawkins_shift', 'hawkins_shift', 'Hawkins түвшний өөрчлөлт', true),
  ('maslow_progression', 'maslow_progression', 'Maslow хэрэгцээний дэвшилт', true)
on conflict (rule_name) do nothing;

-- ============================================================
-- 4. ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================

-- Enable RLS on all tables
do $$ 
declare
  t text;
begin
  foreach t in array array[
    'ref_maslow', 
    'ref_plutchik', 
    'ref_plutchik_dyads',
    'ref_hawkins_bands',
    'ref_hawkins',
    'users',
    'journal_entries',
    'value_nodes',
    'value_graph_edges',
    'psychometric_analyses',
    'pattern_rules',
    'detected_patterns',
    'value_node_maslow_trackers',
    'value_node_emotion_trackers'
  ]
  loop
    execute format('alter table public.%I enable row level security', t);
  end loop;
end $$;

-- Reference tables: public read, service_role write
do $$ 
declare
  t text;
begin
  foreach t in array array[
    'ref_maslow', 
    'ref_plutchik', 
    'ref_plutchik_dyads',
    'ref_hawkins_bands',
    'ref_hawkins',
    'pattern_rules'
  ]
  loop
    execute format('drop policy if exists "policy_%s_public_read" on public.%I', t, t);
    execute format('create policy "policy_%s_public_read" on public.%I for select using (true)', t, t);
    
    execute format('drop policy if exists "policy_%s_service_write" on public.%I', t, t);
    execute format('create policy "policy_%s_service_write" on public.%I for all using (auth.role() = ''service_role'')', t, t);
  end loop;
end $$;

-- User-specific tables: user access + service_role
do $$ 
declare
  t text;
begin
  foreach t in array array[
    'journal_entries',
    'value_nodes',
    'value_graph_edges',
    'psychometric_analyses',
    'detected_patterns',
    'value_node_maslow_trackers',
    'value_node_emotion_trackers'
  ]
  loop
    execute format('drop policy if exists "policy_%s_user_access" on public.%I', t, t);
    execute format('
      create policy "policy_%s_user_access" on public.%I for all 
      using (user_id = auth.uid() OR auth.role() = ''service_role'')
    ', t, t);
  end loop;
end $$;

-- psychometric_analyses special policy (via journal_entries)
drop policy if exists "policy_psychometric_user_access" on public.psychometric_analyses;
create policy "policy_psychometric_user_access" on public.psychometric_analyses
  for all
  using (
    auth.uid() IN (
      select je.user_id 
      from public.journal_entries je 
      where je.id = psychometric_analyses.journal_entry_id
    )
    OR 
    auth.role() = 'service_role'
  );

-- users table: user can read/update own profile
drop policy if exists "policy_users_self_access" on public.users;
create policy "policy_users_self_access" on public.users
  for all
  using (id = auth.uid() OR auth.role() = 'service_role');

-- ============================================================
-- 5. INDEXES FOR PERFORMANCE
-- ============================================================

drop index if exists idx_ref_plutchik_band;
create index idx_ref_plutchik_band on public.ref_plutchik(band);

drop index if exists idx_ref_hawkins_band;
create index idx_ref_ref_hawkins_band on public.ref_hawkins(band_code);

drop index if exists idx_ref_hawkins_power;
create index idx_ref_hawkins_power on public.ref_hawkins(is_power_level);

drop index if exists idx_journal_entries_is_encrypted;
create index idx_journal_entries_is_encrypted on public.journal_entries(is_encrypted);

-- ============================================================
-- 6. SAMPLE SEED DATA FOR TESTING (Optional)
-- ============================================================

-- Sample test user (uncomment for development/testing)
-- insert into public.users (id, email) 
-- values ('00000000-0000-0000-0000-000000000001', 'test@example.com')
-- on conflict (id) do nothing;

-- Sample journal entry (uncomment for development/testing)
-- insert into public.journal_entries (id, user_id, content, title, mood)
-- values (
--   '11111111-1111-1111-1111-111111111111',
--   '00000000-0000-0000-0000-000000000001',
--   'Today I felt grateful for my family and excited about my new project.',
--   'Grateful Day',
--   'happy'
-- )
-- on conflict (id) do nothing;

-- ============================================================
-- SEED.SQL COMPLETE
-- All tables, reference data, and RLS policies configured
-- ============================================================
