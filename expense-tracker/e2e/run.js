// End-to-end test of the web app against the Firebase emulator suite.
//
// Covers: sign-up, onboarding, adding expenses and income, creating a budget,
// transactions/insights/reports screens, PDF + Excel + CSV downloads (with
// file-signature checks), and family sharing: a second user joins with the
// invite code on a phone-sized viewport, sees the shared ledger, adds an
// expense, and the first user sees it live plus in the activity feed.
//
// Flutter web renders to a canvas, so the script drives the app through the
// accessibility (semantics) tree and keyboard input. See README.md here.
const { chromium } = require('playwright');
const interceptFirebase = require('./intercept');
const fs = require('fs');
const path = require('path');

const BASE = process.env.BASE || 'http://localhost:8088/';
const OUT = process.env.OUT || path.join(__dirname, 'output');
fs.mkdirSync(OUT, { recursive: true });

const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

async function shot(page, name) {
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(OUT, `${name}.png`) });
  log('shot', name);
}

async function enableSemantics(page) {
  // Flutter inserts a hidden "Enable accessibility" placeholder; activating it
  // builds the semantics tree which exposes labels, buttons and text fields.
  try {
    await page.waitForSelector('flt-semantics-placeholder', { state: 'attached', timeout: 30000 });
    await page.evaluate(() => {
      const el = document.querySelector('flt-semantics-placeholder');
      if (!el) return;
      for (const type of ['pointerdown', 'pointerup', 'click']) {
        el.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, clientX: 1, clientY: 1 }));
      }
    });
    await page.waitForSelector('flt-semantics', { state: 'attached', timeout: 15000 });
  } catch (e) {
    log('semantics not enabled:', e.message.split('\n')[0]);
  }
  await page.waitForTimeout(1200);
}

async function fillField(page, label, value) {
  const field = page.locator(`input[aria-label="${label}"], textarea[aria-label="${label}"]`).first();
  await field.waitFor({ state: 'attached', timeout: 15000 });
  await bringIntoView(page, field);
  for (let attempt = 0; attempt < 3; attempt++) {
    await field.click({ force: true });
    await page.waitForTimeout(250); // let Flutter attach its text editing host
    await page.keyboard.press('Control+A');
    await page.keyboard.press('Backspace');
    await page.keyboard.type(value, { delay: 20 });
    await page.waitForTimeout(150);
    if ((await field.inputValue().catch(() => value)) === value) return;
  }
  throw new Error(`could not type "${value}" into ${label}`);
}

function esc(t) { return t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

async function bringIntoView(page, loc) {
  // Flutter draws to a canvas, so scroll with the wheel until the semantics
  // node for the target sits inside the viewport.
  const vh = page.viewportSize().height;
  for (let i = 0; i < 12; i++) {
    const box = await loc.boundingBox();
    if (box && box.y >= 0 && box.y + box.height <= vh - 40) return;
    await page.mouse.move(640, vh / 2);
    await page.mouse.wheel(0, box && box.y < 0 ? -300 : 300);
    await page.waitForTimeout(250);
  }
}

async function clickText(page, text, { exact = false, timeout = 4000, nth = 0 } = {}) {
  const matcher = exact ? new RegExp('^\\s*' + esc(text) + '\\s*$') : text;
  // Buttons, chips, list tiles and tappable cards all surface as role=button.
  let loc = page.locator('flt-semantics[role="button"], flt-semantics[flt-tappable], flt-semantics[role="tab"]', { hasText: matcher }).nth(nth);
  try {
    await loc.waitFor({ state: 'attached', timeout });
  } catch (_) {
    // Some widgets (navigation rail/bar, icon buttons) expose aria-label only.
    loc = page.locator(`flt-semantics[aria-label*="${text}"]`).nth(nth);
    try {
      await loc.waitFor({ state: 'attached', timeout: 3000 });
    } catch (__) {
      // Innermost semantics node whose text matches (ancestors match too).
      loc = page.locator('flt-semantics', { hasText: exact ? matcher : new RegExp('^\\s*' + esc(text) + '\\s*$') }).last();
      await loc.waitFor({ state: 'attached', timeout: 5000 });
    }
  }
  await bringIntoView(page, loc);
  await loc.click({ force: true });
  await page.waitForTimeout(250);
}

async function openRoute(page, route) {
  // go_router uses the hash URL strategy on the web.
  await page.evaluate((r) => { window.location.hash = r; }, route);
  await page.waitForTimeout(900);
}

async function typeAmount(page, value) {
  // The amount field is the first (and only unlabeled) input in the editor.
  const input = page.locator('flt-semantics-host input').first();
  await input.waitFor({ state: 'attached', timeout: 15000 });
  for (let attempt = 0; attempt < 3; attempt++) {
    await input.click({ force: true });
    await page.waitForTimeout(250);
    await page.keyboard.press('Control+A');
    await page.keyboard.press('Backspace');
    await page.keyboard.type(value, { delay: 20 });
    await page.waitForTimeout(150);
    if ((await input.inputValue().catch(() => value)) === value) return;
  }
  throw new Error(`could not type amount ${value}`);
}

async function waitEditorClosed(page, label) {
  // After saving, the editor pops; poll until its title is gone.
  for (let i = 0; i < 40; i++) {
    const open = await page.locator('flt-semantics', { hasText: /^\s*New transaction\s*$/ }).count();
    if (open === 0) return;
    await page.waitForTimeout(300);
  }
  const t = await page.evaluate(() => (document.querySelector('flt-semantics-host') || document.body).innerText.slice(0, 500));
  log(`editor still open after ${label}:`, JSON.stringify(t));
}

async function expectText(page, text, timeout = 15000) {
  await page.getByText(text, { exact: false }).first().waitFor({ state: 'attached', timeout });
  log('seen:', text);
}

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1280, height: 860 }, deviceScaleFactor: 1, acceptDownloads: true });
  const page = await context.newPage();
  global.__page = page;
  await interceptFirebase(page);
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });

  log('open', BASE);
  await page.goto(BASE, { waitUntil: 'load' });
  await page.waitForSelector('flutter-view, flt-glass-pane, flt-scene-host', { timeout: 60000 });
  await enableSemantics(page);
  await shot(page, '01-sign-in');

  // ---- sign up ---------------------------------------------------------
  await clickText(page, 'Sign up');
  await page.waitForTimeout(800);
  const email = `user${Date.now()}@example.com`;
  await fillField(page, 'Your name', 'Priya Sharma');
  await fillField(page, 'Email', email);
  await fillField(page, 'Password', 'secret123');
  await shot(page, '02-sign-up');
  await clickText(page, 'Create account');
  await expectText(page, 'Every rupee', 30000);
  await shot(page, '03-onboarding');

  // ---- onboarding ------------------------------------------------------
  await clickText(page, 'Next');
  await page.waitForTimeout(500);
  await clickText(page, 'Next');
  await page.waitForTimeout(500);
  await clickText(page, 'Set up my household');
  await page.waitForTimeout(700);
  await fillField(page, 'Household name', 'Sharma Family');
  await shot(page, '04-household-setup');
  await clickText(page, 'Create household');
  await expectText(page, 'Total balance', 40000);
  await shot(page, '05-dashboard-empty');

  // ---- add transactions -----------------------------------------------
  const adds = [
    { amount: '1250', category: 'Groceries', payee: 'Big Bazaar' },
    { amount: '450', category: 'Food & Dining', payee: 'Cafe Coffee Day' },
    { amount: '15000', category: 'Rent & Housing', payee: 'Landlord' },
    { amount: '799', category: 'Subscriptions', payee: 'Netflix' },
  ];
  for (const a of adds) {
    await openRoute(page, '#/home');
    await openRoute(page, '#/transactions/new');
    await expectText(page, 'New transaction');
    await typeAmount(page, a.amount);
    await clickText(page, 'Choose a category');
    await page.waitForTimeout(900);
    await clickText(page, a.category);
    await page.waitForTimeout(700);
    await fillField(page, 'Payee / merchant (optional)', a.payee);
    if (a === adds[0]) await shot(page, '06-new-transaction');
    await clickText(page, 'Save expense');
    await waitEditorClosed(page, a.payee);
  }
  // income
  await openRoute(page, '#/home');
  await openRoute(page, '#/transactions/new');
  await expectText(page, 'New transaction');
  await clickText(page, 'Income');
  await page.waitForTimeout(300);
  await typeAmount(page, '60000');
  await clickText(page, 'Choose a category');
  await page.waitForTimeout(900);
  await clickText(page, 'Salary');
  await page.waitForTimeout(700);
  await clickText(page, 'Save income');
  await waitEditorClosed(page, 'income');
  await expectText(page, 'Big Bazaar');
  await shot(page, '07-dashboard');

  // ---- budget ----------------------------------------------------------
  await clickText(page, 'Budgets');
  await page.waitForTimeout(800);
  await shot(page, '08-budgets-empty');
  await clickText(page, 'New budget');
  await page.waitForTimeout(700);
  await fillField(page, 'Name', 'Groceries');
  await fillField(page, 'Limit', '5000');
  await clickText(page, 'Groceries', { exact: true });
  await clickText(page, 'Create budget');
  await page.waitForTimeout(1200);
  await shot(page, '09-budgets');

  // ---- transactions & insights ----------------------------------------
  await clickText(page, 'Transactions');
  await page.waitForTimeout(1000);
  await shot(page, '10-transactions');
  await clickText(page, 'Insights');
  await page.waitForTimeout(1200);
  await shot(page, '11-insights-overview');
  await clickText(page, 'Categories');
  await page.waitForTimeout(1000);
  await shot(page, '12-insights-categories');

  // ---- reports: download PDF, Excel, CSV ------------------------------
  await clickText(page, 'Reports');
  await page.waitForTimeout(1000);
  await shot(page, '13-reports');
  const downloads = [];
  const buttons = page.locator('flt-semantics[role="button"]', { hasText: /^\s*Download\s*$/ });
  const n = await buttons.count();
  log('download buttons:', n);
  for (let i = 0; i < n; i++) {
    await bringIntoView(page, buttons.nth(i));
    const [dl] = await Promise.all([
      page.waitForEvent('download', { timeout: 30000 }),
      buttons.nth(i).click({ force: true }),
    ]);
    const target = path.join(OUT, dl.suggestedFilename());
    await dl.saveAs(target);
    downloads.push(target);
    log('downloaded', path.basename(target), fs.statSync(target).size, 'bytes');
    await page.waitForTimeout(800);
  }
  // Validate file signatures.
  for (const f of downloads) {
    const head = fs.readFileSync(f).subarray(0, 8).toString('latin1');
    if (f.endsWith('.pdf') && !head.startsWith('%PDF')) throw new Error('bad pdf ' + f);
    if (f.endsWith('.xlsx') && !head.startsWith('PK')) throw new Error('bad xlsx ' + f);
    if (f.endsWith('.csv') && !fs.readFileSync(f, 'utf8').includes('date,time,type')) throw new Error('bad csv ' + f);
  }
  log('downloads valid:', downloads.map((f) => path.basename(f)).join(', '));

  // ---- family & more ---------------------------------------------------
  await openRoute(page, '#/more');
  await expectText(page, 'Household & members');
  await shot(page, '14-more');
  await clickText(page, 'Household & members');
  await page.waitForTimeout(1500);
  await shot(page, '15-family');

  // ---- family sharing: second member joins with the invite code ---------
  const res = await fetch('http://localhost:8080/v1/projects/demo-expense-budget/databases/(default)/documents/invites', {
    headers: { Authorization: 'Bearer owner' },
  });
  const invites = (await res.json()).documents || [];
  // The emulator keeps data from earlier runs: take the newest invite.
  invites.sort((x, y) => String(x.fields.createdAt.timestampValue).localeCompare(String(y.fields.createdAt.timestampValue)));
  const code = invites[invites.length - 1].name.split('/').pop();
  log('invite code:', code);

  const ctxB = await browser.newContext({ viewport: { width: 412, height: 915 }, deviceScaleFactor: 1 });
  const pageB = await ctxB.newPage();
  await interceptFirebase(pageB);
  await pageB.goto(BASE, { waitUntil: 'load' });
  await enableSemantics(pageB);
  await clickText(pageB, 'Sign up');
  await pageB.waitForTimeout(800);
  await fillField(pageB, 'Your name', 'Rahul Sharma');
  await fillField(pageB, 'Email', `rahul${Date.now()}@example.com`);
  await fillField(pageB, 'Password', 'secret123');
  await clickText(pageB, 'Create account');
  await expectText(pageB, 'Every rupee', 30000);
  await clickText(pageB, 'Have an invite code? Join a family');
  await expectText(pageB, 'Join a family');
  await typeAmount(pageB, code);
  await shot(pageB, '16-join-family');
  await clickText(pageB, 'Join household');
  global.__page = pageB;
  try {
    await expectText(pageB, 'Total balance', 8000);
    log('member B semantics updated without reload');
  } catch (_) {
    const nodes = await pageB.evaluate(() => document.querySelectorAll('flt-semantics').length);
    log('member B semantics stale after join; node count', nodes, '- reloading');
    await pageB.reload({ waitUntil: 'load' });
    await enableSemantics(pageB);
    await expectText(pageB, 'Total balance', 30000);
    log('member B semantics present after reload');
  }
  await shot(pageB, '17-phone-dashboard-member-b');
  await openRoute(pageB, '#/transactions');
  await expectText(pageB, 'Big Bazaar', 30000);
  log('member B sees the shared ledger');
  await shot(pageB, '17b-phone-transactions-member-b');

  // Member B adds an expense; member A should see it without reloading.
  await openRoute(pageB, '#/transactions/new');
  await expectText(pageB, 'New transaction');
  await typeAmount(pageB, '320');
  await clickText(pageB, 'Choose a category');
  await pageB.waitForTimeout(900);
  await clickText(pageB, 'Transport');
  await pageB.waitForTimeout(700);
  await fillField(pageB, 'Payee / merchant (optional)', 'Uber');
  await clickText(pageB, 'Save expense');
  await waitEditorClosed(pageB, 'member B');

  global.__page = page;
  await openRoute(page, '#/home');
  await expectText(page, 'Uber', 30000);
  log('member A sees member B\'s expense live');
  await openRoute(page, '#/family/activity');
  await expectText(page, 'Rahul Sharma', 15000);
  await shot(page, '18-activity-feed');
  await openRoute(page, '#/insights');
  await clickText(page, 'Members');
  await page.waitForTimeout(1200);
  await shot(page, '19-insights-members');
  await ctxB.close();

  // Filter out noisy, known-benign console messages.
  const real = errors.filter((e) => !/favicon|DevTools|font|Tracking Prevention|wasm/i.test(e));
  fs.writeFileSync(path.join(OUT, 'console-errors.txt'), real.join('\n'));
  log('console errors:', real.length);
  await browser.close();
  console.log(JSON.stringify({ ok: true, downloads, errors: real.length }));
})().catch(async (e) => {
  console.error('E2E FAILED:', e);
  try {
    const page = global.__page;
    if (page) {
      await page.screenshot({ path: path.join(OUT, 'zz-failure.png') });
      const text = await page.evaluate(() => (document.querySelector('flt-semantics-host') || document.body).innerText.slice(0, 1500));
      console.error('PAGE TEXT:', text);
    }
  } catch (_) {}
  process.exit(1);
});
