/**
 * Phone-sized screenshots of the demo.
 *
 *   npx playwright install chromium     # once
 *   node demo/shot_mobile.mjs
 */
import { fileURLToPath } from 'url';
import path from 'path';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = require('playwright'));
} catch {
  console.error('playwright not found. Install it first:\n  npm i -D playwright && npx playwright install chromium');
  process.exit(1);
}

const here = path.dirname(fileURLToPath(import.meta.url));
const file = 'file://' + path.resolve(here, 'index.html');

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true });

let n = 0;
async function shot(name, hash, after) {
  // A hash-only change does not reload, so bust it with a query param.
  await page.goto(`${file}?i=${n++}` + (hash ? '#' + hash : ''));
  await page.waitForTimeout(600);
  if (after) { await page.evaluate(after); await page.waitForTimeout(350); }
  const out = path.join(here, `m_${name}.png`);
  await page.screenshot({ path: out });
  console.log('wrote ' + path.basename(out));
}

await shot('dashboard', 'tab=dashboard&theme=light');
await shot('inbox_list', 'tab=inbox&theme=light');
await shot('inbox_detail', 'tab=inbox&thread=1&theme=light');
await shot('followups', 'tab=followups&theme=light');
await shot('settings', 'tab=settings&theme=dark');

await browser.close();
