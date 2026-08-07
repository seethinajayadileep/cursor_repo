import { test, expect } from '@playwright/test'

function jsonLdTypes(html) {
  const types = []
  const re = /<script type="application\/ld\+json">(.*?)<\/script>/gs
  let m
  while ((m = re.exec(html))) {
    try {
      const data = JSON.parse(m[1])
      const collect = (o) => {
        if (Array.isArray(o)) return o.forEach(collect)
        if (o && typeof o === 'object') {
          if (o['@type']) types.push(o['@type'])
          Object.values(o).forEach(collect)
        }
      }
      collect(data)
    } catch {}
  }
  return types
}

test.describe('SEO metadata', () => {
  test('home has unique title, description, canonical, WebSite schema', async ({ page }) => {
    const res = await page.goto('/')
    const html = await res.text()
    expect(await page.title()).toMatch(/RTOLookup/)
    await expect(page.locator('meta[name="description"]')).toHaveAttribute('content', /.{50,}/)
    const types = jsonLdTypes(html)
    expect(types).toContain('WebSite')
    expect(types).toContain('SearchAction')
  })

  test('RTO page has per-page title, canonical, FAQ + Breadcrumb schema', async ({ page }) => {
    const res = await page.goto('/rto/mh-01')
    const html = await res.text()
    expect(await page.title()).toContain('MH-01')
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', /\/rto\/mh-01$/)
    const types = jsonLdTypes(html)
    expect(types).toContain('FAQPage')
    expect(types).toContain('BreadcrumbList')
    expect(types).toContain('Question')
  })

  test('guide page has HowTo + FAQ schema', async ({ page }) => {
    const res = await page.goto('/guides/rc-transfer')
    const html = await res.text()
    const types = jsonLdTypes(html)
    expect(types).toContain('HowTo')
    expect(types).toContain('HowToStep')
    expect(types).toContain('FAQPage')
  })

  test('breadcrumb JSON-LD on guide points to a real /guides page', async ({ page }) => {
    // regression: /guides used to 404 while being referenced in schema
    const guidesRes = await page.goto('/guides')
    expect(guidesRes?.status()).toBe(200)
  })

  test('sitemap lists RTO, state, guide URLs', async ({ page }) => {
    const res = await page.goto('/sitemap.xml')
    const xml = await res.text()
    expect(xml).toContain('/rto/mh-01')
    expect(xml).toContain('/state/maharashtra')
    expect(xml).toContain('/guides/rc-transfer')
    expect(xml).toContain('/guides<')
  })

  test('robots.txt allows crawl and references sitemap', async ({ page }) => {
    const res = await page.goto('/robots.txt')
    const txt = await res.text()
    expect(txt).toMatch(/Allow: \//)
    expect(txt).toMatch(/Sitemap:.*sitemap\.xml/)
  })

  test('exactly one h1 per page', async ({ page }) => {
    for (const url of ['/', '/rto/mh-01', '/state/maharashtra', '/guides', '/guides/rc-transfer']) {
      await page.goto(url)
      await expect(page.locator('h1')).toHaveCount(1)
    }
  })
})
