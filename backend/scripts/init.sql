-- GambleGlee Database Initialization Script
-- This script runs when the PostgreSQL container starts for the first time

-- Create database if it doesn't exist (handled by POSTGRES_DB env var)
-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create custom types
DO $$ BEGIN
    CREATE TYPE bet_status AS ENUM (
        'pending', 'accepted', 'active', 'completed', 
        'resolved', 'cancelled', 'expired', 'disputed', 'refunded'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE bet_type AS ENUM (
        'friend_bet', 'trick_shot', 'live_event', 
        'prediction', 'challenge', 'tournament'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE bet_outcome AS ENUM (
        'pending', 'winner_a', 'winner_b', 'tie', 'cancelled', 'disputed'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE participant_role AS ENUM (
        'creator', 'acceptor', 'observer', 'judge'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create indexes for better performance
-- These will be created by Alembic migrations, but we can add some initial ones

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE gambleglee TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA public TO postgres;

-- Set timezone
SET timezone = 'UTC';

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'GambleGlee database initialized successfully';
END $$;
