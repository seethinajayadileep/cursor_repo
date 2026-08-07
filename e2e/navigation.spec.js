import { test, expect } from '@playwright/test'

test.describe('Core navigation', () => {
  test('home loads with hero and search', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/Decode Any Indian Vehicle Number Plate/)
    await expect(page.getByRole('heading', { level: 1 })).toContainText('number plate')
    await expect(page.getByRole('textbox', { name: /enter rto code/i })).toBeVisible()
  })

  test('header nav links resolve (no 404)', async ({ page }) => {
    await page.goto('/')
    // Guides hub — previously broken
    await page.goto('/guides')
    await expect(page.getByRole('heading', { level: 1 })).toContainText('RTO & Vehicle Guides')
  })

  test('popular RTO card navigates to detail page', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('link', { name: /MH-01.*Mumbai/i }).first().click()
    await expect(page).toHaveURL(/\/rto\/mh-01/)
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Mumbai')
  })

  test('state hub lists its RTOs', async ({ page }) => {
    await page.goto('/state/maharashtra')
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Maharashtra RTO Codes')
    await expect(page.getByRole('link', { name: /MH-04/i }).first()).toBeVisible()
  })

  test('guide page renders steps + faq', async ({ page }) => {
    await page.goto('/guides/rc-transfer')
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Transfer RC')
    await expect(page.getByText('Gather the documents')).toBeVisible()
  })
})

test.describe('404 handling', () => {
  test('unknown RTO code shows not-found', async ({ page }) => {
    const res = await page.goto('/rto/zz-99')
    expect(res?.status()).toBe(404)
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Page not found')
  })

  test('unknown state shows not-found', async ({ page }) => {
    const res = await page.goto('/state/atlantis')
    expect(res?.status()).toBe(404)
  })
})
