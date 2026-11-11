import { test, expect } from '@playwright/test';

test('rejects requests without credentials', async ({request}) => {
  const response = await request.get('/');
  expect(response.status()).toBe(401);
  expect(await response.text()).not.toContain('Categoria X');
});

test.describe('authorized synthetic demo', () => {
  test.use({httpCredentials:{username:'dashboard',password:'synthetic-dashboard-token-123456'}});
  test('shows operation and filters aggregates', async ({page}) => {
    await page.goto('/');
    await expect(page.getByRole('heading',{name:'Saúde da sincronização'})).toBeVisible();
    await expect(page.getByText('DADOS DEMO')).toBeVisible();
    await page.getByLabel('Categoria').selectOption('Categoria Y');
    await page.getByRole('button',{name:'Filtrar'}).click();
    await expect(page.locator('tbody tr')).toHaveCount(1);
    await expect(page.locator('tbody')).toContainText('Categoria Y');
    await expect(page.locator('tbody')).not.toContainText('Categoria X');
    await page.screenshot({path:'test-results/dashboard-desktop.png',fullPage:true});
  });
  test('mobile navigation and table remain usable', async ({page}) => {
    await page.setViewportSize({width:390,height:844});
    await page.goto('/');
    await expect(page.getByRole('heading',{name:'Uma visão além dos dados'})).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({path:'test-results/dashboard-mobile.png',fullPage:true});
  });
});
