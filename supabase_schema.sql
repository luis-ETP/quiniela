-- ── Profiles ──────────────────────────────────────────────────────────────────
create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  nombre text not null,
  email text,
  is_admin boolean default false,
  pagado boolean default false,
  draft_orden int,
  desempate_manual int,
  created_at timestamptz default now()
);

-- ── Teams ─────────────────────────────────────────────────────────────────────
create table if not exists teams (
  id uuid primary key default gen_random_uuid(),
  ranking_compuesto int not null,
  nombre text not null unique,
  grupo_oficial text,
  bombo text not null,
  pts_victoria numeric not null,
  pts_empate numeric not null,
  ranking_fifa int,
  odds_las_vegas text,
  ranking_modelo int,
  created_at timestamptz default now()
);

-- ── Matches ───────────────────────────────────────────────────────────────────
create table if not exists matches (
  id uuid primary key default gen_random_uuid(),
  numero int not null unique,
  fecha date,
  fase text not null,
  grupo text,
  local_id uuid references teams(id),
  visitante_id uuid references teams(id),
  local_nombre text,
  visitante_nombre text,
  goles_local int,
  goles_visitante int,
  equipo_avanza_id uuid references teams(id),
  equipo_avanza_nombre text,
  estado text default 'Programado',
  pts_local numeric default 0,
  pts_visitante numeric default 0,
  capturado_por uuid references profiles(id),
  created_at timestamptz default now()
);

-- ── Picks ─────────────────────────────────────────────────────────────────────
create table if not exists picks (
  id uuid primary key default gen_random_uuid(),
  pick_numero int not null unique,
  ronda int not null,
  participant_id uuid references profiles(id),
  team_id uuid references teams(id) unique,
  group_conflict boolean default false,
  exception_authorized boolean default false,
  created_at timestamptz default now()
);

-- ── RLS: disable for MVP (admin secret key handles auth) ─────────────────────
alter table profiles disable row level security;
alter table teams disable row level security;
alter table matches disable row level security;
alter table picks disable row level security;
