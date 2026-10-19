import { defineConfig } from "@playwright/test";
const basePath = process.env.E2E_BASE_PATH || "/";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  use: {
    baseURL: `http://127.0.0.1:4173${basePath}`,
    viewport: { width: 1440, height: 1000 },
    trace: "retain-on-failure",
    launchOptions: process.env.E2E_CHROME ? { channel: "chrome" } : {},
  },
  webServer: {
    command: "npm run preview",
    url: `http://127.0.0.1:4173${basePath}`,
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
});
