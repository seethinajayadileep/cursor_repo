export default function manifest() {
  return {
    name: 'RTOLookup — Decode Indian Vehicle Number Plates',
    short_name: 'RTOLookup',
    description: 'Decode any Indian RTO code and number plate instantly. Guides for RC transfer, owner check, and more.',
    start_url: '/',
    display: 'standalone',
    background_color: '#0E1117',
    theme_color: '#0E1117',
    categories: ['utilities', 'reference', 'automotive'],
    lang: 'en-IN',
    icons: [
      { src: '/icon.svg', sizes: 'any', type: 'image/svg+xml' },
    ],
  }
}
