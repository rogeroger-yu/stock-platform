/**
 * E2E 测试脚本 — 使用 Playwright 测试前端所有页面
 * 测试方案: 每个页面加载 → 截图 → 检查控制台错误 → 检查API调用
 */
import { chromium } from 'playwright';
import { writeFileSync, mkdirSync } from 'fs';

const BASE_URL = 'http://47.97.26.218/';
const SCREENSHOTS_DIR = './e2e-screenshots';

mkdirSync(SCREENSHOTS_DIR, { recursive: true });

const pages = [
  { name: 'Home', path: '/', checks: ['股票策略研发平台'] },
  { name: 'StrategyList', path: '/strategies', checks: ['策略', 'momentum'] },
  { name: 'StrategyDetail', path: '/strategies/1', checks: ['策略详情', '回测'] },
  { name: 'BatchRun', path: '/batch', checks: ['批量', '回测'] },
  { name: 'Compare', path: '/compare', checks: ['对比'] },
  { name: 'PaperTrade', path: '/paper', checks: ['模拟交易', '账户'] },
  { name: 'DataManagement', path: '/data', checks: ['数据', '股票'] },
];

const results = [];

async function runTests() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
  });

  for (const pageDef of pages) {
    const page = await context.newPage();
    const consoleErrors = [];
    const networkErrors = [];
    const apiCalls = [];

    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    page.on('requestfailed', request => {
      networkErrors.push(`${request.method()} ${request.url()}: ${request.failure()?.errorText}`);
    });

    page.on('response', response => {
      if (response.url().includes('/api/')) {
        apiCalls.push({
          url: response.url().replace(/.*\/api/, '/api'),
          status: response.status(),
        });
      }
    });

    const url = `${BASE_URL}${pageDef.path.startsWith('/') ? pageDef.path.slice(1) : pageDef.path}`;
    console.log(`\n=== Testing ${pageDef.name}: ${url} ===`);

    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
      await page.waitForTimeout(3000);

      // 截图
      await page.screenshot({ path: `${SCREENSHOTS_DIR}/${pageDef.name}.png`, fullPage: true });
      console.log(`  Screenshot saved`);

      // 检查页面内容
      const bodyText = await page.textContent('body');
      for (const check of pageDef.checks) {
        const found = bodyText?.includes(check);
        console.log(`  Content "${check}": ${found ? 'FOUND' : 'MISSING'}`);
      }

      // 检查页面是否为空白（React渲染失败）
      const hasContent = bodyText && bodyText.trim().length > 100;
      console.log(`  Has content: ${hasContent ? 'YES' : 'NO (blank page!)'}`);

      // 检查控制台错误
      if (consoleErrors.length > 0) {
        console.log(`  Console errors (${consoleErrors.length}):`);
        consoleErrors.forEach(e => console.log(`    - ${e.slice(0, 120)}`));
      }

      // 检查API调用
      if (apiCalls.length > 0) {
        console.log(`  API calls (${apiCalls.length}):`);
        apiCalls.forEach(a => console.log(`    ${a.status} ${a.url}`));
      }

      // 检查网络错误
      if (networkErrors.length > 0) {
        console.log(`  Network errors (${networkErrors.length}):`);
        networkErrors.forEach(e => console.log(`    - ${e.slice(0, 120)}`));
      }

      results.push({
        page: pageDef.name,
        url,
        ok: hasContent && consoleErrors.length === 0,
        hasContent,
        consoleErrors: consoleErrors.length,
        networkErrors: networkErrors.length,
        apiCalls: apiCalls.length,
        errors: [...consoleErrors, ...networkErrors],
      });
    } catch (e) {
      console.log(`  FAILED: ${e.message}`);
      results.push({
        page: pageDef.name,
        url,
        ok: false,
        error: e.message,
      });
    }

    await page.close();
  }

  await browser.close();

  // Summary
  console.log('\n\n=== SUMMARY ===');
  let allOk = true;
  for (const r of results) {
    const status = r.ok ? 'PASS' : 'FAIL';
    console.log(`  ${status} ${r.page}: content=${r.hasContent} errors=${r.consoleErrors || 0} api=${r.apiCalls || 0}`);
    if (!r.ok) allOk = false;
  }

  // Save results
  writeFileSync(`${SCREENSHOTS_DIR}/results.json`, JSON.stringify(results, null, 2));
  console.log(`\nResults saved to ${SCREENSHOTS_DIR}/results.json`);

  process.exit(allOk ? 0 : 1);
}

runTests().catch(e => {
  console.error('Test runner failed:', e);
  process.exit(1);
});
