import { rtos, states, getStateSlug } from '@/data/rtos'
import { guides } from '@/data/guides'

const SITE_URL = 'https://www.rtolookup.site'

export default function sitemap() {
  const now = new Date()

  const staticRoutes = [
    { url: SITE_URL, lastModified: now, changeFrequency: 'daily', priority: 1.0 },
    { url: `${SITE_URL}/guides`, lastModified: now, changeFrequency: 'weekly', priority: 0.9 },
  ]

  const rtoRoutes = rtos.map(r => ({
    url: `${SITE_URL}/rto/${r.code.toLowerCase()}`,
    lastModified: now,
    changeFrequency: 'monthly',
    priority: 0.8,
  }))

  const stateRoutes = states.map(s => ({
    url: `${SITE_URL}/state/${getStateSlug(s)}`,
    lastModified: now,
    changeFrequency: 'monthly',
    priority: 0.7,
  }))

  const guideRoutes = guides.map(g => ({
    url: `${SITE_URL}/guides/${g.slug}`,
    lastModified: now,
    changeFrequency: 'monthly',
    priority: 0.9,
  }))

  return [...staticRoutes, ...guideRoutes, ...stateRoutes, ...rtoRoutes]
}
