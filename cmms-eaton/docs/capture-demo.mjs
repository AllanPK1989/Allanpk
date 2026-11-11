// Smoke test and screenshot capture against the production build.
// Usage: npm run build && node docs/capture-demo.mjs   (or BASE_URL=https://host node docs/capture-demo.mjs)
import { spawn } from "node:child_process";
import { mkdirSync } from "node:fs";
import { createRequire } from "node:module";

const { chromium, devices } = createRequire(import.meta.url)("playwright");
const root = new URL("..", import.meta.url).pathname;
const OUT = new URL("./screenshots/", import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });
const BASE = process.env.BASE_URL || "http://localhost:4173";
const PASSWORD = "demo1234";

let server = null;
if (!process.env.BASE_URL) {
  server = spawn("npx", ["vite", "preview", "--port", "4173", "--strictPort"], { cwd: root, stdio: "ignore" });
  for (let i = 0; i < 60; i++) {
    try {
      const res = await fetch(BASE);
      if (res.ok) break;
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 500));
  }
}

const browser = await chromium.launch();
const errors = [];
const failures = [];
const context = await browser.newContext({ viewport: { width: 1366, height: 860 }, deviceScaleFactor: 2 });
const page = await context.newPage();
page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
page.on("console", (m) => {
  if (m.type() === "error") errors.push(`console: ${m.text()}`);
});

const check = (cond, label) => {
  if (!cond) failures.push(label);
  console.log(`${cond ? "ok  " : "FAIL"} ${label}`);
};
async function shot(name) {
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}${name}.png` });
  console.log(`shot ${name}`);
}
async function login(id) {
  await page.goto(`${BASE}/#/login`);
  await page.waitForSelector('input[autocomplete="username"]', { timeout: 30_000 });
  await page.fill('input[autocomplete="username"]', id);
  await page.fill('input[type="password"]', PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForSelector(".topbar", { timeout: 30_000 });
}
async function logout() {
  await page.click(".user-chip");
  await page.click(".menu >> text=Log out");
  await page.waitForSelector('input[autocomplete="username"]');
}

// 1. Login screen and owner tour
await page.goto(`${BASE}/`);
await page.waitForSelector('input[autocomplete="username"]', { timeout: 60_000 });
await shot("01-login");
await login("D-OWNER");
check(await page.isVisible("text=Open breakdowns"), "owner dashboard shows KPIs");
await shot("02-dashboard-owner");
await page.goto(`${BASE}/#/work-orders`);
await page.waitForSelector("table.data tbody tr");
check((await page.locator("table.data tbody tr").count()) > 3, "work order list has rows");
await shot("03-work-orders");
await page.click("table.data tbody tr >> nth=0");
await page.waitForSelector("text=Assignment");
await shot("04-work-order-detail");
await page.goto(`${BASE}/#/pm`);
await page.waitForSelector("table.data tbody tr");
check(await page.isVisible("text=Generate due work orders"), "owner can generate PM work orders");
await shot("05-pm-plans");
await page.click(".tabs >> text=Calendar");
await page.waitForSelector(".calendar");
await shot("06-pm-calendar");
await page.goto(`${BASE}/#/assets`);
await page.waitForSelector("table.data tbody tr");
await shot("07-assets");
await page.click("table.data tbody tr >> nth=0");
await page.waitForSelector("text=QR code");
await page.waitForSelector('img[alt^="QR code"]');
await shot("08-asset-detail");
await page.goto(`${BASE}/#/parts`);
await page.waitForSelector("table.data tbody tr");
await shot("09-parts");
await page.goto(`${BASE}/#/reports`);
await page.waitForSelector("text=Breakdowns by failure code");
await shot("10-reports");
await page.goto(`${BASE}/#/users`);
await page.waitForSelector("table.data tbody tr");
await shot("11-users");
await page.goto(`${BASE}/#/settings?tab=storage`);
await page.waitForSelector("text=Where the data lives");
await shot("12-settings-storage");
await page.goto(`${BASE}/#/settings?tab=lines`);
await page.waitForSelector("text=Production lines");
await shot("13-settings-lines");
await logout();

// 2. Production supervisor reports a breakdown
await login("D-PSUP");
check(await page.isVisible("text=Awaiting your handback"), "production dashboard shows handback queue");
check(!(await page.isVisible("nav >> text=Users")), "production supervisor has no Users menu");
await shot("14-dashboard-production");
await page.getByRole("button", { name: "Report breakdown" }).first().click();
await page.waitForSelector(".modal");
await page.locator('.modal label:has-text("Machine") select').first().selectOption({ index: 1 });
await page.locator('.modal label:has-text("Title") input').fill("Smoke test: conveyor belt stopped, motor humming");
await shot("15-report-breakdown");
await page.click(".modal-foot >> text=Report breakdown");
await page.waitForSelector("text=Machine down for");
const woUrl = page.url();
const woNo = (await page.locator("h1").innerText()).trim().split(/\s+/)[0];
check(/^WO-\d{4}-\d{5}$/.test(woNo), `breakdown created as ${woNo}`);
await shot("16-breakdown-open");
await logout();

// 3. Technician picks it up, completes it
await login("D-TECH1");
check(page.url().includes("/work-orders"), "technician lands on their work orders after sign-in");
await page.goto(`${BASE}/#/`);
await page.waitForSelector("text=My work orders");
check(await page.isVisible("text=My work orders"), "technician dashboard shows my work orders");
await shot("17-dashboard-technician");
await page.goto(woUrl);
await page.waitForSelector("text=Start work");
await page.click("text=Start work");
await page.waitForSelector(".page-actions >> text=Complete");
await page.click(".page-actions >> text=Complete");
await page.waitForSelector(".modal");
await page.locator('.modal label:has-text("Root cause") input').fill("Drive belt snapped");
await page.locator('.modal label:has-text("Action taken") textarea').fill("Replaced belt, aligned pulleys, test run OK");
await shot("18-complete-breakdown");
await page.click(".modal-foot >> text=Mark completed");
await page.waitForSelector("text=Waiting for the production supervisor");
check(await page.isVisible(".badge >> text=Completed"), "work order shows Completed");
await logout();

// 4. Production confirms handback, maintenance supervisor closes
await login("D-PSUP");
await page.goto(woUrl);
await page.click("text=Confirm handback");
await page.waitForSelector("text=Handback recorded");
await logout();
await login("D-MSUP");
await page.goto(woUrl);
await page.click(".page-actions >> text=Close");
await page.waitForSelector(".badge >> text=Closed");
check(await page.isVisible(".badge >> text=Closed"), "maintenance supervisor closed the work order");
await shot("19-closed-breakdown");
// PM generation
await page.goto(`${BASE}/#/pm`);
await page.waitForSelector("table.data tbody tr");
const genBtn = page.locator("button", { hasText: "Generate due work orders" });
if (await genBtn.isEnabled()) {
  await genBtn.click();
  await page.waitForSelector(".toast");
  check((await page.locator(".toast").last().innerText()).includes("created"), "PM work orders generated");
}
await logout();

// 5. Phone layout
const phone = await browser.newContext({ ...devices["iPhone 13"] });
const p2 = phone.newPage ? await phone.newPage() : page;
p2.on("pageerror", (e) => errors.push(`pageerror(mobile): ${e.message}`));
await p2.goto(`${BASE}/#/login`);
await p2.waitForSelector('input[autocomplete="username"]', { timeout: 30_000 });
await p2.fill('input[autocomplete="username"]', "D-TECH1");
await p2.fill('input[type="password"]', PASSWORD);
await p2.click('button[type="submit"]');
await p2.waitForSelector(".topbar", { timeout: 30_000 });
await p2.goto(`${BASE}/#/`);
await p2.waitForSelector("text=My work orders");
await p2.waitForTimeout(400);
await p2.screenshot({ path: `${OUT}20-mobile-dashboard.png` });
await p2.goto(`${BASE}/#/work-orders?tab=mine`);
await p2.waitForSelector("table.data");
await p2.waitForTimeout(400);
await p2.screenshot({ path: `${OUT}21-mobile-work-orders.png` });
await p2.click(".hamburger");
await p2.waitForTimeout(300);
await p2.screenshot({ path: `${OUT}22-mobile-menu.png` });
console.log("shot 20-22 mobile");

await browser.close();
server?.kill();

const relevant = errors.filter((e) => !e.includes("favicon"));
check(relevant.length === 0, `no page or console errors (${relevant.length})`);
for (const e of relevant) console.log("   ", e);
if (failures.length) {
  console.log(`\n${failures.length} check(s) failed`);
  process.exit(1);
}
console.log("\nAll checks passed");
