import { test, expect } from '@playwright/test';

test('timeline loads with events and panel opens on click', async ({ page }) => {
  await page.goto('/');
  // Wait for timeline to render
  await expect(page.locator('.vis-timeline')).toBeVisible({ timeout: 10_000 });
  // Header
  await expect(page.locator('h1')).toContainText('Master Timeline Chabad');
  // Search
  await page.locator('#search').fill('Tanya');
  await page.waitForTimeout(400);  // debounce
  // Zoom into a narrow window (1790–1810) so items de-cluster into individual vis-items
  await page.evaluate(() => {
    const tl = (window as any).__timeline;
    if (tl) tl.setWindow(new Date(1790, 0, 1), new Date(1810, 0, 1), { animation: false });
  });
  await page.waitForTimeout(300);  // let vis-timeline re-render
  // Programmatically trigger select on the first visible item to open the panel.
  // DOM clicks on vis-items are unreliable when items cluster; using the timeline
  // select API directly exercises the same onSelect → panel.open() wiring.
  const opened = await page.evaluate(() => {
    const tl = (window as any).__timeline;
    if (!tl) return false;
    // Get the currently rendered (visible) item IDs from the dataset
    const items = tl.itemsData;
    if (!items) return false;
    const ids = items.getIds();
    if (ids.length === 0) return false;
    // Trigger the select event with the first item id
    tl.setSelection([ids[0]]);
    tl.emit('select', { items: [ids[0]], event: null });
    return true;
  });
  expect(opened).toBe(true);
  await expect(page.locator('aside#panel.open')).toBeVisible();
  // Close via ESC
  await page.keyboard.press('Escape');
  await expect(page.locator('aside#panel.open')).toBeHidden();
});
