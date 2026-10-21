-- Final evidence only; all booleans must be true. Does not inspect business tables.
BEGIN READ ONLY;
SELECT count(*)=3 AS exactly_three_cases,
 count(*) FILTER(WHERE case_name IN ('rollback','race') AND claim_count=1)=2 AS two_consumed,
 count(*) FILTER(WHERE case_name='expired' AND claim_count=0)=1 AS expired_unused,
 max(claim_count)<=1 AS bounded_claims
 FROM cron_tx_probe.permits;
SELECT NOT EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
 WHERE n.nspname='cron_tx_probe' AND p.prosecdef) AS no_definer_functions;
ROLLBACK;
