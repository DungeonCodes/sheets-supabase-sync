import { test, expect } from '@playwright/test';

test('fixture aggregates appear after authentication', async ({browser}) => {
  const anonymous = await browser.newPage();
  const denied = await anonymous.goto('/');
  expect(denied?.status()).toBe(401);
  await anonymous.close();
  const context = await browser.newContext({httpCredentials:{username:'dashboard',password:process.env.DASHBOARD_ACCESS_TOKEN!}});
  const page = await context.newPage();
  await page.goto('/');
  await expect(page.getByText('POSTGRES LOCAL')).toBeVisible();
  await expect(page.locator('tbody')).toContainText('Categoria X');
  await expect(page.locator('tbody')).toContainText('Categoria Y');
  await page.getByLabel('Categoria').selectOption('Categoria X');
  await page.getByRole('button',{name:'Filtrar'}).click();
  await expect(page.locator('tbody tr')).toHaveCount(1);
  await context.close();
});
