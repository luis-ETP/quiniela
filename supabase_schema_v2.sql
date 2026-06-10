-- Drop old tables if exist
drop table if exists picks cascade;
drop table if exists matches cascade;
drop table if exists teams cascade;
drop table if exists profiles cascade;

-- Profiles (username based, no auth dependency)
create table profiles (
  username text primary key,
  nombre text not null,
  is_admin boolean default false,
  pagado boolean default false,
  draft_orden int,
  desempate_manual int,
  created_at timestamptz default now()
);

-- Teams
create table teams (
  id uuid primary key default gen_random_uuid(),
  ranking_compuesto int not null,
  nombre text not null unique,
  grupo_oficial text,
  bombo text not null,
  pts_victoria numeric not null,
  pts_empate numeric not null,
  ranking_fifa int,
  odds_las_vegas text,
  ranking_modelo int
);

-- Matches
create table matches (
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
  pts_visitante numeric default 0
);

-- Picks
create table picks (
  id uuid primary key default gen_random_uuid(),
  pick_numero int not null unique,
  ronda int not null,
  participant_username text references profiles(username),
  team_id uuid references teams(id) unique,
  group_conflict boolean default false,
  exception_authorized boolean default false,
  created_at timestamptz default now()
);

-- Disable RLS
alter table profiles disable row level security;
alter table teams disable row level security;
alter table matches disable row level security;
alter table picks disable row level security;
