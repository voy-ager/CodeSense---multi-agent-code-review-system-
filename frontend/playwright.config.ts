import { defineConfig, devices } from "@playwright/test";

// Uses an installed browser channel (Edge locally, Chrome on CI runners) so no
// browser download is needed. Override with PW_CHANNEL.
const channel = process.env.PW_CHANNEL ?? (process.env.CI ? "chrome" : "msedge");

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: { baseURL: "http://localhost:3000", channel, trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], channel } },
    { name: "mobile",  use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, channel } },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
