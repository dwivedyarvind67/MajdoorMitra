-- Safe rollback of hourly/overtime and payment-allocation additions.
-- It refuses to remove any data already entered through the new fields.
DO $$
BEGIN
    IF to_regclass('public.payment_allocations') IS NOT NULL
       AND EXISTS (SELECT 1 FROM public.payment_allocations) THEN
        RAISE EXCEPTION 'payment_allocations contains records; export them before rollback';
    END IF;
    IF to_regclass('public.work_entries') IS NOT NULL
       AND EXISTS (
           SELECT 1 FROM public.work_entries
           WHERE wage_basis <> 'daily'
              OR hourly_rate IS NOT NULL
              OR overtime_hours <> 0
              OR overtime_multiplier <> 1.5
       ) THEN
        RAISE EXCEPTION 'work_entries contains hourly/overtime data; export it before rollback';
    END IF;
END $$;

DROP TABLE IF EXISTS payment_allocations;
ALTER TABLE work_entries DROP COLUMN IF EXISTS overtime_multiplier;
ALTER TABLE work_entries DROP COLUMN IF EXISTS overtime_hours;
ALTER TABLE work_entries DROP COLUMN IF EXISTS hourly_rate;
ALTER TABLE work_entries DROP COLUMN IF EXISTS wage_basis;
