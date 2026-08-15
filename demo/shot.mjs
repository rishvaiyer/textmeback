/**
 * Desktop screenshots of the demo, used for docs/preview.png.
 *
 *   npx playwright install chromium     # once
 *   node demo/shot.mjs
 *
 * Writes shot_<view>.png next to this script, in both themes.
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
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });

let n = 0;
async function shot(name, hash) {
  // A hash-only change does not reload, so bust it with a query param.
  await page.goto(`${file}?i=${n++}` + (hash ? '#' + hash : ''));
  await page.waitForTimeout(700);
  const out = path.join(here, `shot_${name}.png`);
  await page.screenshot({ path: out });
  console.log('wrote ' + path.basename(out));
}

for (const theme of ['light', 'dark']) {
  await shot(`dashboard_${theme}`, `tab=dashboard&theme=${theme}`);
  await shot(`inbox_${theme}`, `tab=inbox&thread=1&theme=${theme}`);
}
await shot('followups', 'tab=followups&theme=light');
await shot('analytics', 'tab=analytics&theme=light');
await shot('settings', 'tab=settings&theme=light');

await browser.close();
