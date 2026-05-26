/**
 * E2E Test Script for Stock Strategy Platform
 * Tests all pages, finds errors, and reports issues.
 */

import { chromium } from 'playwright';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const BASE_URL = 'http://localhost:5174';

const PAGES = [
  { name: '首页', path: '/' },
  { name: '策略列表', path: '/strategies' },
  { name: '策略详情', path: '/strategies/1' },
  { name: '对比', path: '/compare' },
  { name: '批量排名', path: '/batch' },
  { name: '模拟交易', path: '/paper' },
  { name: '数据管理', path: '/data' },
  { name: '回测详情', path: '/backtest/1' },
];

async function startViteServer() {
  // Check if serve is already running
  try {
    const resp = await fetch('http://localhost:5174/');
    if (resp.ok) {
      console.log('  (Serve already running)');
      return null;
    }
  } catch {}

  return new Promise((resolve, reject) => {
    const proc = spawn('node', ['node_modules/.bin/serve', '-s', 'dist', '-l', '5174'], {
      cwd: __dirname,
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    
    let started = false;
    proc.stdout.on('data', (data) => {
      const text = data.toString();
      if (text.includes('Accepting') && !started) {
        started = true;
        setTimeout(() => resolve(proc), 1000);
      }
    });
    proc.stderr.on('data', (data) => {
      console.error('serve stderr:', data.toString());
    });
    
    setTimeout(() => {
      if (!started) {
        proc.kill();
        reject(new Error('Serve start timeout'));
      }
    }, 15000);
  });
}

async function testPage(browser, pagePath, pageName) {
  const context = await browser.newContext();
  const page = await context.newPage();
  
  const errors = [];
  const consoleErrors = [];
  const networkErrors = [];
  
  // Collect console errors
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });
  
  // Collect page errors (uncaught exceptions)
  page.on('pageerror', (err) => {
    errors.push(err.message);
  });
  
  // Collect network failures
  page.on('requestfailed', (req) => {
    if (!req.url().includes('/api/')) { // Ignore API errors (backend may not be running)
      networkErrors.push(`${req.method()} ${req.url()}: ${req.failure()?.errorText || 'failed'}`);
    }
  });
  
  let status = 'PASS';
  let loadTime = 0;
  const startTime = Date.now();
  
  try {
    const response = await page.goto(`${BASE_URL}${pagePath}`, {
      waitUntil: 'domcontentloaded',
      timeout: 15000,
    });
    loadTime = Date.now() - startTime;
    
    if (response && response.status() >= 400) {
      status = 'FAIL';
      errors.push(`HTTP ${response.status()}`);
    }
    
    // Wait a bit for React to render
    await page.waitForTimeout(2000);
    
    // Check if page has content (not blank)
    const bodyText = await page.textContent('body');
    if (!bodyText || bodyText.trim().length < 10) {
      status = 'FAIL';
      errors.push('Page appears blank (no content)');
    }
    
    // Check for React error boundary or error messages
    const hasErrorBoundary = await page.locator('text=Something went wrong').count().catch(() => 0);
    if (hasErrorBoundary > 0) {
      status = 'FAIL';
      errors.push('React error boundary triggered');
    }
    
    // Check for antd error messages
    const antdErrors = await page.locator('.ant-message-error').count().catch(() => 0);
    if (antdErrors > 0) {
      const errorTexts = await page.locator('.ant-message-error').allTextContents().catch(() => []);
      errors.push(`antd errors: ${errorTexts.join(', ')}`);
    }
    
  } catch (err) {
    status = 'FAIL';
    errors.push(err.message);
    loadTime = Date.now() - startTime;
  }
  
  await context.close();
  
  return {
    name: pageName,
    path: pagePath,
    status,
    loadTime,
    errors,
    consoleErrors: consoleErrors.slice(0, 5),
    networkErrors: networkErrors.slice(0, 5),
  };
}

async function main() {
  console.log('🚀 Starting E2E tests for Stock Strategy Platform\n');
  
  // Start vite server
  console.log('📦 Starting Vite dev server...');
  let viteProc;
  try {
    viteProc = await startViteServer();
    if (viteProc) console.log('✅ Vite server running\n');
  } catch (err) {
    console.error('❌ Failed to start Vite:', err.message);
    process.exit(1);
  }
  
  // Launch browser
  const browser = await chromium.launch({ headless: true });
  
  const results = [];
  
  for (const pg of PAGES) {
    process.stdout.write(`  Testing ${pg.name} (${pg.path})... `);
    const result = await testPage(browser, pg.path, pg.name);
    results.push(result);
    
    if (result.status === 'PASS') {
      console.log(`✅ ${result.loadTime}ms`);
    } else {
      console.log(`❌ ${result.loadTime}ms`);
      for (const err of result.errors) {
        console.log(`    ERROR: ${err}`);
      }
    }
    if (result.consoleErrors.length > 0) {
      for (const err of result.consoleErrors) {
        console.log(`    CONSOLE: ${err.substring(0, 120)}`);
      }
    }
    if (result.networkErrors.length > 0) {
      for (const err of result.networkErrors) {
        console.log(`    NETWORK: ${err}`);
      }
    }
  }
  
  await browser.close();
  if (viteProc) viteProc.kill();
  
  // Summary
  const passed = results.filter(r => r.status === 'PASS').length;
  const failed = results.filter(r => r.status === 'FAIL').length;
  
  console.log(`\n${'='.repeat(60)}`);
  console.log(`📊 Results: ${passed} passed, ${failed} failed, ${results.length} total`);
  
  if (failed > 0) {
    console.log('\n❌ Failed pages:');
    for (const r of results.filter(r => r.status === 'FAIL')) {
      console.log(`  - ${r.name} (${r.path}): ${r.errors.join(', ')}`);
    }
  }
  
  console.log(`${'='.repeat(60)}\n`);
  
  // Write results to JSON for further processing
  const fs = await import('fs');
  fs.writeFileSync('/tmp/e2e-results.json', JSON.stringify(results, null, 2));
  console.log('📝 Results saved to /tmp/e2e-results.json');
  
  process.exit(failed > 0 ? 1 : 0);
}

main().catch((err) => {
  console.error('Fatal:', err);
  process.exit(1);
});
