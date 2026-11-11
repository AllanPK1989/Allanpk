// Renders public/icon.svg to the PNG sizes the PWA manifest needs (uses the pre-installed Chromium).
import { createRequire } from "node:module";
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

// Playwright is installed globally in the cloud environment; resolve it the CommonJS way.
const { chromium } = createRequire(import.meta.url)("playwright");

const root = new URL("..", import.meta.url).pathname;
const svg = readFileSync(join(root, "public/icon.svg"), "utf8");
const browser = await chromium.launch();
for (const size of [192, 512]) {
  const page = await browser.newPage({ viewport: { width: size, height: size }, deviceScaleFactor: 1 });
  await page.setContent(`<html><body style="margin:0;background:transparent">${svg.replace(/width="128" height="128"/, `width="${size}" height="${size}"`)}</body></html>`);
  const png = await page.screenshot({ omitBackground: true, clip: { x: 0, y: 0, width: size, height: size } });
  writeFileSync(join(root, `public/icon-${size}.png`), png);
  await page.close();
  console.log(`public/icon-${size}.png`);
}
await browser.close();
