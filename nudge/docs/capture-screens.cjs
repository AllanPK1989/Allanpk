// Captures the screenshots used in DEMO.md from a running demo (sample data, PIN 1234).
//   node docs/capture-screens.cjs [base-url] [out-dir]
// Uses Playwright's Chromium with a fake microphone so the voice flow can be recorded.
const { chromium } = require("playwright");

const BASE = process.argv[2] || "http://localhost:8000";
const OUT = process.argv[3] || `${__dirname}/screens`;

(async () => {
  const browser = await chromium.launch({ args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"] });
  const phone = await browser.newContext({
    viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true,
    timezoneId: "Asia/Kolkata", locale: "en-IN", permissions: ["microphone"],
  });
  const p = await phone.newPage();
  const shot = (name) => p.screenshot({ path: `${OUT}/${name}.png` });
  const go = async (path) => { await p.goto(BASE + path); await p.waitForTimeout(900); };

  await go("/");
  await shot("01-pin");
  for (const d of "1234") await p.getByRole("button", { name: d, exact: true }).click();
  await p.getByRole("button", { name: "Continue" }).click();
  await p.waitForTimeout(1200);
  await shot("02-home");

  await p.getByRole("button", { name: /Add tasks by voice/ }).click();
  await p.waitForTimeout(2500);
  await shot("03-listening");
  await p.getByRole("button", { name: "Stop recording" }).click();
  await p.waitForSelector("text=Check these", { timeout: 15000 });
  await p.waitForTimeout(300);
  await shot("04-review");
  await p.getByRole("button", { name: /^Save 3 tasks/ }).click();
  await p.waitForTimeout(800);

  await go("/tasks?lane=today");
  await p.getByRole("button", { name: /^Mark done: Call amma/ }).click();
  await p.waitForTimeout(600);
  await shot("05-done-follow-up");

  await go("/tasks?lane=waiting");
  await p.getByRole("link").filter({ hasText: "Follow up with Ravi on the spares quotation" }).first().click();
  await p.waitForTimeout(900);
  await p.getByRole("button", { name: "Write a nudge" }).first().click();
  await p.waitForTimeout(800);
  await shot("06-nudge-message");
  await p.keyboard.press("Escape");

  await go("/?capture=text");
  await p.locator("textarea").fill("what's pending with Ravi?");
  await p.getByRole("button", { name: "Continue" }).click();
  await p.waitForSelector("text=Here's what I found");
  await shot("07-ask");
  await p.keyboard.press("Escape");

  for (const [path, name] of [["/briefing", "08-briefing"], ["/review", "09-weekly-review"], ["/people", "10-people"], ["/settings", "11-settings"]]) {
    await go(path);
    await shot(name);
  }

  for (const scheme of ["light", "dark"]) {
    const desk = await browser.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 2, colorScheme: scheme, timezoneId: "Asia/Kolkata", locale: "en-IN" });
    const d = await desk.newPage();
    await d.goto(BASE + "/");
    await d.waitForTimeout(500);
    for (const k of "1234") await d.keyboard.press(k);
    await d.keyboard.press("Enter");
    await d.waitForTimeout(1400);
    await d.screenshot({ path: `${OUT}/12-desktop-${scheme}.png`, fullPage: true });
    await desk.close();
  }
  await browser.close();
  console.log(`Saved screenshots to ${OUT}`);
})();
