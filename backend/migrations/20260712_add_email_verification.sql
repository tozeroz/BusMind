-- ============================================================================
-- Migration: 20260712_add_email_verification.sql
-- Purpose:   Add email column to user_account and create email_verification_code
--            table for registration verification flow.
-- Database:  busmind (MySQL 8)
-- Author:    BusMind team
-- Date:      2026-07-12
--
-- This script is IDEMPOTENT — safe to run multiple times.
-- No data is deleted or modified.
-- ============================================================================

USE busmind;

DELIMITER $$

CREATE PROCEDURE migrate_20260712_add_email_verification()
BEGIN
    DECLARE _cnt INT DEFAULT 0;

    -- -------------------------------------------------------------------------
    -- 1. Add `email` column to `user_account` if it does not already exist
    -- -------------------------------------------------------------------------
    SELECT COUNT(*) INTO _cnt
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'user_account'
      AND COLUMN_NAME = 'email';

    IF _cnt = 0 THEN
        ALTER TABLE user_account
            ADD COLUMN email VARCHAR(100) NULL AFTER nickname;
    END IF;

    -- -------------------------------------------------------------------------
    -- 2. Add unique index on `email` if it does not already exist
    -- -------------------------------------------------------------------------
    SELECT COUNT(*) INTO _cnt
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'user_account'
      AND INDEX_NAME = 'uk_user_email';

    IF _cnt = 0 THEN
        ALTER TABLE user_account
            ADD UNIQUE KEY uk_user_email (email);
    END IF;

    -- -------------------------------------------------------------------------
    -- 3. Create `email_verification_code` table if it does not already exist
    -- -------------------------------------------------------------------------
    SELECT COUNT(*) INTO _cnt
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'email_verification_code';

    IF _cnt = 0 THEN
        CREATE TABLE email_verification_code (
            code_id    BIGINT       NOT NULL AUTO_INCREMENT,
            email      VARCHAR(100) NOT NULL,
            code_hash  VARCHAR(255) NOT NULL,
            purpose    VARCHAR(30)  NOT NULL DEFAULT 'register',
            expires_at DATETIME     NOT NULL,
            used_at    DATETIME     NULL,
            created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (code_id),
            KEY idx_email_verification_email   (email),
            KEY idx_email_verification_purpose (purpose),
            KEY idx_email_verification_expires (expires_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    END IF;

END$$

DELIMITER ;

-- Execute the migration procedure, then drop it
CALL migrate_20260712_add_email_verification();
DROP PROCEDURE IF EXISTS migrate_20260712_add_email_verification;

-- Verify results (optional — review output after execution)
SELECT
    COLUMN_NAME,
    COLUMN_TYPE,
    IS_NULLABLE,
    COLUMN_KEY
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'busmind'
  AND TABLE_NAME = 'user_account'
  AND COLUMN_NAME = 'email';

SELECT
    TABLE_NAME,
    TABLE_ROWS,
    CREATE_TIME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'busmind'
  AND TABLE_NAME = 'email_verification_code';