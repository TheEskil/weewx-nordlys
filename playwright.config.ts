import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: 'tests/e2e',
  timeout: 30000,
  use: {
    baseURL: 'http://localhost:5183',
    colorScheme: 'dark',
  },
  webServer: {
    command: 'npm run dev -- --port 5183 --strictPort',
    port: 5183,
    reuseExistingServer: true,
  },
})
