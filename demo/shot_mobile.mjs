import pw from '/opt/node22/lib/node_modules/playwright/index.js';
import { fileURLToPath } from 'url';
import path from 'path';
const { chromium } = pw;

const here = path.dirname(fileURLToPath(import.meta.url));
const file = 'file://' + path.resolve(here, 'index.html');
const browser = await chromium.launch();
// iPhone 14-ish portrait
const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true });
await page.goto(file);
await page.waitForTimeout(500);

async function shot(name, fn) {
  if (fn) { await page.evaluate(fn); await page.waitForTimeout(300); }
  await page.screenshot({ path: `m_${name}.png`, fullPage: false });
  console.log('wrote m_' + name + '.png');
}

await shot('dashboard');
await shot('inbox_list', () => window.go('inbox'));
await shot('inbox_detail', () => window.pick(2));
await shot('followups', () => window.go('followups'));
await shot('settings', () => window.go('settings'));

await browser.close();
