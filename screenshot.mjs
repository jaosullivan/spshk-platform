/**
 * Usage:
 *   node screenshot.mjs                          → http://localhost:3000, no label
 *   node screenshot.mjs http://localhost:3000    → explicit URL
 *   node screenshot.mjs http://localhost:3000 hero → saves as screenshot-N-hero.png
 *
 * Screenshots saved to ./temporary screenshots/screenshot-N[-label].png
 * Auto-increments; never overwrites existing files.
 */
import puppeteer from 'puppeteer';
import { existsSync, mkdirSync, readdirSync } from 'fs';
import { join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const [,, url = 'http://localhost:3000', label = ''] = process.argv;

const dir = join(__dirname, 'temporary screenshots');
if (!existsSync(dir)) mkdirSync(dir, { recursive: true });

const n   = readdirSync(dir).filter(f => /^screenshot-\d/.test(f)).length + 1;
const name = label ? `screenshot-${n}-${label}.png` : `screenshot-${n}.png`;
const out  = join(dir, name);

const browser = await puppeteer.launch({
  headless: 'new',
  args: ['--no-sandbox', '--disable-setuid-sandbox'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 800 });
await page.goto(url, { waitUntil: 'networkidle0' });
await page.screenshot({ path: out, fullPage: true });
await browser.close();

console.log(`Saved: ${out}`);
