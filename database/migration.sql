-- Campus Complaint Portal — Database Migration Script
-- Run these statements in your MySQL client against the complaint_portal database

-- 1. Add staff_type column to users table
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS staff_type ENUM('Cleaning','Technical','Electrical','Mechanical') DEFAULT NULL
    AFTER role;

-- 2. Add dynamic complaint detail fields (Hostel / Academic)
ALTER TABLE complaints
    ADD COLUMN IF NOT EXISTS room_number   VARCHAR(20)      DEFAULT NULL AFTER sla_deadline,
    ADD COLUMN IF NOT EXISTS block_letter  VARCHAR(10)      DEFAULT NULL AFTER room_number,
    ADD COLUMN IF NOT EXISTS hostel_type   ENUM('MH','LH') DEFAULT NULL AFTER block_letter,
    ADD COLUMN IF NOT EXISTS building_name VARCHAR(100)     DEFAULT NULL AFTER hostel_type;

-- 3. Add is_read column to notifications table
ALTER TABLE notifications
    ADD COLUMN IF NOT EXISTS is_read TINYINT(1) NOT NULL DEFAULT 0 AFTER message;

-- 4. Create audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id     INT       NOT NULL AUTO_INCREMENT,
    user_id    INT       DEFAULT NULL,
    action     TEXT      NOT NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (log_id),
    KEY idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Verify schema
DESCRIBE users;
DESCRIBE complaints;
DESCRIBE notifications;
DESCRIBE audit_logs;
