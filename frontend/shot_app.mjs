import pw from '/opt/node22/lib/node_modules/playwright/index.js';
const { chromium } = pw;
const URL = 'http://localhost:5173';
const browser = await chromium.launch();

// Desktop
const d = await browser.newPage({ viewport: { width: 1280, height: 860 }, deviceScaleFactor: 2 });
await d.goto(URL); await d.waitForTimeout(1200);
await d.screenshot({ path: 'app_dashboard.png' });
await d.getByText('Inbox', { exact: true }).first().click(); await d.waitForTimeout(800);
// open first thread
await d.locator('.thread').first().click(); await d.waitForTimeout(700);
await d.locator('.draft-card, .btn.primary').first().waitFor({ timeout: 3000 }).catch(()=>{});
// generate a draft
const gen = d.getByRole('button', { name: /Generate draft/i });
if (await gen.count()) { await gen.first().click(); await d.waitForTimeout(900); }
await d.screenshot({ path: 'app_inbox.png' });
await d.getByText('Analytics', { exact: true }).first().click(); await d.waitForTimeout(700);
await d.screenshot({ path: 'app_analytics.png' });
await d.getByText('Settings', { exact: true }).first().click(); await d.waitForTimeout(600);
await d.screenshot({ path: 'app_settings.png' });
console.log('desktop shots done');

// Mobile
const m = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true });
await m.goto(URL); await m.waitForTimeout(1000);
await m.screenshot({ path: 'app_m_dashboard.png' });
await m.locator('.mobile-nav button').nth(1).click(); await m.waitForTimeout(700);
await m.locator('.thread').first().click(); await m.waitForTimeout(700);
await m.screenshot({ path: 'app_m_inbox_detail.png' });
console.log('mobile shots done');

await browser.close();
