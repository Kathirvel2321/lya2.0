-- ============================================================================
-- LYA 2.0 Phone Command Module - Supabase Schema
-- ============================================================================

-- 1. Admins Table
create table if not exists public.admins (
    id uuid primary key references auth.users(id) on delete cascade,
    email text,
    created_at timestamptz not null default now()
);

-- Helper function to check if the caller is an active admin
create or replace function public.is_admin()
returns boolean
language sql
security definer
set search_path = public
stable
as $$
    select exists (
        select 1 from public.admins where id = auth.uid()
    );
$$;

-- 2. Commands Table
create table if not exists public.commands (
    id uuid primary key default gen_random_uuid(),
    action text not null check (char_length(action) <= 100),
    args jsonb default '{}'::jsonb check (pg_column_size(args) <= 1024),
    status text not null default 'pending',
    result text,
    created_at timestamptz not null default now(),
    finished_at timestamptz,
    created_by uuid default auth.uid()
);

-- Before-insert trigger to enforce clean initial state and admin creator (security invoker)
create or replace function public.commands_before_insert()
returns trigger
language plpgsql
security invoker
as $$
begin
    new.status := 'pending';
    new.created_at := now();
    new.result := null;
    new.finished_at := null;
    new.created_by := auth.uid();
    return new;
end;
$$;

drop trigger if exists trg_commands_before_insert on public.commands;
create trigger trg_commands_before_insert
    before insert on public.commands
    for each row
    execute function public.commands_before_insert();

-- Atomic command claim function (service_role only)
create or replace function public.claim_next_command()
returns setof public.commands
language plpgsql
security definer
set search_path = public
as $$
declare
    target_row public.commands;
begin
    select *
    into target_row
    from public.commands
    where status = 'pending'
    order by created_at asc
    limit 1
    for update skip locked;

    if not found then
        return;
    end if;

    if target_row.created_at < now() - interval '60 seconds' then
        update public.commands
        set status = 'rejected: expired',
            finished_at = now(),
            result = 'Command timestamp is older than 60 seconds'
        where id = target_row.id
        returning * into target_row;
    else
        update public.commands
        set status = 'running'
        where id = target_row.id
        returning * into target_row;
    end if;

    return next target_row;
end;
$$;

revoke execute on function public.claim_next_command() from public, anon, authenticated;
grant execute on function public.claim_next_command() to service_role;

-- 3. Command Audit Log Table
create table if not exists public.command_log (
    id uuid primary key default gen_random_uuid(),
    command_id uuid references public.commands(id) on delete cascade,
    action text not null,
    status text not null,
    timestamp timestamptz not null default now()
);

-- 4. Allowed Actions Table (Populated by the Laptop Listener on startup)
create table if not exists public.allowed_actions (
    id text primary key,
    category text not null,
    label text not null,
    updated_at timestamptz not null default now()
);

-- ============================================================================
-- Row Level Security (RLS) Policies (Idempotent)
-- ============================================================================

-- Admins Table RLS
alter table public.admins enable row level security;

drop policy if exists "Admins can view admins list" on public.admins;
create policy "Admins can view admins list"
    on public.admins
    for select
    to authenticated
    using (public.is_admin());

-- Commands Table RLS
-- Rule: Only authenticated user whose UUID is in admins may insert and select.
-- No update or delete from the client (service role bypasses RLS for updates).
alter table public.commands enable row level security;

drop policy if exists "Admins can select commands" on public.commands;
create policy "Admins can select commands"
    on public.commands
    for select
    to authenticated
    using (public.is_admin());

drop policy if exists "Admins can insert commands" on public.commands;
create policy "Admins can insert commands"
    on public.commands
    for insert
    to authenticated
    with check (public.is_admin());

-- Command Log RLS
alter table public.command_log enable row level security;

drop policy if exists "Admins can select command log" on public.command_log;
create policy "Admins can select command log"
    on public.command_log
    for select
    to authenticated
    using (public.is_admin());

-- Allowed Actions RLS
alter table public.allowed_actions enable row level security;

drop policy if exists "Admins can select allowed actions" on public.allowed_actions;
create policy "Admins can select allowed actions"
    on public.allowed_actions
    for select
    to authenticated
    using (public.is_admin());

-- ============================================================================
-- Storage Bucket: screenshots (Idempotent)
-- ============================================================================

insert into storage.buckets (id, name, public)
values ('screenshots', 'screenshots', false)
on conflict (id) do update set public = false;

-- Storage Policies:
-- Authenticated admin may read. Nobody may write except service role (which bypasses RLS).
drop policy if exists "Admins can read screenshots" on storage.objects;
create policy "Admins can read screenshots"
    on storage.objects
    for select
    to authenticated
    using (
        bucket_id = 'screenshots'
        and public.is_admin()
    );

-- ============================================================================
-- Realtime Subscriptions (Guarded & Idempotent)
-- ============================================================================

do $$
begin
    if not exists (
        select 1 from pg_publication_tables 
        where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'commands'
    ) then
        alter publication supabase_realtime add table public.commands;
    end if;

    if not exists (
        select 1 from pg_publication_tables 
        where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'allowed_actions'
    ) then
        alter publication supabase_realtime add table public.allowed_actions;
    end if;
end;
$$;
