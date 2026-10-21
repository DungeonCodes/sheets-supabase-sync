// No deployable ingress identity or database driver is provisioned in this gate.
// Keep imports resolvable offline; do not read platform-wide keys or serve a route.
import { createHandler, createWakeHandler } from './dispatch.mjs';
import { createLedger } from './ledger.mjs';
export { createHandler, createWakeHandler, createLedger };
throw new Error('redesign_requires_verified_ingress_and_dedicated_db_identity');
