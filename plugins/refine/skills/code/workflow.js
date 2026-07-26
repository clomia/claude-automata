export const meta = {
  name: 'refine-code',
  description: 'Code architecture optimization — cross-examine antipatterns into consensus, then apply only the highest-ROI refactors',
  phases: [
    { title: 'Map', detail: 'split the codebase into independent analysis regions' },
    { title: 'Identify', detail: 'find antipatterns per region until findings run dry' },
    { title: 'Deliberate', detail: 'defend, critique, and settle the consensus list' },
    { title: 'Plan', detail: 'draft self-contained refactoring plans' },
    { title: 'Review', detail: 'audit each plan through value and side-effect lenses' },
    { title: 'Refine', detail: 'improve plans and fix the execution order' },
    { title: 'Apply', detail: 'execute plans sequentially and test' },
  ],
}

const SYNOD = 'refine:synod'
const cfg = typeof args === 'string' ? JSON.parse(args) : args
const { focusArea, projectDir, agoraPath, repomixCmd, principlesPath } = cfg
const plansDir = `${agoraPath}/refactor-manager/plans`

const slug = (s) => String(s).trim().replace(/[^a-zA-Z0-9._-]+/g, '-').replace(/^-+|-+$/g, '')

function header(agoraName) {
  return [
    `Your Agora Path: ${agoraPath}/${agoraName}/`,
    `Agora Base Path: ${agoraPath}/`,
    `Project Dir: ${projectDir}`,
    `principles: ${principlesPath}`,
    `repomix: ${repomixCmd}`,
    focusArea ? `집중 분석 영역: ${focusArea}` : null,
    '',
  ].filter((l) => l !== null).join('\n')
}

// agent의 null은 결과가 아니라 실패다 — session limit·skip·safety block.
// 첫 실패에서 멈춰야 남은 호출이 같은 벽에 줄줄이 부딪히지 않고, Agora가 재개 지점으로 남는다.
let halted = null
const synod = async (agoraName, task, opts = {}) => {
  if (halted) return null
  const res = await agent(header(agoraName) + task, { agentType: SYNOD, ...opts })
  if (res === null) {
    halted = opts.label ?? agoraName
    log(`halted at ${halted} — agent returned no result (limit, skip, or block)`)
  }
  return res
}

const outcome = (status, extra = {}) =>
  halted ? { status: 'interrupted', at: halted, agoraPath, ...extra } : { status, agoraPath, ...extra }

// 동시 실행은 session limit을 조기 소진시킨다 — agent는 한 번에 하나씩.
// 하나가 죽어도 run은 계속된다.
const series = async (tasks) => {
  const out = []
  for (const task of tasks) {
    try {
      out.push(await task())
    } catch (e) {
      log(`series[${out.length}] failed: ${e}`)
      out.push(null)
    }
  }
  return out
}

const PRINCIPLE = `## refactoring 원칙 (principles 해석)
- 최대한 단순한 설계로 side-effect 없이 최대한 많은 antipattern을 제거하라.
- 모든 antipattern 제거는 불가능하다. ROI 최적해를 찾아라.
- backlog proposal 금지. ROI 낮은 계획은 폐기하라.`

const REGIONS_SCHEMA = {
  type: 'object',
  required: ['regions'],
  properties: {
    regions: {
      type: 'array',
      items: {
        type: 'object',
        required: ['name', 'scope'],
        properties: {
          name: { type: 'string', description: 'English kebab-case identifier (becomes the Agora directory name)' },
          scope: { type: 'string', description: '이 영역이 책임지는 범위 (경로·module)' },
        },
      },
    },
  },
}

const ANTIPATTERNS_SCHEMA = {
  type: 'object',
  required: ['antipatterns'],
  properties: {
    antipatterns: {
      type: 'array',
      items: {
        type: 'object',
        required: ['title'],
        properties: {
          title: { type: 'string' },
          reason: { type: 'string' },
        },
      },
    },
  },
}

const CONSENSUS_SCHEMA = {
  type: 'object',
  required: ['count'],
  properties: {
    count: { type: 'integer', description: '합의된 antipattern 수' },
    titles: { type: 'array', items: { type: 'string' } },
  },
}

const PLANS_SCHEMA = {
  type: 'object',
  required: ['plans'],
  properties: {
    plans: {
      type: 'array',
      items: {
        type: 'object',
        required: ['name'],
        properties: {
          name: {
            type: 'string',
            pattern: '^[0-9]+-[a-z0-9]+(-[a-z0-9]+)*$',
            description: "English kebab-case '{index}-{name}', exactly matching the plan directory you wrote",
          },
        },
      },
    },
  },
}

const ORDER_SCHEMA = {
  type: 'object',
  required: ['executionOrder'],
  properties: {
    executionOrder: { type: 'array', items: { type: 'string' } },
  },
}

const APPLY_SCHEMA = {
  type: 'object',
  required: ['status'],
  properties: {
    status: { type: 'string', enum: ['done', 'partial', 'skipped'] },
    summary: { type: 'string' },
    testsPassed: { type: 'boolean' },
  },
}

const FINAL_SCHEMA = {
  type: 'object',
  required: ['ok'],
  properties: {
    ok: { type: 'boolean' },
    notes: { type: 'string' },
  },
}

// 1. Map — 분석 영역 정의 + 독립 검수
phase('Map')
await synod(
  'cartographer',
  `# 임무: 분석 영역 정의
codebase를 독립적으로 해석 가능한 분석 영역으로 나눠라.
모든 영역은 경계가 명확히 나누어 떨어져야 하고, agent 하나가 전수 분석할 수 있는 크기여야 한다.
각 영역의 착수 context(범위·진입점·핵심 파일)를 네 Agora에 기록하라.`,
  { label: 'map:draft', schema: REGIONS_SCHEMA },
)
const mapping = await synod(
  'cartographer',
  `# 임무: 분석 영역 검수
네 Agora의 분석 영역들을 검수하라. 경계가 모호하거나 겹치면 수정해서 반영하고, 최종 영역 목록을 반환하라.`,
  { label: 'map:review', schema: REGIONS_SCHEMA },
)
const usedDirs = new Set()
const regions = (mapping?.regions ?? []).map((r, i) => {
  let dir = slug(r.name) || `region-${i + 1}`
  while (usedDirs.has(dir)) dir = `${dir}-${i + 1}`
  usedDirs.add(dir)
  return { ...r, dir }
})
if (!regions.length) return outcome('no-regions')
log(`${regions.length} regions: ${regions.map((r) => r.dir).join(', ')}`)

// 2. Identify — 영역별 antipattern 식별: 새 발견이 마를 때까지 재수색
phase('Identify')
const SWEEPS = 4
async function identifyRegion(r) {
  let count = 0
  for (let round = 1; round <= SWEEPS; round++) {
    const res = await synod(
      r.dir,
      `# 임무: antipattern 식별 — 영역 '${r.dir}' (${r.scope})
이 영역의 antipattern을 식별하고 네 Agora에 기록하라.
각 antipattern의 존재 이유를 코드 주변 환경과 history(.claude/·문서·설정·git 등)에서 추론해 함께 기록하라.
네 Agora에 이미 antipattern이 기록되어 있다면 그 너머의 새 antipattern만 기록·반환하라. 새 antipattern이 없으면 빈 배열을 반환하라.`,
      { label: `identify:${r.dir}#${round}`, schema: ANTIPATTERNS_SCHEMA },
    )
    const fresh = res?.antipatterns?.length ?? 0
    count += fresh
    if (!fresh) break
    if (round === SWEEPS) log(`${r.dir}: ${SWEEPS} sweeps spent, still finding — coverage capped`)
  }
  return count
}
const counts = (await series(regions.map((r) => () => identifyRegion(r)))).filter((n) => n !== null)
const totalAntipatterns = counts.reduce((a, b) => a + b, 0)
if (totalAntipatterns === 0) return outcome('no-antipatterns')
log(`${totalAntipatterns} antipatterns across ${regions.length} regions`)

// 3. Deliberate — 변호·비판·합의 (barriers: 각 단계가 이전 단계 전체 산출물을 요구)
// 영역이 하나면 독립 skeptic이 비판을 맡아 교차검증을 보존한다
phase('Deliberate')
const names = regions.map((r) => r.dir)
const critics =
  regions.length > 1
    ? regions.map((r) => ({
        dir: r.dir,
        role: `영역 '${r.dir}'의 변호인이자 다른 영역의 비판자`,
        targets: names.filter((n) => n !== r.dir),
      }))
    : [{ dir: 'skeptic', role: '독립 비판자', targets: names }]

// 3.1 비판: 대상 영역의 antipattern을 검토, 비평은 자기 Agora에 기록
await series(
  critics.map((c) => () =>
    synod(
      c.dir,
      `# 임무: 비판 (회의 1/3)
너는 ${c.role}다.
대상 영역(${c.targets.join(', ')})의 Agora에 기록된 antipattern 중 실재하지 않거나 존재 이유가 여전히 정당한 오검출을 지목하고, 그들이 놓친 antipattern을 찾아 보완하라.
각 비평과 보완 antipattern을 네 Agora에 기록하라 (누구의 어떤 antipattern에 대한 것인지 명시).`,
      { label: `critique:${c.dir}` },
    ),
  ),
)

// 3.2 반박: 자기 antipattern에 달린 비평을 찾아 수용/반박
await series(
  regions.map((r) => () =>
    synod(
      r.dir,
      `# 임무: 반박 (회의 2/3)
비판자들(${critics.map((c) => c.dir).filter((d) => d !== r.dir).join(', ')})의 Agora에서 너의 antipattern을 겨냥한 비평을 모두 찾아,
각 비평에 대한 수용/반박 의견을 네 Agora에 기록하라.`,
      { label: `rebut:${r.dir}` },
    ),
  ),
)

// 3.3 합의: cartographer가 종합하고 완전성을 검수
await synod(
  'cartographer',
  `# 임무: 합의 도출 (회의 3/3)
모든 antipattern·비평·반박(${agoraPath}/ 전체)을 종합해서 합의된 antipattern list를
${agoraPath}/cartographer/consensus.md 에 작성하라.
모든 antipattern을 빠짐없이 채택/기각으로 판정하고 근거를 남겨라. 실재하며 개선 가치가 있는 것만 채택하라.`,
  { label: 'consensus:draft', schema: CONSENSUS_SCHEMA },
)
const consensus = await synod(
  'cartographer',
  `# 임무: 합의 완전성 검수
${agoraPath}/ 전체를 consensus.md 와 대조해 판정이 누락된 antipattern과 반영되지 않은 비평·반박을 찾아라.
누락이 있으면 consensus.md 를 수정하고, 최종 list를 반환하라.`,
  { label: 'consensus:review', schema: CONSENSUS_SCHEMA },
)
if (!consensus?.count) return outcome('no-consensus')
log(`consensus: ${consensus.count} antipatterns`)

// 4. Plan — refactoring 계획 수립
phase('Plan')
const planned = await synod(
  'refactor-manager',
  `# 임무: refactoring 계획 수립
합의된 antipattern(${agoraPath}/cartographer/consensus.md)을 파악한 뒤 refactoring 계획을 작성하라.
${PRINCIPLE}
- 전체 작업을 최대한 크게 쪼개서 계획 개수를 적게 유지하라.
각 계획은 self-contained markdown으로 ${plansDir}/{순번}-{kebab-name}/proposal.md 에 작성한다.
proposal.md는 대상 antipattern / 변경 내용 / ROI 근거 / 예상 side-effect / 영향 범위를 포함한다.`,
  { label: 'plan', schema: PLANS_SCHEMA },
)
const plans = (planned?.plans ?? []).map((p, i) => {
  const name = String(p.name).trim()
  return {
    name,
    label: slug(name) || `plan-${i + 1}`,
    proposal: `${plansDir}/${name}/proposal.md`,
  }
})
if (!plans.length) return outcome('no-plans', { antipatterns: consensus.count })
log(`${plans.length} refactoring plans`)

// 5. Review — 계획별 · 렌즈별 독립 검수
phase('Review')
const LENSES = [
  { key: 'value', charge: '계획이 실제로 유효한 개선안인지 득실을 계산하라.' },
  { key: 'side-effects', charge: '계획이 고려하지 못한 side-effect를 탐색하라.' },
]
await series(
  plans.flatMap((p) =>
    LENSES.map((l) => () =>
      synod(
        `review-${p.name}-${l.key}`,
        `# 임무: refactoring 계획 검수 — '${p.name}' / ${l.key}
합의된 antipattern(${agoraPath}/cartographer/consensus.md)과 대상 계획(${p.proposal})을 읽어라.
${l.charge}
issue나 개선점을 네 Agora에 기록하라.`,
        { label: `review:${p.label}:${l.key}` },
      ),
    ),
  ),
)

// 6. Refine — 검수 반영 + 실행 순서 확정
phase('Refine')
const refined = await synod(
  'refactor-manager',
  `# 임무: refactoring 계획 개선 + 실행 순서 확정
${agoraPath}/ 전체(계획들과 review-* 검수 기록)를 읽고, 검수 내용을 기반으로 각 계획을 개선하라.
${PRINCIPLE}
개선이 끝나면 계획들의 실행 순서를 확정하고, 그 순서를 계획 name 배열로 반환하라.`,
  { label: 'refine', schema: ORDER_SCHEMA },
)
const ordered = (refined?.executionOrder ?? [])
  .map((n) => String(n).trim())
  .filter((n) => plans.some((p) => p.name === n))
const order = [...new Set(ordered.length ? ordered : plans.map((p) => p.name))]
log(`execution order: ${order.join(' -> ')}`)

// 7. Apply — 순차 실행 후 최종 검수
phase('Apply')
const applied = []
for (const name of order) {
  const p = plans.find((x) => x.name === name)
  const res = await synod(
    `apply-${name}`,
    `# 임무: refactoring 수행 — '${name}'
계획(${p.proposal})을 읽고 그대로 구현하라. 실행 가능한 코드를 실제로 수정한다.
선행 적용 기록(${agoraPath}/apply-*)이 있으면 현재 상태 파악에 참고하라.
구현 후 project의 test suite를 실행해 회귀가 없음을 확인하고, 변경 영역을 cover하는 test가 없으면 추가하라.
변경 요약과 test 결과를 네 Agora에 기록하고 반환하라.`,
    { label: `apply:${p.label}`, schema: APPLY_SCHEMA },
  )
  applied.push({ name, status: res?.status ?? 'unknown', testsPassed: res?.testsPassed ?? null })
  log(`applied ${applied.length}/${order.length}: ${name} (${res?.status ?? 'unknown'})`)
}

const finalReview = await synod(
  'refactor-manager',
  `# 임무: 최종 검수
적용된 모든 계획(${agoraPath}/apply-* 기록)과 실제 변경된 코드를 종합 검수하라.
모든 변경이 principles에 부합하는지, side-effect가 없는지, test가 통과하는지 확인하고 결과를 반환하라.`,
  { label: 'final-review', schema: FINAL_SCHEMA },
)

return outcome('done', {
  regions: regions.length,
  antipatterns: consensus.count,
  consensusTitles: consensus.titles ?? [],
  plans: plans.length,
  applied,
  finalReview,
})
