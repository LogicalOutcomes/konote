-- Audit database initialisation
-- ================================
-- This script sets up roles for the separate audit database.
-- The audit trail is tamper-resistant: the application can only INSERT and
-- SELECT rows — never UPDATE or DELETE them.
--
-- IMPORTANT: Django migrations require CREATE/ALTER TABLE privileges, so the
-- audit_writer role starts with full privileges on the public schema. After
-- migrations have run, call the lockdown_audit_db management command (or run
-- the REVOKE statements below manually) to restrict audit_writer to
-- INSERT + SELECT only.

-- ---------------------------------------------------------------
-- 1. audit_reader — read-only role for admin dashboard / reports
-- ---------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'audit_reader') THEN
        CREATE ROLE audit_reader WITH LOGIN PASSWORD 'audit_read_pass';
    END IF;
END
$$;

-- Grant connect and read-only access
GRANT CONNECT ON DATABASE CURRENT_DATABASE() TO audit_reader;
GRANT USAGE ON SCHEMA public TO audit_reader;

-- If the audit_log table already exists, grant SELECT now.
-- (If it doesn't exist yet, the lockdown command handles this after migrate.)
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'audit_log'
    ) THEN
        EXECUTE 'GRANT SELECT ON audit_log TO audit_reader';
    END IF;
END
$$;

-- ---------------------------------------------------------------
-- 2. audit_writer — the role Django uses for the audit database
-- ---------------------------------------------------------------
-- This role is created by Docker Compose / Railway environment variables.
-- The statements below are for reference and will be applied by the
-- lockdown_audit_db management command AFTER migrations complete.
--
-- REVOKE ALL ON audit_log FROM audit_writer;
-- GRANT SELECT, INSERT ON audit_log TO audit_writer;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO audit_writer;
--
-- This ensures the application layer cannot modify or delete audit records.
