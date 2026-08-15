#!/usr/bin/env node
/**
 * The demo is a single self-contained file, but its look has to stay identical
 * to the real app. This copies frontend/src/styles.css into the marked <style>
 * block in demo/index.html.
 *
 *   node demo/sync-styles.mjs          write the demo
 *   node demo/sync-styles.mjs --check  fail if the demo is out of date (CI)
 */
import { readFileSync, writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import path from 'path';

const here = path.dirname(fileURLToPath(import.meta.url));
const cssPath = path.resolve(here, '../frontend/src/styles.css');
const htmlPath = path.resolve(here, 'index.html');

const START = '/* RG-STYLES-START';
const END = '/* RG-STYLES-END */';

const css = readFileSync(cssPath, 'utf8').trim();
const html = readFileSync(htmlPath, 'utf8');

const startAt = html.indexOf(START);
const endAt = html.indexOf(END);
if (startAt === -1 || endAt === -1) {
  console.error('demo/index.html is missing its RG-STYLES markers.');
  process.exit(1);
}

const header = `${START} — generated from frontend/src/styles.css by demo/sync-styles.mjs. Do not edit here. */`;
const next = html.slice(0, startAt) + header + '\n' + css + '\n' + html.slice(endAt);

if (process.argv.includes('--check')) {
  if (next !== html) {
    console.error('demo/index.html styles are stale. Run: node demo/sync-styles.mjs');
    process.exit(1);
  }
  console.log('demo styles are in sync.');
} else {
  writeFileSync(htmlPath, next);
  console.log(`synced ${css.length.toLocaleString()} bytes of CSS into demo/index.html`);
}
