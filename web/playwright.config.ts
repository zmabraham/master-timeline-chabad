import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173/master-timeline-chabad/',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
  use: { baseURL: 'http://localhost:5173/master-timeline-chabad/' },
});
