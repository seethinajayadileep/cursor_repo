// Standalone accessibility audit: Chrome (CDP) + axe-core, no Playwright browser download.
import { readFileSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { setTimeout as sleep } from 'node:timers/promises'

const BASE = 'http://localhost:3000'
const PAGES = ['/', '/rto/mh-01', '/state/maharashtra', '/guides', '/guides/rc-transfer', '/rto/zz-99']
const axeSource = readFileSync('./node_modules/axe-core/axe.min.js', 'utf8')

// Launch headless Chrome with remote debugging
const chrome = spawn('google-chrome-stable', [
  '--headless', '--disable-gpu', '--no-sandbox',
  '--remote-debugging-port=9222', '--remote-allow-origins=*',
  'about:blank',
], { stdio: 'ignore' })

await sleep(2500)

async function cdpTargets() {
  const res = await fetch('http://localhost:9222/json')
  return res.json()
}

async function auditPage(path) {
  // New tab
  const newTab = await (await fetch('http://localhost:9222/json/new?about:blank')).json().catch(async () => {
    return (await (await fetch('http://localhost:9222/json/new', { method: 'PUT' })).json())
  })
  const ws = newTab.webSocketDebuggerUrl
  const { default: WebSocket } = await import('ws').catch(() => ({ default: null }))
  if (!WebSocket) throw new Error('ws module missing')

  const sock = new WebSocket(ws)
  let id = 0
  const pending = new Map()
  const send = (method, params = {}) => new Promise((resolve) => {
    const mid = ++id
    pending.set(mid, resolve)
    sock.send(JSON.stringify({ id: mid, method, params }))
  })

  await new Promise(r => sock.on('open', r))
  sock.on('message', (data) => {
    const msg = JSON.parse(data)
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg.result); pending.delete(msg.id) }
  })

  await send('Page.enable')
  await send('Runtime.enable')
  const THEME = process.env.THEME || 'dark'
  await send('Page.addScriptToEvaluateOnNewDocument', { source: `try{localStorage.setItem('theme','${THEME}')}catch(e){}` })
  await send('Page.navigate', { url: BASE + path })
  await sleep(1800)

  await send('Runtime.evaluate', { expression: axeSource })
  const res = await send('Runtime.evaluate', {
    expression: `axe.run(document, { runOnly: ['wcag2a','wcag2aa','wcag21a','wcag21aa'] }).then(r => JSON.stringify({violations: r.violations}))`,
    awaitPromise: true,
    returnByValue: true,
  })

  sock.close()
  const out = JSON.parse(res.result.value)
  return out.violations
}

let totalViolations = 0
for (const path of PAGES) {
  try {
    const violations = await auditPage(path)
    const serious = violations.filter(v => ['serious', 'critical'].includes(v.impact))
    totalViolations += serious.length
    if (violations.length === 0) {
      console.log(`✓ ${path} — 0 violations`)
    } else {
      console.log(`${serious.length ? '✗' : '⚠'} ${path} — ${violations.length} issue(s):`)
      for (const v of violations) {
        console.log(`   [${v.impact}] ${v.id}: ${v.help} (${v.nodes.length} node(s))`)
        console.log(`      ${v.nodes[0]?.target?.join(' ')}`)
      }
    }
  } catch (e) {
    console.log(`! ${path} — audit error: ${e.message}`)
  }
}

chrome.kill()
console.log(`\n=== ${totalViolations} serious/critical violation(s) total ===`)
process.exit(totalViolations > 0 ? 1 : 0)
