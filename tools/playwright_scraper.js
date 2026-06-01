#!/usr/bin/env node
/* Playwright 轻量抓取 — 替代 Firecrawl 的 browser engine */
const { chromium } = require('playwright');

async function scrape(url) {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
    const text = await page.evaluate(() => {
      document.querySelectorAll('script, style, nav, footer, header, aside, iframe, noscript')
        .forEach(el => el.remove());
      return document.body?.innerText || document.documentElement.innerText || '';
    });
    return text.replace(/\n{3,}/g, '\n\n').trim().slice(0, 5000);
  } finally {
    await browser.close();
  }
}

if (require.main === module) {
  const url = process.argv[2];
  if (!url) { console.error('Usage: node playwright_scraper.js <URL>'); process.exit(1); }
  scrape(url).then(text => console.log(text)).catch(e => { console.error('Error:', e.message); process.exit(1); });
}

module.exports = { scrape };
