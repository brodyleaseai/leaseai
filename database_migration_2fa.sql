-- Add 2FA/TOTP columns to admin_users and clients tables
-- Run this in Supabase SQL Editor

-- Add TOTP columns to admin_users table
ALTER TABLE admin_users
ADD COLUMN IF NOT EXISTS totp_secret TEXT,
ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS totp_enabled_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS totp_disabled_at TIMESTAMP WITH TIME ZONE;

-- Add TOTP columns to clients table
ALTER TABLE clients
ADD COLUMN IF NOT EXISTS totp_secret TEXT,
ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS totp_enabled_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS totp_disabled_at TIMESTAMP WITH TIME ZONE;

-- Add comments
COMMENT ON COLUMN admin_users.totp_secret IS 'Base32-encoded TOTP secret key for 2FA';
COMMENT ON COLUMN admin_users.totp_enabled IS 'Whether 2FA is enabled for this user';
COMMENT ON COLUMN admin_users.totp_enabled_at IS 'Timestamp when 2FA was enabled';
COMMENT ON COLUMN admin_users.totp_disabled_at IS 'Timestamp when 2FA was last disabled';

COMMENT ON COLUMN clients.totp_secret IS 'Base32-encoded TOTP secret key for 2FA';
COMMENT ON COLUMN clients.totp_enabled IS 'Whether 2FA is enabled for this user';
COMMENT ON COLUMN clients.totp_enabled_at IS 'Timestamp when 2FA was enabled';
COMMENT ON COLUMN clients.totp_disabled_at IS 'Timestamp when 2FA was last disabled';

-- Create index for faster 2FA status queries
CREATE INDEX IF NOT EXISTS idx_admin_users_totp_enabled ON admin_users(totp_enabled);
CREATE INDEX IF NOT EXISTS idx_clients_totp_enabled ON clients(totp_enabled);

-- Grant permissions
GRANT SELECT, UPDATE ON admin_users TO authenticated;
GRANT SELECT, UPDATE ON clients TO authenticated;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ 2FA database schema migration completed successfully!';
    RAISE NOTICE 'Added totp_secret, totp_enabled, totp_enabled_at, totp_disabled_at columns';
    RAISE NOTICE 'Created indexes for performance optimization';
END $$;
