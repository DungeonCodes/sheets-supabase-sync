// connect is an injected, dedicated-role PostgreSQL driver. No driver/dependency installed.
// A live implementation must use verified TLS, connect/query deadlines and no retries.
export function createLedger({ connect }) {
  if (typeof connect !== 'function') throw new Error('ledger_configuration_invalid');
  async function call(readOnly, query, parameters) {
    let connection;
    try {
      connection = await connect();
      await connection.query(readOnly ? 'BEGIN READ ONLY' : 'BEGIN');
      await connection.query("SET LOCAL statement_timeout='5s'");
      await connection.query("SET LOCAL lock_timeout='2s'");
      await connection.query("SET LOCAL synchronous_commit='on'");
      const result = await connection.query(query, parameters);
      await connection.query('COMMIT');
      return result.rows[0].result;
    } catch {
      if (connection) { try { await connection.query('ROLLBACK'); } catch { /* No retry. */ } }
      throw new Error('ledger_unavailable');
    } finally {
      if (connection) { try { await connection.close(); } catch { /* Never leak driver credentials. */ } }
    }
  }
  return Object.freeze({
    claim: (id, sha, release) => call(false,
      'SELECT cron_dispatch_v2.claim($1::uuid,$2::text,$3::uuid) AS result', [id, sha, release]),
    confirm: (id, receipt) => call(true,
      'SELECT cron_dispatch_v2.confirm($1::uuid,$2::uuid) AS result', [id, receipt]),
    finish: (id, receipt, result) => call(false,
      'SELECT cron_dispatch_v2.finish($1::uuid,$2::uuid,$3::text,$4::integer,$5::bigint) AS result',
      [id, receipt, result.outcome, result.http_status, result.run_id]),
  });
}
