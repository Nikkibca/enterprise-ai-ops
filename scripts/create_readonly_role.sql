DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_catalog.pg_roles
        WHERE rolname = 'sql_reader'
    ) THEN
        CREATE ROLE sql_reader
        LOGIN
        PASSWORD 'sql_reader_password';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE enterprise_ai_ops TO sql_reader;

GRANT USAGE ON SCHEMA public TO sql_reader;

GRANT SELECT ON TABLE
    payments,
    payment_failures
TO sql_reader;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public
TO sql_reader;

ALTER DEFAULT PRIVILEGES FOR ROLE app_user IN SCHEMA public
GRANT SELECT ON TABLES TO sql_reader;

ALTER DEFAULT PRIVILEGES FOR ROLE app_user IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO sql_reader;