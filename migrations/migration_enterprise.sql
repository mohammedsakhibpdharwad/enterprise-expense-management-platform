-- Safe additive enterprise migration. Does not drop tables or delete data.
-- Prefer: python scripts/migrate_enterprise.py  (idempotent)
-- Or run this file once against expense_management.

USE expense_management;

ALTER TABLE users
  MODIFY COLUMN role VARCHAR(32) NOT NULL DEFAULT 'employee';

UPDATE users SET role = 'super_admin' WHERE role IN ('admin');

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS employee_code VARCHAR(32) NULL,
  ADD COLUMN IF NOT EXISTS department_id INT NULL,
  ADD COLUMN IF NOT EXISTS manager_id INT NULL,
  ADD COLUMN IF NOT EXISTS is_active TINYINT(1) NOT NULL DEFAULT 1;

CREATE TABLE IF NOT EXISTS departments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  manager_id INT NULL,
  monthly_budget DECIMAL(12, 2) NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_departments_manager (manager_id)
);

CREATE TABLE IF NOT EXISTS approval_rules (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  min_amount DECIMAL(12, 2) NOT NULL DEFAULT 0,
  max_amount DECIMAL(12, 2) NOT NULL,
  require_manager TINYINT(1) NOT NULL DEFAULT 1,
  require_finance TINYINT(1) NOT NULL DEFAULT 0,
  require_super TINYINT(1) NOT NULL DEFAULT 0,
  is_active TINYINT(1) NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS expense_policies (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  policy_type VARCHAR(40) NOT NULL,
  category_id INT NULL,
  department_id INT NULL,
  threshold DECIMAL(12, 2) NULL,
  extra_value VARCHAR(120) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1
);

ALTER TABLE expenses
  ADD COLUMN IF NOT EXISTS current_stage VARCHAR(32) NOT NULL DEFAULT 'manager',
  ADD COLUMN IF NOT EXISTS required_stages VARCHAR(120) NOT NULL DEFAULT 'manager',
  ADD COLUMN IF NOT EXISTS policy_violations TEXT NULL,
  ADD COLUMN IF NOT EXISTS risk_level VARCHAR(16) NOT NULL DEFAULT 'none',
  ADD COLUMN IF NOT EXISTS risk_reasons TEXT NULL,
  ADD COLUMN IF NOT EXISTS reopen_count INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS receipt_hash VARCHAR(64) NULL;

CREATE TABLE IF NOT EXISTS approval_audit (
  id INT AUTO_INCREMENT PRIMARY KEY,
  expense_id INT NOT NULL,
  action VARCHAR(40) NOT NULL,
  previous_status VARCHAR(32) NULL,
  new_status VARCHAR(32) NULL,
  previous_stage VARCHAR(32) NULL,
  new_stage VARCHAR(32) NULL,
  performed_by INT NULL,
  comment TEXT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_audit_expense (expense_id, created_at),
  INDEX idx_audit_actor (performed_by),
  CONSTRAINT fk_audit_expense FOREIGN KEY (expense_id) REFERENCES expenses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  title VARCHAR(150) NOT NULL,
  message VARCHAR(500) NOT NULL,
  link VARCHAR(255) NULL,
  is_read TINYINT(1) NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_notifications_user (user_id, is_read, created_at),
  CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_users_department_id ON users (department_id);
CREATE INDEX IF NOT EXISTS idx_users_manager_id ON users (manager_id);
CREATE INDEX IF NOT EXISTS idx_users_employee_code ON users (employee_code);
CREATE INDEX IF NOT EXISTS idx_expenses_stage ON expenses (current_stage, status);
CREATE INDEX IF NOT EXISTS idx_expenses_amount ON expenses (amount);
CREATE INDEX IF NOT EXISTS idx_expenses_receipt_hash ON expenses (receipt_hash);
