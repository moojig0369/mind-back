-- ============================================================
-- MIGRATION V5 — UML DIAGRAM ALIGNMENT
-- PsychometricAnalysis, JournalEntry, ValueGraph холбогдох өөрчлөлтүүд
-- ============================================================

-- UUID generation extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 1. psychometric_analyses - emotions болон hawkins_label нэмэх
-- ============================================================

-- emotions ARRAY багана нэмэх (UML: emotions: string[])
alter table public.psychometric_analyses
  add column if not exists emotions text[];

-- hawkins_label багана нэмэх (UML: hawkinsLabel: string)
alter table public.psychometric_analyses
  add column if not exists hawkins_label text;

-- hawkins_label-ийг ref_hawkins-ээс автоматаар дүүргэх
update public.psychometric_analyses pa
set hawkins_label = rh.label_en
from public.ref_hawkins rh
where pa.hawkins_level = rh.level
  and pa.hawkins_label is null;

-- ============================================================
-- 2. journal_entries - is_encrypted, embedding баганууд
-- ============================================================

-- is_encrypted багана нэмэх (UML: isEncrypted: bool)
alter table public.journal_entries
  add column if not exists is_encrypted boolean default false;

-- embedding VECTOR багана нэмэх (UML: embedding: vector)
-- pgvector extension шаардлагатай
CREATE EXTENSION IF NOT EXISTS vector;

alter table public.journal_entries
  add column if not exists embedding vector(768);

-- embedding индекс үүсгэх (optional, semantic search-д ашигтай)
create index if not exists idx_journal_entries_embedding 
  on public.journal_entries using ivfflat (embedding vector_cosine_ops);

-- ============================================================
-- 3. pattern_rules - анхны дүрмүүдийг оруулах
-- ============================================================

insert into public.pattern_rules (rule_name, rule_type, description, is_active)
values
  ('value_co_occurrence', 'value_co_occurrence', 'Хоёр утга хамт давтагдах хэв маяг', true),
  ('emotion_trend', 'emotion_trend', 'Сэтгэлийн хөдлөлийн чиг хандлага', true),
  ('hawkins_shift', 'hawkins_shift', 'Hawkins түвшний өөрчлөлт', true),
  ('maslow_progression', 'maslow_progression', 'Maslow хэрэгцээний дэвшилт', true)
on conflict (rule_name) do nothing;

-- ============================================================
-- 4. value_nodes - dominant_primary FK засвар
-- ============================================================

-- dominant_primary нь ref_plutchik.emotion_key руу заах ёстой
alter table public.value_nodes
  drop constraint if exists value_nodes_dominant_primary_fkey;

alter table public.value_nodes
  add constraint fk_value_nodes_dominant_primary
  foreign key (dominant_primary)
  references public.ref_plutchik(emotion_key);

-- ============================================================
-- 5. value_node_emotion_trackers - secondary_emotion нэмэх
-- ============================================================

alter table public.value_node_emotion_trackers
  add column if not exists secondary_emotion text references public.ref_plutchik(emotion_key);

-- ============================================================
-- 6. RLS policies шинэчлэх
-- ============================================================

-- psychometric_analyses RLS
alter table public.psychometric_analyses enable row level security;

drop policy if exists "policy_psychometric_user_access" on public.psychometric_analyses;
create policy "policy_psychometric_user_access" on public.psychometric_analyses
  for all
  using (
    auth.uid() IN (
      select je.user_id 
      from public.journal_entries je 
      where je.id = psychometric_analyses.journal_id
    )
    OR 
    auth.role() = 'service_role'
  );

-- journal_entries RLS (шинэ багануудыг хамруулан)
alter table public.journal_entries enable row level security;

drop policy if exists "policy_journal_entries_user_access" on public.journal_entries;
create policy "policy_journal_entries_user_access" on public.journal_entries
  for all
  using (
    user_id = auth.uid() 
    OR 
    auth.role() = 'service_role'
  );

-- ============================================================
-- 7. INDEXES
-- ============================================================

-- emotions array индекс
create index if not exists idx_psychometric_emotions 
  on public.psychometric_analyses using gin (emotions);

-- hawkins_label индекс
create index if not exists idx_psychometric_hawkins_label 
  on public.psychometric_analyses (hawkins_label);

-- is_encrypted индекс
create index if not exists idx_journal_entries_is_encrypted 
  on public.journal_entries (is_encrypted);

-- ============================================================
-- MIGRATION V5 COMPLETE
-- ============================================================
