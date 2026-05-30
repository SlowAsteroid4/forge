-- WP-02a: cp_approval_fields migration (2026-05-30)
-- Adds cp_rejection_reason and cp_modified_post_approval to subtasks

ALTER TABLE subtasks ADD COLUMN cp_rejection_reason TEXT;
ALTER TABLE subtasks ADD COLUMN cp_modified_post_approval BOOLEAN NOT NULL DEFAULT 0;

-- Backfill: mark L/XL subtasks that need approval
UPDATE subtasks SET cp_approval_required = 1
WHERE complexity_size IN ('L', 'XL') AND cp_approved_at IS NULL;
