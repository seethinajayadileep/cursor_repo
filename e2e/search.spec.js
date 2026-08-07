import { test, expect } from '@playwright/test'

test.describe('Plate search', () => {
  test('valid code routes to RTO page', async ({ page }) => {
    await page.goto('/')
    const input = page.getByRole('textbox', { name: /enter rto code/i })
    await input.fill('KA-03')
    await input.press('Enter')
    await expect(page).toHaveURL(/\/rto\/ka-03/)
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Bengaluru')
  })

  test('lowercase + no hyphen normalises', async ({ page }) => {
    await page.goto('/')
    const input = page.getByRole('textbox', { name: /enter rto code/i })
    await input.fill('mh1')
    await input.press('Enter')
    // mh1 -> MH-01 padded
    await expect(page).toHaveURL(/\/rto\/mh-01/)
  })

  test('invalid input shows error, no navigation', async ({ page }) => {
    await page.goto('/')
    const input = page.getByRole('textbox', { name: /enter rto code/i })
    await input.fill('hello world')
    await input.press('Enter')
    await expect(page.getByRole('alert')).toContainText(/valid RTO code/i)
    await expect(page).toHaveURL('/')
  })

  test('empty submit does nothing', async ({ page }) => {
    await page.goto('/')
    const input = page.getByRole('textbox', { name: /enter rto code/i })
    await input.press('Enter')
    await expect(page).toHaveURL('/')
  })
})
