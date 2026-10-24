// Drives the app like a technician, supervisor and admin, and saves the screenshots used in
// DEMO.md. It doubles as an end-to-end smoke test: any step that fails stops the run.
//
// Needs: a running Thunai with fresh SAMPLE data (python -m app.cli init) and Playwright.
//   BASE_URL=http://localhost:8000 node docs/capture-demo.mjs
import { createRequire } from "node:module";
import { mkdirSync } from "node:fs";
import { execSync } from "node:child_process";

const require = createRequire(import.meta.url);
let playwright;
try {
  playwright = require("playwright");
} catch {
  playwright = require(`${execSync("npm root -g").toString().trim()}/playwright`);
}

const BASE = process.env.BASE_URL ?? "http://localhost:8000";
const OUT = new URL("./screenshots/", import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await playwright.chromium.launch({
  args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
});
const phone = {
  ignoreHTTPSErrors: true, // Caddy's internal certificate on https://localhost
  viewport: { width: 360, height: 780 },
  deviceScaleFactor: 2,
  isMobile: true,
  hasTouch: true,
  timezoneId: "Asia/Kolkata",
  locale: "en-IN",
};

async function shot(page, name) {
  await page.waitForTimeout(300);
  // A page wider than the phone makes mobile browsers zoom out; treat it as a failure.
  const { sw, w } = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, w: innerWidth }));
  if (sw > w + 1) throw new Error(`${name}: page is ${sw}px wide on a ${w}px screen`);
  await page.screenshot({ path: `${OUT}${name}.png` });
  console.log("saved", name);
}

/** Answer OK on the current step and wait for the next step (or the end of the procedure). */
async function okStep(page) {
  const before = await page.locator(".step-no").textContent();
  await page.getByRole("button", { name: "OK", exact: true }).click();
  await page.waitForFunction((b) => {
    const el = document.querySelector(".step-no");
    return !el || el.textContent !== b;
  }, before);
}

async function login(page, emp, lang, beforeSubmit) {
  await page.goto(`${BASE}/login`);
  await page.evaluate((l) => localStorage.setItem("thunai-lang", l), lang);
  await page.reload();
  await page.locator("input.input-big").fill(emp);
  for (const d of "1234") await page.getByRole("button", { name: d, exact: true }).click();
  if (beforeSubmit) await beforeSubmit();
  await page.locator(".login .btn-primary").click();
  await page.locator(".greeting").waitFor();
}

// ---- 1. Technician (Tamil): Ask Thunai --------------------------------------------------------
{
  const ctx = await browser.newContext({ ...phone, permissions: ["microphone"] });
  const page = await ctx.newPage();
  await login(page, "D-TECH1", "ta", () => shot(page, "01-login-ta"));
  await shot(page, "02-home-ta");

  await page.getByRole("button", { name: /Thunai-கிட்ட கேளுங்க/ }).click();
  await page.getByText("DEMO-SF-01").first().click();
  await page.locator("textarea").fill("Cylinder return aagala");
  await shot(page, "03-ask-describe-ta");
  await page.getByRole("button", { name: "உதவி வாங்கு" }).click();
  await page.getByText("சில சின்ன கேள்விகள்").waitFor();
  for (const q of await page.locator(".question").all()) await q.locator(".option").first().click();
  await shot(page, "04-ask-questions-ta");
  await page.getByRole("button", { name: "தொடரு" }).click();
  await page.locator(".step").waitFor();
  await shot(page, "05-step-safety-ta");
  await okStep(page); // LOTO
  await okStep(page); // stored air
  await page.getByText("ஏன் இந்த step?").click();
  await shot(page, "06-why-this-step-ta");
  await page.getByRole("button", { name: "மூடு" }).click();
  await okStep(page);
  await page.locator(".badge-danger").waitFor();
  await shot(page, "07-step-authorised-ta");
  // finish the procedure
  while (await page.locator(".step").count()) await okStep(page);
  await page.getByText("Machine இப்போ ஓடுதா?").waitFor();
  await shot(page, "08-is-running-ta");
  await page.getByRole("button", { name: "ஆமா, ஓடுது" }).click();
  await page.locator(".field-ai, .field-unsure").first().waitFor();
  await shot(page, "09-draft-log-from-session-ta");
  await page.locator("textarea").nth(2).fill("Coil maathiten, 10 cycle check OK");
  await page.getByRole("button", { name: "Submit", exact: true }).click();
  await page.locator(".kpis").waitFor();
  await shot(page, "10-machine-page-ta");

  // ---- voice log with the fake microphone (mock speech-to-text) -------------------------------
  await page.goto(`${BASE}/log/new/DEMO-SF-02`);
  await page.locator(".mic-btn").waitFor();
  const mic = await page.locator(".mic-btn").boundingBox();
  await page.mouse.move(mic.x + mic.width / 2, mic.y + mic.height / 2);
  await page.mouse.down();
  await page.waitForTimeout(2200);
  await page.mouse.up();
  await page.locator(".field-ai").first().waitFor({ timeout: 15000 });
  await shot(page, "11-voice-log-filled-ta");
  await page.getByRole("button", { name: "Submit", exact: true }).click();
  await page.locator(".kpis").waitFor();

  // ---- offline log ------------------------------------------------------------------------
  await page.goto(`${BASE}/log/new/DEMO-LP-01`);
  await page.locator("textarea").first().waitFor();
  await ctx.setOffline(true);
  await page.locator("textarea").nth(0).fill("Label print faded again");
  await page.locator("textarea").nth(2).fill("Cleaned print head");
  await page.getByRole("button", { name: "Submit", exact: true }).click();
  await page.locator(".banner").waitFor();
  await shot(page, "12-offline-queued-ta");
  await ctx.setOffline(false);
  await page.waitForTimeout(2500);
  await ctx.close();
}

// ---- 2. Safety refusal (English) ------------------------------------------------------------
{
  const ctx = await browser.newContext(phone);
  const page = await ctx.newPage();
  await login(page, "D-TECH2", "en");
  await page.goto(`${BASE}/ask/DEMO-NT-01`);
  await page.locator("textarea").fill("Light curtain keeps stopping the press. How do I bypass it?");
  await page.getByRole("button", { name: "Get help" }).click();
  await page.getByText("Not allowed").waitFor();
  await shot(page, "13-safety-refusal-en");

  await page.goto(`${BASE}/ask/DEMO-AC-01`);
  await page.locator("textarea").fill("Door seal leaking steam");
  await page.getByRole("button", { name: "Get help" }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.locator(".step").waitFor();
  await okStep(page);
  await shot(page, "14-autoclave-pressure-step-en");
  await page.getByRole("button", { name: "Call supervisor" }).click();
  await page.locator(".summary").waitFor();
  await shot(page, "15-call-supervisor-en");
  await ctx.close();
}

// ---- 3. Supervisor review and admin ---------------------------------------------------------
{
  const ctx = await browser.newContext(phone);
  const page = await ctx.newPage();
  await login(page, "D-SUP1", "en");
  await page.goto(`${BASE}/review`);
  await page.getByText("Logs to verify").waitFor();
  await shot(page, "16-review-queue-en");
  await page.getByRole("button", { name: "Verify" }).first().click();
  await page.waitForTimeout(800);
  await page.goto(`${BASE}/m/DEMO-SF-01`);
  await page.locator(".kpis").waitFor();
  await page.getByRole("button", { name: /FC-1/ }).click();
  await shot(page, "17-machine-page-en");
  await ctx.close();

  const admin = await browser.newContext({ viewport: { width: 1024, height: 768 }, deviceScaleFactor: 1, timezoneId: "Asia/Kolkata", ignoreHTTPSErrors: true });
  const a = await admin.newPage();
  await login(a, "D-ADMIN", "en");
  await a.goto(`${BASE}/admin?tab=import`);
  await a.getByText("Machine master").waitFor();
  await shot(a, "18-admin-import");
  await a.goto(`${BASE}/admin/qr`);
  await a.locator(".qr-img svg").first().waitFor();
  await shot(a, "19-qr-stickers");
  await a.goto(`${BASE}/admin?tab=usage`);
  await a.locator(".table").waitFor();
  await shot(a, "20-ai-usage");
  await admin.close();
}


// ================= Phase 2 =================
/** Calls the API with the logged-in user's token (setup steps that are not the point of a screenshot). */
async function apiCall(page, method, path, body) {
  return page.evaluate(
    async ([m, p, b]) => {
      const auth = JSON.parse(sessionStorage.getItem("thunai-auth") ?? localStorage.getItem("thunai-auth"));
      const r = await fetch(p, {
        method: m,
        headers: { authorization: `Bearer ${auth.token}`, "content-type": "application/json" },
        body: b ? JSON.stringify(b) : undefined,
      });
      if (!r.ok) throw new Error(`${m} ${p}: ${r.status} ${await r.text()}`);
      return r.json();
    },
    [method, path, body],
  );
}

const log = (machine, issue, cause, fix, min) => ({
  machine_no: machine,
  issue: { original: issue },
  root_cause: { original: cause },
  corrective_action: { original: fix },
  downtime_min: min,
});

// ---- 4. Technician: more logs, an expert tip and an alarm code (Tamil) ------------------------
{
  const ctx = await browser.newContext({ ...phone, permissions: ["microphone"] });
  const page = await ctx.newPage();
  await login(page, "D-TECH1", "ta");
  // Two more "label print faded" logs: with the sample log that makes 3, so a fault card is drafted.
  await apiCall(page, "POST", "/api/logs", log("DEMO-LP-01", "Label print faded", "Print head dirty", "Cleaned print head with IPA", 15));
  await apiCall(page, "POST", "/api/logs", log("DEMO-LP-01", "Label print faded", "Ribbon wrinkled", "Reloaded ribbon and set tension", 25));
  // A log that contradicts the approved card FC-1 (its causes do not include an air leak).
  await apiCall(page, "POST", "/api/logs", log("DEMO-SF-01", "Cylinder not returning", "Air leak at push-in fitting", "Replaced the fitting", 30));

  await page.goto(`${BASE}/m/DEMO-SF-01`);
  await page.locator(".kpis").waitFor();
  await page.getByRole("button", { name: /Tip சேர்/ }).click();
  await page.locator(".sheet textarea").fill("Coil seekiram burn aagum, air pressure 6 bar mela irundha. FRL-a first check pannunga.");
  await shot(page, "21-add-expert-tip-ta");
  await page.locator(".sheet .btn-primary").click();
  await page.waitForTimeout(800);

  await page.goto(`${BASE}/ask/DEMO-SF-01`);
  await page.locator("textarea").fill("Machine nikkudhu");
  await page.locator("input.input").first().fill("A101");
  await page.locator(".alarm-card").waitFor();
  await shot(page, "22-alarm-code-lookup-ta");
  await ctx.close();
}

// ---- 5. Supervisor: review fault cards and tips, dashboard -----------------------------------
{
  const ctx = await browser.newContext(phone);
  const page = await ctx.newPage();
  await login(page, "D-SUP1", "en");
  await page.goto(`${BASE}/review`);
  await page.getByText("Fault cards to review").waitFor();
  await page.locator(".list-item", { hasText: "FC-" }).first().waitFor({ timeout: 20000 });
  await shot(page, "23-review-cards-and-tips-en");
  // Approve the expert tip.
  const tipCard = page.locator(".card", { hasText: "Coil seekiram" });
  await tipCard.getByRole("button", { name: "Approve" }).click();
  await page.waitForTimeout(600);
  // Open the new draft card for the label printer.
  await page.locator(".list-item", { hasText: "DEMO-LP-01" }).first().click();
  await page.locator(".chip", { hasText: "Draft" }).waitFor();
  await shot(page, "24-draft-fault-card-en");
  await page.getByRole("button", { name: "Approve" }).click();
  await page.locator(".chip", { hasText: "Approved" }).waitFor();
  // The flagged card FC-1.
  await page.goto(`${BASE}/cards/1`);
  await page.locator(".note-warn").waitFor();
  await shot(page, "25-flagged-card-en");
  await page.goto(`${BASE}/dashboard`);
  await page.locator(".stat-grid").first().waitFor();
  await shot(page, "26-dashboard-en");
  await page.goto(`${BASE}/m/DEMO-SF-01`);
  await page.locator(".tip").first().waitFor();
  await page.locator(".tip").first().scrollIntoViewIfNeeded();
  await shot(page, "27-machine-tips-documents-en");
  await ctx.close();

  const admin = await browser.newContext({ viewport: { width: 1024, height: 768 }, deviceScaleFactor: 1, timezoneId: "Asia/Kolkata", ignoreHTTPSErrors: true });
  const a = await admin.newPage();
  await login(a, "D-ADMIN", "en");
  await a.goto(`${BASE}/admin?tab=documents`);
  await a.locator(".table tbody tr").first().waitFor();
  await shot(a, "28-admin-documents");
  await a.goto(`${BASE}/dashboard`);
  await a.locator(".bars").first().waitFor();
  await shot(a, "29-dashboard-wide");
  await admin.close();
}

await browser.close();
console.log("Demo run finished");
