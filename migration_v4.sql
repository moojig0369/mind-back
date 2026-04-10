-- ============================================================
-- MIGRATION V4 — REF TABLES REFACTOR
-- ENUM-ийг устгаж, 3 онолын reference table-уудыг сайжруулсан
-- ============================================================

-- UUID generation extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 1. ref_maslow
--    Өмнө: maslow_category ENUM + тусдаа ref_maslow хүснэгт
--    Одоо: нэг table, code TEXT primary key
-- ============================================================
create table if not exists public.ref_maslow (
  code         text    primary key,   -- 'physiological', 'safety', ...
  level        integer not null unique check (level between 1 and 5),
  label_mn     text    not null,
  label_en     text    not null,
  description  text,
  color_hex    text,                  -- UI-д ашиглах өнгө
  icon         text                   -- emoji эсвэл icon name
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

-- ============================================================
-- 2. ref_plutchik
--    Өмнө: emotion_band ENUM + ref_plutchik хүснэгт
--    Одоо: band TEXT check constraint, dyad холбоос нэмсэн
-- ============================================================
create table if not exists public.ref_plutchik (
  emotion_key      text    primary key,  -- 'joy', 'fear', ...
  label_mn         text    not null,
  full_name_mn     text    not null,
  label_en         text    not null,
  emoji            text,
  band             text    not null check (band in ('lower', 'upper')),
  wheel_order      integer not null,     -- 1-8, дугуй дээрх байрлал
  color_hex        text,                 -- Plutchik wheel-ийн өнгө
  opposite_emotion text,                 -- эсрэг сэтгэл (FK added after insert)
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

-- Add FK constraint after data is inserted
alter table public.ref_plutchik
  add constraint fk_ref_plutchik_opposite
  foreign key (opposite_emotion)
  references public.ref_plutchik(emotion_key);

-- Plutchik dyad table: хоёр сэтгэлийн нийлмэл
-- joy + trust = love, trust + fear = submission, гэх мэт
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

-- ============================================================
-- 3. ref_hawkins
--    Өмнө: band TEXT, хоосон зай
--    Одоо: band table болгосон, calibration_note нэмсэн
-- ============================================================

-- Hawkins band-уудыг тусдаа table болгов
create table if not exists public.ref_hawkins_bands (
  code         text primary key,   -- 'ego', 'observer', 'enlightened'
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

create table if not exists public.ref_hawkins (
  level              integer primary key,
  band_code          text    not null references public.ref_hawkins_bands(code),
  label_mn           text    not null,
  label_en           text    not null,
  emotion_mn         text,
  description        text,
  is_power_level     boolean not null default false, -- 200+ бол true
  calibration_note   text                            -- Hawkins-ийн судалгааны тайлбар
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
-- 4. RLS — бүх ref table public read, service write
-- ============================================================
do $$ 
declare
  t text;
begin
  foreach t in array array[
    'ref_maslow', 
    'ref_plutchik', 
    'ref_plutchik_dyads',
    'ref_hawkins_bands',
    'ref_hawkins'
  ]
  loop
    execute format('alter table public.%I enable row level security', t);
    execute format('
      drop policy if exists "policy_%s_public_read" on public.%I;
      create policy "policy_%s_public_read" on public.%I for select using (true);
    ', t, t, t, t);
    execute format('
      drop policy if exists "policy_%s_service_write" on public.%I;
      create policy "policy_%s_service_write" on public.%I for all using (auth.role() = ''service_role'');
    ', t, t, t, t);
  end loop;
end $$;

-- ============================================================
-- 5. INDEXES
-- ============================================================
drop index if exists idx_ref_plutchik_band;
create index idx_ref_plutchik_band        on public.ref_plutchik(band);

drop index if exists idx_ref_hawkins_band;
create index idx_ref_ref_hawkins_band     on public.ref_hawkins(band_code);

drop index if exists idx_ref_hawkins_power;
create index idx_ref_hawkins_power        on public.ref_hawkins(is_power_level);

-- ============================================================
-- 6. psychometric_analyses дахь FK шинэчлэл
--    maslow_categories[] → ref_maslow.code[] болгох
--    (ENUM array-аас TEXT array руу)
-- ============================================================
alter table public.psychometric_analyses
  alter column maslow_categories type text[]
    using maslow_categories::text[];

-- hawkins_label redundant тул устгана (ref_hawkins JOIN-оор авна)
alter table public.psychometric_analyses
  drop column if exists hawkins_label;

-- ============================================================
-- 7. value_nodes дахь maslow_category → maslow_code
-- ============================================================
alter table public.value_nodes
  add column if not exists maslow_code text references public.ref_maslow(code);

-- Хуучин maslow_category өгөгдлийг шилжүүлэх
update public.value_nodes
set maslow_code = maslow_category::text
where maslow_code is null
  and maslow_category is not null;

-- Шилжүүлэг дууссаны дараа хуучин багана болон ENUM-ийг устгана:
alter table public.value_nodes drop column if exists maslow_category;

-- value_node_maslow_trackers table-д мөн адил
alter table public.value_node_maslow_trackers
  add column if not exists maslow_code text references public.ref_maslow(code);

update public.value_node_maslow_trackers
set maslow_code = category::text
where maslow_code is null
  and category is not null;

alter table public.value_node_maslow_trackers drop column if exists category;

-- ENUM төрлүүдийг устгах
drop type if exists maslow_category cascade;
drop type if exists quick_action_type cascade;
drop type if exists emotion_band cascade;
