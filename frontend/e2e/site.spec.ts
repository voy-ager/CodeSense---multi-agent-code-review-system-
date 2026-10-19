import { test, expect, type Page } from "@playwright/test";

// The API is mocked at the network layer so these tests are fast and deterministic.
// Set E2E_LIVE=1 (with the backend running) to also run the real end-to-end review.
const API = "http://localhost:8002";
const PR = "https://github.com/psf/requests/pull/6746";

const REPORT = {
  pr_title: "feat: add chunked parameter",
  author: "octocat",
  total_findings: 3,
  by_severity: { critical: 1, high: 1, medium: 0, low: 1 },
  by_agent: { security: 2, performance: 0, testing: 0, style: 1 },
  summary: "Found 3 issue(s): 1 critical, 1 high, 0 medium, 1 low.",
  diff_truncated: true,
  failed_agents: [],
  findings: [
    { severity: "critical", file: "cfg.py", line: 4, category: "Hardcoded Secret", agent: "security", source: "static",
      issue: "AWS access key committed in plain text (AKIA…(20 chars)).", fix: "Rotate it." },
    { severity: "high", file: "a.py", line: 7, category: "XSS", agent: "security",
      issue: '<img src=x onerror="window.__xss=1">', fix: "<script>window.__xss=1</script>" },
    { severity: "low", file: "a.py", line: 9, category: "Naming", agent: "style", issue: "Rename o.", fix: "Use order." },
  ],
};

function sse(events: object[]): string {
  return events.map(e => `data: ${JSON.stringify(e)}\n\n`).join("") + "data: [DONE]\n\n";
}

async function mockStream(page: Page, events: object[]) {
  await page.route(`${API}/review/stream`, route =>
    route.fulfill({ status: 200, contentType: "text/event-stream", body: sse(events) }));
}

const errors: string[] = [];
test.beforeEach(async ({ page }) => {
  errors.length = 0;
  page.on("pageerror", e => errors.push(e.message));
  await page.goto("/");
});
test.afterEach(() => expect(errors, "uncaught page errors").toEqual([]));

test("renders the landing page without layout overflow", async ({ page }) => {
  await expect(page).toHaveTitle(/CodeSense/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("thinks in parallel");
  for (const id of ["review", "how-it-works", "about", "faq"]) await expect(page.locator(`#${id}`)).toBeAttached();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("hero walkthrough follows keyboard focus", async ({ page }) => {
  const perf = page.getByRole("button", { name: /Performance/ });
  await perf.focus();
  await expect(perf).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByText("N+1 query: one items lookup per order.")).toBeVisible();
});

test("streams a review and renders findings safely", async ({ page }) => {
  await mockStream(page, [
    { status: "starting", message: "Fetching PR diff from GitHub..." },
    { status: "diff_fetched", message: "PR: 'feat' — 3 files changed" },
    { status: "security_done", message: "Security: 1 issue(s) found" },
    { status: "static_done", message: "Static checks (secrets, deps, injection): 1 issue(s) found" },
    { status: "style_done", message: "Style: 1 issue(s) found" },
    { status: "complete", report: REPORT, cached: false },
  ]);
  await page.locator("#pr-url").fill(PR);
  await page.getByRole("button", { name: "Analyze PR" }).click();

  await expect(page.getByText("Analysis complete")).toBeVisible();
  await expect(page.getByText(REPORT.summary)).toBeVisible();
  await expect(page.getByText("rule-based", { exact: true })).toHaveCount(1);
  await expect(page.getByRole("note")).toContainText("Large PR");
  // Status messages are not double-prefixed with a check mark
  await expect(page.getByText(/✓\s*✓/)).toHaveCount(0);
  // Attacker-controlled finding text renders as text, never as HTML
  await expect(page.getByText('<img src=x onerror="window.__xss=1">')).toBeVisible();
  expect(await page.evaluate(() => (window as unknown as { __xss?: number }).__xss)).toBeUndefined();
});

test("filters findings by agent", async ({ page }) => {
  await mockStream(page, [{ status: "complete", report: REPORT, cached: true }]);
  await page.locator("#pr-url").fill(PR);
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: /style: 1/ }).click();
  await expect(page.getByText("Rename o.")).toBeVisible();
  await expect(page.getByText("Rotate it.")).toHaveCount(0);
});

test("shows the server's reason for a rejected URL", async ({ page }) => {
  await page.route(`${API}/review/stream`, route => route.fulfill({
    status: 400, contentType: "application/json",
    body: JSON.stringify({ detail: "URL must be a GitHub pull request, e.g. https://github.com/owner/repo/pull/123" }),
  }));
  await page.locator("#pr-url").fill("https://evil.com/pull/1");
  await page.keyboard.press("Enter");
  await expect(page.getByText(/must be a GitHub pull request/)).toBeVisible();
});

test("shows rate limiting clearly", async ({ page }) => {
  await page.route(`${API}/review/stream`, route => route.fulfill({
    status: 429, contentType: "application/json", body: JSON.stringify({ error: "Rate limit exceeded: 10 per 1 minute" }),
  }));
  await page.locator("#pr-url").fill(PR);
  await page.keyboard.press("Enter");
  await expect(page.getByText(/Rate limit exceeded/)).toBeVisible();
});

test("marks failed agents instead of hiding them", async ({ page }) => {
  await mockStream(page, [
    { status: "agent_failed", message: "Performance: agent failed — results incomplete" },
    { status: "complete", report: { ...REPORT, failed_agents: ["performance"] }, cached: false },
  ]);
  await page.locator("#pr-url").fill(PR);
  await page.keyboard.press("Enter");
  await expect(page.getByText("Performance: agent failed — results incomplete")).toBeVisible();
});

test("backend unreachable is reported, not a blank screen", async ({ page }) => {
  await page.route(`${API}/review/stream`, route => route.abort("connectionrefused"));
  await page.locator("#pr-url").fill(PR);
  await page.keyboard.press("Enter");
  await expect(page.locator("#review").getByText(/Failed to fetch|Failed to reach|NetworkError/)).toBeVisible();
});

test("FAQ works with the keyboard", async ({ page }) => {
  const first = page.locator("#faq summary").first();
  await first.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#faq details").first()).toHaveAttribute("open", "");
});

test("live: reviews a real PR end to end", async ({ page }) => {
  test.skip(!process.env.E2E_LIVE, "set E2E_LIVE=1 with the backend running");
  test.setTimeout(240_000);
  await page.getByRole("button", { name: /Try an example/ }).click();
  await expect(page.getByText("Analysis complete")).toBeVisible({ timeout: 220_000 });
  expect(await page.locator("#review article, #review .font-mono").count()).toBeGreaterThan(0);
});

// ── Regression tests for the independent QA pass ────────────────────────────

test("M7: incomplete review is never shown as 'no issues'", async ({ page }) => {
  await mockStream(page, [{ status: "complete", cached: false,
    report: { ...REPORT, findings: [], total_findings: 0, failed_agents: ["security", "performance", "testing"] } }]);
  await page.locator("#pr-url").fill(PR);
  await page.keyboard.press("Enter");
  // filter: Next.js renders its own (empty) role="alert" route announcer
  const banner = page.getByRole("alert").filter({ hasText: "Incomplete review" });
  await expect(banner).toContainText("does not mean the code is clean");
});

test("M8: a stream that ends without a result shows an error", async ({ page }) => {
  await page.route(`${API}/review/stream`, route => route.fulfill({ status: 200, contentType: "text/event-stream",
    body: `data: ${JSON.stringify({ status: "diff_fetched", message: "PR: 'x' — 1 files changed" })}\n\n` }));
  await page.locator("#pr-url").fill(PR);
  await page.keyboard.press("Enter");
  await expect(page.getByText(/Connection lost before the review finished/)).toBeVisible();
});

test("M9: long file paths do not overflow the page", async ({ page }) => {
  const path = "src/components/dashboard/settings/NotificationPreferencesPanel" + "Extremely".repeat(8) + ".tsx";
  await mockStream(page, [{ status: "complete", cached: true,
    report: { ...REPORT, findings: [{ ...REPORT.findings[2], file: path }] } }]);
  await page.locator("#pr-url").fill(PR);
  await page.keyboard.press("Enter");
  await expect(page.getByText(path, { exact: false })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("L4: validation error lists are readable", async ({ page }) => {
  await page.route(`${API}/review/stream`, route => route.fulfill({ status: 422, contentType: "application/json",
    body: JSON.stringify({ detail: [{ loc: ["body", "pr_url"], msg: "String should have at most 500 characters" }] }) }));
  await page.locator("#pr-url").fill(PR);
  await page.keyboard.press("Enter");
  await expect(page.getByText("String should have at most 500 characters")).toBeVisible();
});

test("L5: progress is announced and filters expose pressed state", async ({ page }) => {
  await mockStream(page, [{ status: "complete", report: REPORT, cached: true }]);
  await page.locator("#pr-url").fill(PR);
  await page.keyboard.press("Enter");
  await expect(page.getByRole("status")).toContainText("Analysis complete");
  const style = page.getByRole("button", { name: /style: 1/ });
  await expect(style).toHaveAttribute("aria-pressed", "false");
  await style.click();
  await expect(style).toHaveAttribute("aria-pressed", "true");
});

test("stale cached review is labelled", async ({ page }) => {
  await mockStream(page, [{ status: "complete", report: { ...REPORT, stale: true }, cached: true }]);
  await page.locator("#pr-url").fill(PR);
  await page.keyboard.press("Enter");
  await expect(page.getByText(/may predate the latest commits/)).toBeVisible();
});
