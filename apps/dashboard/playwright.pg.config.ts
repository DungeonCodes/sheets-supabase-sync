import { defineConfig } from '@playwright/test';

if (process.env.RUN_ANALYTICS_LOCAL_TESTS !== '1' || !process.env.DASHBOARD_DATABASE_URL || !process.env.DASHBOARD_SOURCE_REF || !process.env.DASHBOARD_ACCESS_TOKEN) {
  throw new Error('Explicit local fixture database and dashboard configuration required');
}
export default defineConfig({
  testDir:'./tests-postgres', workers:1, reporter:'list',
  use:{baseURL:'http://127.0.0.1:3218'},
  webServer:{command:'npm run dev -- --port 3218',url:'http://127.0.0.1:3218',reuseExistingServer:false,timeout:60000,
    env:{...process.env,DASHBOARD_MODE:'postgres',NEXT_DIST_DIR:'.next-postgres-test'}},
});
