-- Phase 3 migration
-- No schema changes required for expense CRUD, analytics, or UI polish.
-- Existing tables (users, categories, expenses) already support all features.
-- Safe to run on existing databases.

USE expense_management;

-- Optional performance index for analytics date-range queries (ignore error if index exists)
-- CREATE INDEX idx_expenses_status_date ON expenses (status, date);
