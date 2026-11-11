import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir:'./tests', workers:1, reporter:'list',
  use:{baseURL:'http://127.0.0.1:3217'},
  webServer:{command:'npm run dev -- --port 3217',url:'http://127.0.0.1:3217',reuseExistingServer:false,timeout:60000,
    env:{...process.env,DASHBOARD_MODE:'demo',DASHBOARD_ACCESS_TOKEN:'synthetic-dashboard-token-123456',NEXT_DIST_DIR:'.next-playwright'}},
});
