import type { Hook, Register, RenderElement, SessionUsage, ThemeColors } from 'claude-code'

type Api = Parameters<Hook<'session.start'>>[0]

import { makeColors } from './make-colors.js'
import { TOPICS as TOPIC_LIST } from './topics.js'

// One color per topic. The first prompt that names a topic picks it;
// /tint <topic> overrides; /tint off clears. The list lives in topics.js,
// which setup writes from the choices made in the setup wizard.
type Topic = {
  id: string
  label: string
  color: string // accent, six-digit hex
  hue: number // tint for the surfaces
  words: string[] // matched as whole words
  parent?: string // the broader topic this one is an area of
  hues?: number[] // the aurora's own hues; absent, neighbors of `hue`
  isMuted?: boolean // near-neutral surfaces
  dot?: string // the shape put in front of the chat's title
}

const TOPICS: Topic[] = TOPIC_LIST

// A chat with no topic yet: charcoal surfaces under a northern-lights aurora.
const DEFAULT: Topic = {
  id: 'default',
  label: 'No topic',
  color: '#3fa99b',
  hue: 215,
  words: [],
  hues: [165, 140, 265, 200],
  isMuted: true,
}

const hex = (h: number, s: number, l: number): string => {
  const a = (s / 100) * Math.min(l / 100, 1 - l / 100)
  const f = (n: number) => {
    const k = (n + h / 30) % 12
    const c = l / 100 - a * Math.max(-1, Math.min(k - 3, 9 - k, 1))
    return Math.round(c * 255).toString(16).padStart(2, '0')
  }
  return `#${f(0)}${f(8)}${f(4)}`
}

const themeFor = (t: Topic): { colors: ThemeColors; unpainted?: string } => {
  const m = t.isMuted === true ? 0.4 : 1
  const { theme, problems } = makeColors({
    label: `Tint: ${t.label}`,
    id: `tint-${t.id}`,
    roles: { accent: t.color },
    dark: {
      gray: {
        anchors: {
          'surface-0': hex(t.hue, 28 * m, 8),
          'surface-1': hex(t.hue, 26 * m, 11),
          'surface-2': hex(t.hue, 24 * m, 14),
          'surface-3': hex(t.hue, 22 * m, 16),
          'text-primary': hex(t.hue, 30 * m, 93),
          'text-secondary': hex(t.hue, 18 * m, 80),
          'text-muted': hex(t.hue, 14 * m, 68),
        },
      },
    },
    light: {
      gray: {
        anchors: {
          'surface-0': hex(t.hue, 45 * m, 89),
          'surface-1': hex(t.hue, 50 * m, 93),
          'surface-2': hex(t.hue, 55 * m, 97),
          'text-primary': hex(t.hue, 35 * m, 12),
          'text-secondary': hex(t.hue, 25 * m, 26),
          'text-muted': hex(t.hue, 18 * m, 36),
        },
      },
    },
  })
  return { colors: theme, unpainted: problems.find(p => p.startsWith("Desktop won't paint")) }
}

const THEMES = new Map([...TOPICS, DEFAULT].map(t => [t.id, themeFor(t)]))

// The aurora: soft blobs of the topic's color resting behind the chat. It stays
// still because continuous motion cost about 15% GPU and a still one measured 0%.
// The chat's status changes the light with one short fade: brighter while Claude
// works, an amber glow in the top right corner while the chat waits on the person.
const SCENE = 'aurora-'

type Status = 'idle' | 'working' | 'waiting'

// How strong the topic's light is in each status.
const LEVEL: Record<Status, number> = { idle: 0.78, working: 1, waiting: 0.78 }

// `from` is what the last drawing showed: a status to fade from, 'fresh' for a scene
// drawn for the first time (it fades up from the dark), or 'same' for no fade.
const auroraFor = (t: Topic, status: Status, from: Status | 'fresh' | 'same'): string => {
  const hues = t.hues ?? [t.hue, (t.hue + 34) % 360, (t.hue + 326) % 360, (t.hue + 62) % 360]
  const m = t.isMuted === true ? 0.4 : 1
  const light = hues.map((h, i) => `.c${i}{stop-color:${hex(h, 85, 68)}}`).join('')
  const dark = hues.map((h, i) => `.c${i}{stop-color:${hex(h, 80, 46)}}`).join('')
  const grads = hues
    .map(
      (_, i) =>
        `<radialGradient id="g${i}"><stop class="c${i}" offset="0" stop-opacity="1"/>` +
        `<stop class="c${i}" offset="0.55" stop-opacity="0.46"/><stop class="c${i}" offset="1" stop-opacity="0"/></radialGradient>`,
    )
    .join('')
  // Amber, or a cool white-blue on the warm topics where amber would not show.
  const amber = t.hue <= 80 || t.hue >= 330 ? hex(192, 90, 68) : hex(40, 96, 56)

  // The topic's light: one fade from the last level to this one, then it holds.
  const level = LEVEL[status]
  const fade = from === 'fresh' ? 3.6 : 2.8
  const start = from === 'fresh' ? 0 : from === 'same' ? level : LEVEL[from]
  const lv = `.lv{opacity:${level}${start !== level ? `;animation:shift ${fade}s ease-in-out 1 both` : ''}}`

  // The amber glow: ease in when the chat starts waiting, ease out when it stops.
  const wasWaiting = from === 'waiting'
  const isWaiting = status === 'waiting'
  const glow = isWaiting
    ? `.wait{opacity:0.8${from === 'same' || wasWaiting ? '' : `;animation:glowin ${fade}s ease-in-out 1 both`}}`
    : wasWaiting
      ? `.wait{opacity:0;animation:glowout ${fade}s ease-in-out 1 both}`
      : ''

  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1000" preserveAspectRatio="xMidYMid slice">` +
    `<style>` +
    `.bg{fill:${hex(t.hue, 45 * m, 89)}}${light}` +
    `@media (prefers-color-scheme: dark){.bg{fill:${hex(t.hue, 28 * m, 8)}}${dark}}` +
    lv +
    `@keyframes shift{from{opacity:${start}}to{opacity:${level}}}` +
    glow +
    `@keyframes glowin{from{opacity:0}to{opacity:0.8}}` +
    `@keyframes glowout{from{opacity:0.8}to{opacity:0}}` +
    `</style>` +
    `<defs>${grads}<radialGradient id="ga"><stop offset="0" stop-color="${amber}" stop-opacity="0.95"/>` +
    `<stop offset="0.5" stop-color="${amber}" stop-opacity="0.4"/><stop offset="1" stop-color="${amber}" stop-opacity="0"/></radialGradient></defs>` +
    `<rect class="bg" width="1600" height="1000"/>` +
    `<g class="lv">` +
    `<ellipse cx="260" cy="170" rx="620" ry="430" fill="url(#g0)"/>` +
    `<ellipse cx="1380" cy="210" rx="640" ry="460" fill="url(#g1)"/>` +
    `<ellipse cx="330" cy="900" rx="600" ry="420" fill="url(#g2)"/>` +
    `<ellipse cx="1320" cy="880" rx="660" ry="440" fill="url(#g3)"/>` +
    `</g>` +
    (isWaiting || wasWaiting ? `<ellipse class="wait" cx="1470" cy="90" rx="560" ry="400" fill="url(#ga)"/>` : '') +
    `</svg>`
  )
}

const TOPIC_BY_ID = new Map([...TOPICS, DEFAULT].map(t => [t.id, t]))

// What this chat is doing now (one process per chat; a reload starts at idle),
// what it was doing before, and when that changed.
let status: Status = 'idle'
let before: Status = 'idle'
let changedAt = 0
// The scene drawn last, and when it was first drawn.
let drawn = ''
let freshAt = 0

function to($: Api, next: Status): void {
  if (status === next) return
  before = status
  status = next
  changedAt = Date.now()
  freshAt = 0 // a status change ends the first fade-in
  $.ui.invalidate('ui.render')
}

// A topic's words as whole-word tests.
const TESTS = new Map(TOPICS.map(t => [t.id, t.words.map(w => new RegExp(`(?:^|[^a-z0-9])${w.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![a-z0-9])`))]))

// The topic with the most words in the text. Where a broad topic wins and one of
// its own areas was named too, the area takes it.
const pick = (text: string): Topic | undefined => {
  const s = text.toLowerCase()
  const hits = new Map(TOPICS.map(t => [t.id, (TESTS.get(t.id) ?? []).filter(r => r.test(s)).length]))
  const most = (among: Topic[]): Topic | undefined => {
    let best: Topic | undefined
    let bestHits = 0
    for (const t of among) {
      const n = hits.get(t.id) ?? 0
      if (n > bestHits) {
        best = t
        bestHits = n
      }
    }
    return best
  }
  const best = most(TOPICS)
  if (best === undefined) return undefined
  const top = best.parent ?? best.id
  return most(TOPICS.filter(t => t.parent === top)) ?? best
}

const DOTS: Record<string, string> = Object.fromEntries(TOPICS.filter(t => t.dot !== undefined).map(t => [t.id, t.dot as string]))
const ALL_DOTS = Object.values(DOTS)

// The chat's current title: the last custom or AI title in the tail of its transcript.
async function currentTitle($: Api, transcript: string): Promise<string | undefined> {
  if (transcript === '') return undefined
  const { size } = await $.fs.stat(transcript)
  const offset = Math.max(0, size - 512 * 1024)
  const tail = await $.fs.read(transcript, { offset, length: size - offset })
  let title: string | undefined
  for (const m of tail.matchAll(/"(?:customTitle|aiTitle)":"((?:[^"\\]|\\.)*)"/g)) {
    try {
      title = JSON.parse(`"${m[1]}"`) as string
    } catch {
      // a line cut by the range; skip it
    }
  }
  return title
}

const keyFor = (sessionId: string) => `tint:${sessionId}`

// The topic this process has applied (reset on reload; the store is the truth).
let applied: string | undefined

async function apply($: Api, id: string): Promise<void> {
  const t = THEMES.get(id)
  if (t === undefined) return
  if (t.unpainted !== undefined) $.ui.toast(`session-tint: ${t.unpainted}`)
  const set = await $.theme.set({ colors: t.colors, backdrop: { scene: SCENE + id, glass: { blur: 24, opacity: 0.5 } } })
  if (!set.isDrawn) $.ui.toast(`session-tint: color not drawn: ${set.reason}`)
  if (id !== DEFAULT.id) applied = id
}

// A row above the message box: how full the context window is, and how much of
// the session and weekly limits is used. The terminal has its own status line,
// so the row is drawn in the apps only.
type Reading = Pick<SessionUsage, 'context' | 'rateLimits'>
type Meter = { label: string; percent: number; note?: string }

let reading: Reading | undefined

const count = (n: number): string =>
  n >= 1_000_000 ? `${(n / 1_000_000).toFixed(n % 1_000_000 === 0 ? 0 : 1)}M` : n >= 1000 ? `${(n / 1000).toFixed(1)}k` : `${n}`

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

// A reset as a clock time, which stays true while the row sits undrawn.
const resetText = (iso: string | undefined, now: number): string | undefined => {
  if (iso === undefined) return undefined
  const at = new Date(iso)
  const ms = at.getTime()
  if (Number.isNaN(ms) || ms <= now) return undefined
  const hour = at.getHours()
  const minute = at.getMinutes()
  const clock = `${hour % 12 === 0 ? 12 : hour % 12}${minute === 0 ? '' : `:${String(minute).padStart(2, '0')}`} ${hour < 12 ? 'AM' : 'PM'}`
  const isToday = new Date(now).toDateString() === at.toDateString()
  return `resets ${isToday ? '' : `${DAYS[at.getDay()]} `}${clock}`
}

const LABELS: Record<string, string> = { five_hour: 'Session', seven_day: 'Week', spend_limit: 'Spend' }

const metersOf = (r: Reading, now: number): Meter[] => {
  const list: Meter[] = []
  if (r.context.percent !== undefined) {
    const note = r.context.tokens === undefined ? undefined : `${count(r.context.tokens)} of ${count(r.context.window)}`
    list.push({ label: 'Context', percent: r.context.percent, note })
  }
  for (const limit of r.rateLimits) {
    const label = LABELS[limit.kind] ?? limit.kind.replace(/[^a-z0-9]+/gi, ' ').trim().slice(0, 10)
    list.push({ label, percent: limit.percentUsed, note: resetText(limit.resetsAt, now) })
  }
  return list
}

function keep($: Api, next: Reading): void {
  reading = { context: next.context, rateLimits: next.rateLimits }
  $.ui.invalidate('ui.render')
}

// Each meter is a rounded pill with a soft glow under a gradient fill: green,
// then amber from 60, then red from 85, with its detail beside it. Nothing moves.
const SLOT = 292
const BAR_X = 56
const BAR_W = 100
const RAMPS: [string, string][] = [
  ['#2fb673', '#5fd6c0'],
  ['#e0a11f', '#f2c14e'],
  ['#e0452f', '#f27a8a'],
]

const usageSvg = (meters: Meter[]): string => {
  const width = meters.length * SLOT - 8
  let defs = ''
  let body = ''
  meters.forEach((m, i) => {
    const p = Math.max(0, Math.min(100, m.percent))
    const level = p >= 85 ? 2 : p >= 60 ? 1 : 0
    const [c0, c1] = RAMPS[level] ?? ['#2fb673', '#5fd6c0']
    const w = ((BAR_W * p) / 100).toFixed(1)
    defs +=
      `<linearGradient id="g${i}"><stop offset="0" stop-color="${c0}"/><stop offset="1" stop-color="${c1}"/></linearGradient>` +
      `<clipPath id="c${i}"><rect x="${BAR_X}" y="7" width="${BAR_W}" height="10" rx="5"/></clipPath>`
    const hasNote = m.note !== undefined
    body +=
      `<g transform="translate(${i * SLOT},0)">` +
      `<title>${m.label}: ${Math.round(m.percent)}%${hasNote ? `, ${m.note}` : ''}</title>` +
      `<rect width="${SLOT - 8}" height="24" fill="transparent"/>` +
      `<text class="lb" x="0" y="16">${m.label}</text>` +
      `<rect class="gl" x="${BAR_X}" y="5" width="${w}" height="14" rx="7" fill="${c0}"/>` +
      `<rect class="tr" x="${BAR_X}" y="7" width="${BAR_W}" height="10" rx="5"/>` +
      `<g clip-path="url(#c${i})"><rect x="${BAR_X}" y="7" width="${w}" height="10" rx="5" fill="url(#g${i})"/></g>` +
      `<text class="pc" x="${BAR_X + BAR_W + 8}" y="16">${Math.round(m.percent)}%</text>` +
      (hasNote ? `<text class="nt" x="${BAR_X + BAR_W + 44}" y="16">${m.note}</text>` : '') +
      `</g>`
  })
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="24" viewBox="0 0 ${width} 24">` +
    `<style>` +
    `text{font-family:system-ui,-apple-system,Segoe UI,sans-serif;font-size:12.5px}` +
    `.lb{fill:#5c5c5c;letter-spacing:.3px}.pc{fill:#262626;font-weight:600;font-variant-numeric:tabular-nums}.nt{fill:#6a6a6a;font-size:11.5px}` +
    `.tr{fill:#000000;fill-opacity:.12}.gl{opacity:.2}` +
    `@media (prefers-color-scheme: dark){.lb{fill:#a8a8a8}.pc{fill:#f0f0f0}.nt{fill:#9a9a9a}.tr{fill:#ffffff;fill-opacity:.14}}` +
    `</style><defs>${defs}</defs>${body}</svg>`
  )
}

export const register: Register = on => {
  on('session.measure', ($, e, next) => {
    keep($, e)
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, ($, e, next) => {
    if (e.surface === 'terminal' || e.props.hasSurvey || reading === undefined) return next(e)
    const now = Date.now()
    const meters = metersOf(reading, now)
    if (meters.length === 0) return next(e)
    const { Svg } = $.ui.resolve(e)
    const alt = meters.map(m => `${m.label} ${Math.round(m.percent)}%`).join(', ')
    return h(Svg, { source: usageSvg(meters), alt, height: 24 }) as RenderElement
  })

  // Draw the aurora and keep its status current.
  on('ui.render', { component: 'Backdrop' }, ($, e, next) => {
    if (e.surface !== 'desktop' && e.surface !== 'mobile') return next(e)
    const name = e.props.scene
    const topic = name.startsWith(SCENE) ? TOPIC_BY_ID.get(name.slice(SCENE.length)) : undefined
    if (topic === undefined) return next(e)
    const { Svg } = $.ui.resolve(e)
    const now = Date.now()
    if (name !== drawn) {
      drawn = name
      freshAt = now
    }
    const from = now - freshAt < 3600 ? 'fresh' : now - changedAt < 2800 ? before : 'same'
    const alt = status === 'working' ? 'Bright light, Claude is working' : status === 'waiting' ? 'A glow in the corner, waiting on you' : 'Soft colored light'
    return h(Svg, { source: auroraFor(topic, status, from), alt, isInteractive: true }) as RenderElement
  })

  on('turn.start', ($, e, next) => {
    if (e.agentId === undefined) to($, 'working')
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    if (e.agentId === undefined) to($, 'idle')
    return result
  })

  // A question to the person, or a permission prompt, is the chat waiting on them.
  on('tool.call', { tool: 'AskUserQuestion' }, async ($, e, next) => {
    to($, 'waiting')
    try {
      return await next(e)
    } finally {
      to($, 'working')
    }
  })

  on('tool.check', async ($, e, next) => {
    const verdict = await next(e)
    if (verdict.decision === 'ask') to($, 'waiting')
    return verdict
  })

  on('tool.run', ($, e, next) => {
    if (status === 'waiting') to($, 'working')
    return next(e)
  })

  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'tint',
      description: `Color this session by topic: ${TOPICS.map(t => t.id).join(', ')}, auto, or off`,
    })
    const saved = await $.store.get(keyFor(await $.session.id()))
    if (typeof saved === 'string' && saved !== 'off') await apply($, saved)
    else if (saved === undefined) await apply($, DEFAULT.id)
    const result = await next(e)
    keep($, await $.session.usage())
    return result
  })

  on('prompt.submit', async ($, e, next) => {
    if (e.command === undefined && e.isMeta !== true && applied === undefined) {
      const key = keyFor(await $.session.id())
      const saved = await $.store.get(key)
      if (saved === undefined) {
        const t = pick(e.text)
        if (t !== undefined) {
          await $.store.set(key, t.id)
          await apply($, t.id)
          $.ui.toast(`Tinted ${t.label}. /tint to change.`)
        }
      }
    }
    return next(e)
  })

  // Put the topic's dot at the front of the chat's title, so the sidebar shows it.
  on('classic.UserPromptSubmit', async ($, e, next) => {
    const result = await next(e)
    if (result.block !== undefined) return result
    const topic = await $.store.get(keyFor(await $.session.id()))
    const dot = typeof topic === 'string' ? DOTS[topic] : undefined
    if (dot === undefined) return result
    const title = await currentTitle($, e.transcript_path)
    if (title === undefined || title.startsWith(dot)) return result
    const bare = ALL_DOTS.reduce((t, d) => (t.startsWith(d) ? t.slice(d.length).trimStart() : t), title)
    return { ...result, sessionTitle: `${dot} ${bare}` }
  })

  on('command.run', { command: 'tint' }, async ($, e) => {
    const arg = e.args.trim().toLowerCase()
    const key = keyFor(await $.session.id())
    const list = TOPICS.map(t => `${t.id} (${t.label})`).join(', ')

    if (arg === '') {
      const saved = await $.store.get(key)
      const now = TOPICS.find(t => t.id === saved)?.label ?? 'none'
      return { text: `Tint: ${now}. Use /tint <topic>, /tint auto, or /tint off. Topics: ${list}`, isTextDisplayOnly: true }
    }
    if (arg === 'off') {
      await $.store.set(key, 'off')
      applied = 'off'
      await $.theme.clear()
      return { text: 'Tint off for this session.', isTextDisplayOnly: true }
    }
    if (arg === 'auto') {
      await $.store.delete(key)
      applied = undefined
      await apply($, DEFAULT.id)
      return { text: 'Tint will pick from your next prompt.', isTextDisplayOnly: true }
    }
    const t = TOPICS.find(x => x.id === arg || x.label.toLowerCase() === arg)
    if (t === undefined) return { text: `Unknown topic "${arg}". Topics: ${list}`, isTextDisplayOnly: true }
    await $.store.set(key, t.id)
    await apply($, t.id)
    return { text: `Tinted ${t.label}.`, isTextDisplayOnly: true }
  })
}
