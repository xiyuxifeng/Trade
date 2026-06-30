import { defineConfig } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:8000";
const localhostNoProxy = ["127.0.0.1", "localhost", "::1"];

for (const key of ["NO_PROXY", "no_proxy"] as const) {
  const existing = process.env[key]?.split(",").map((item) => item.trim()).filter(Boolean) ?? [];
  process.env[key] = Array.from(new Set([...existing, ...localhostNoProxy])).join(",");
}

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 120_000,
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER
    ? undefined
    : {
        command: "pnpm build && cd .. && CONFIG_PATH=config/app.template.yaml python -m scripts.web_local start-api",
        url: baseURL,
        reuseExistingServer: true,
        timeout: 300_000,
      },
});
