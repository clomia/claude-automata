export const meta = {
  name: 'refine-integrity',
  description: "Integrity-boundary optimization — cross-examine hazards into consensus, then absorb only the highest-ROI set into the boundary, pinned by tests",
  phases: [
    { title: 'Map', detail: 'split the codebase into independent analysis regions' },
    { title: 'Hunt', detail: 'hunt states outside the integrity boundary per region until findings run dry' },
    { title: 'Deliberate', detail: 'defend, critique, and settle the consensus list' },
    { title: 'Plan', detail: 'draft self-contained hardening plans' },
    { title: 'Review', detail: 'audit each plan through hazard-fit, simplicity, and test-pin lenses' },
    { title: 'Refine', detail: 'improve plans and fix the execution order' },
    { title: 'Apply', detail: 'execute plans sequentially with pinning tests' },
  ],
}

const SYNOD = 'refine:synod'
const cfg = typeof args === 'string' ? JSON.parse(args) : args
const { focusArea, projectDir, agoraPath, repomixCmd, principlesPath } = cfg
const plansDir = `${agoraPath}/integrity-manager/plans`
const consensusPath = `${agoraPath}/cartographer/consensus.md`

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

const synod = (agoraName, task, opts = {}) =>
  agent(header(agoraName) + task, { agentType: SYNOD, ...opts })

const PRINCIPLE = `## 강화 원칙 (principles 해석)
- 모든 hazard 흡수는 불가능하다. ROI 최적해를 찾아라.
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
          scope: { type: 'string', description: '이 영역이 책임지는 범위 (경로·모듈)' },
        },
      },
    },
  },
}

const HAZARDS_SCHEMA = {
  type: 'object',
  required: ['hazards'],
  properties: {
    hazards: {
      type: 'array',
      items: {
        type: 'object',
        required: ['title', 'verdict'],
        properties: {
          title: { type: 'string' },
          verdict: {
            type: 'string',
            enum: ['make-impossible', 'define-error', 'normal-flow', 'keep'],
            description: '경계 흡수 방식의 제안 — principles의 답 넷에 순서대로 대응',
          },
        },
      },
    },
  },
}

const CONSENSUS_SCHEMA = {
  type: 'object',
  required: ['count'],
  properties: {
    count: { type: 'integer', description: '합의된 hazard 수' },
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
    unabsorbed: { type: 'array', items: { type: 'string' } },
  },
}

// 1. Map — 분석 영역 정의 + 독립 검수
phase('Map')
await synod(
  'cartographer',
  `# 임무: 분석 영역 정의
코드베이스 전체 구조를 독립적으로 해석 가능한 분석 영역으로 나눠라.
모든 영역은 모호한 경계 없이 나누어 떨어져야 하고, 에이전트 하나가 전수 분석할 수 있는 크기여야 한다.
각 영역의 착수 컨텍스트(범위·진입점·경계 입력·핵심 파일)를 네 Agora에 기록하라.`,
  { label: 'map:draft', schema: REGIONS_SCHEMA },
)
const mapping = await synod(
  'cartographer',
  `# 임무: 분석 영역 검수
분석 영역 간 책임이 명확히 나누어 떨어지는지 검수하라.
경계가 모호하거나 겹치면 수정해서 네 Agora에 반영하고, 최종 영역 목록을 반환하라.`,
  { label: 'map:review', schema: REGIONS_SCHEMA },
)
const usedDirs = new Set()
const regions = (mapping?.regions ?? []).map((r, i) => {
  let dir = slug(r.name) || `region-${i + 1}`
  while (usedDirs.has(dir)) dir = `${dir}-${i + 1}`
  usedDirs.add(dir)
  return { ...r, dir }
})
if (!regions.length) return { status: 'no-regions', agoraPath }
log(`${regions.length} regions: ${regions.map((r) => r.dir).join(', ')}`)

// 2. Hunt — 영역별 hazard 수집: 새 발견이 마를 때까지 재수색 (parallel per region)
phase('Hunt')
const SWEEPS = 4
async function huntRegion(r) {
  let count = 0
  for (let round = 1; round <= SWEEPS; round++) {
    const res = await synod(
      r.dir,
      `# 임무: hazard 수집 — 영역 '${r.dir}' (${r.scope})
principles를 기준으로, 이 영역에서 무결성 경계가 포함하지 못하는 도달 가능한 상태를 모두 찾아라 — 검증 없는 경계 입력과 경합까지.
각 hazard의 도달 경로(입력·상태)와 현재 동작을 추적하고, 첫 질문의 답을 verdict로 제안하고 근거를 기록하라.
네 Agora에 이미 hazard가 기록되어 있다면 그 너머의 새 hazard만 기록·반환하라. 새 hazard가 없으면 빈 배열을 반환하라.`,
      { label: `hunt:${r.dir}#${round}`, phase: 'Hunt', schema: HAZARDS_SCHEMA },
    )
    const fresh = res?.hazards?.length ?? 0
    count += fresh
    if (!fresh) break
  }
  return count
}
const counts = (await parallel(regions.map((r) => () => huntRegion(r)))).filter((n) => n !== null)
const totalHazards = counts.reduce((a, b) => a + b, 0)
if (totalHazards === 0) return { status: 'no-hazards', agoraPath }
log(`${totalHazards} hazards across ${regions.length} regions`)

// 3. Deliberate — 비판·반박·합의 (barriers: 각 단계가 이전 단계 전체 산출물을 요구)
// 영역이 하나면 독립 스켑틱이 비판을 맡아 교차검증을 보존한다
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

// 3.1 비판: 대상 영역의 hazard를 검토, 비평은 자기 Agora에 기록
await parallel(
  critics.map((c) => () =>
    synod(
      c.dir,
      `# 임무: 비판 (회의 1/3)
너는 ${c.role}다.
대상 영역(${c.targets.join(', ')})의 Agora에 기록된 hazard를 검토하라 —
실제로는 도달 불가능한 오검출을 지목하고, verdict가 옳은지 반론하고, 그들이 놓친 hazard를 찾아 보완하라.
각 비평과 보완 hazard를 네 Agora에 기록하라 (누구의 어떤 hazard에 대한 것인지 명시).`,
      { label: `critique:${c.dir}`, phase: 'Deliberate' },
    ),
  ),
)

// 3.2 반박: 자기 hazard에 달린 비평을 찾아 수용/반박
await parallel(
  regions.map((r) => () =>
    synod(
      r.dir,
      `# 임무: 반박 (회의 2/3)
비판자들(${critics.map((c) => c.dir).filter((d) => d !== r.dir).join(', ')})의 Agora에서 너의 hazard를 겨냥한 비평을 모두 찾아 검토하고,
각 비평에 대한 수용/반박 의견을 네 Agora에 기록하라.`,
      { label: `rebut:${r.dir}`, phase: 'Deliberate' },
    ),
  ),
)

// 3.3 합의: cartographer가 종합하고 완전성을 검수
await synod(
  'cartographer',
  `# 임무: 합의 도출 (회의 3/3)
모든 hazard·비평·반박(${agoraPath}/ 전체)을 종합해서 합의된 hazard 리스트를
${consensusPath} 에 작성하라.
모든 hazard를 빠짐없이 채택/기각으로 판정하고 근거를 남겨라. 교차검증을 통과한 — 실재하고 도달 가능하며 경계 안으로 흡수할 가치가 있는 — hazard만 verdict와 함께 리스트에 남겨라.
verdict가 keep인 것은 근거만 기록하고 리스트에서 제외한다.`,
  { label: 'consensus:draft', phase: 'Deliberate', schema: CONSENSUS_SCHEMA },
)
const consensus = await synod(
  'cartographer',
  `# 임무: 합의 완전성 검수
${agoraPath}/ 전체를 consensus.md 와 대조해 판정이 누락된 hazard와 반영되지 않은 비평·반박을 찾아라.
누락이 있으면 consensus.md 를 수정하고, 최종 리스트를 반환하라.`,
  { label: 'consensus:review', phase: 'Deliberate', schema: CONSENSUS_SCHEMA },
)
if (!consensus?.count) return { status: 'no-consensus', agoraPath }
log(`consensus: ${consensus.count} hazards`)

// 4. Plan — 강화 계획 수립
phase('Plan')
const planned = await synod(
  'integrity-manager',
  `# 임무: 강화 계획 수립
합의된 hazard(${consensusPath})를 파악한 뒤 무결성 강화 계획을 작성하라.
${PRINCIPLE}
- 전체 작업을 최대한 크게 쪼개서 계획 개수를 적게 유지하라.
## 계획 형식
각 계획은 self-contained 마크다운으로 ${plansDir}/{순번}-{kebab-name}/proposal.md 에 작성한다.
proposal.md는 다음을 포함한다: 대상 hazard와 verdict / 변경 내용 / 고정 테스트 / ROI 근거 / 예상 side-effect / 영향 범위.`,
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
if (!plans.length) return { status: 'no-plans', hazards: consensus.count, unabsorbed: consensus.titles ?? [], agoraPath }
log(`${plans.length} hardening plans`)

// 5. Review — 계획별 · 렌즈별 독립 검수 (parallel)
phase('Review')
const LENSES = [
  { key: 'hazard-fit', charge: '계획이 hazard를 실제로 제거하는지, verdict에 맞는 최단 해법인지 따져라.' },
  { key: 'simplicity', charge: '계획이 새로운 hazard나 복잡성을 만들지 않는지 검증하라.' },
  { key: 'test-pin', charge: '고정 테스트가 정의된 behavior를 정확히 고정하는지 확인하라.' },
]
await parallel(
  plans.flatMap((p) =>
    LENSES.map((l) => () =>
      synod(
        `review-${p.name}-${l.key}`,
        `# 임무: 강화 계획 검수 — '${p.name}' / ${l.key}
합의된 hazard(${consensusPath})와 대상 계획(${p.proposal})을 읽어라.
${l.charge}
이슈나 개선점을 네 Agora에 기록하라.`,
        { label: `review:${p.label}:${l.key}`, phase: 'Review' },
      ),
    ),
  ),
)

// 6. Refine — 검수 반영 + 실행 순서 확정
phase('Refine')
const refined = await synod(
  'integrity-manager',
  `# 임무: 강화 계획 개선 + 실행 순서 확정
${agoraPath}/ 전체(계획들과 review-* 검수 기록)를 읽어 컨텍스트를 복원하라.
검수 내용을 기반으로 각 계획을 개선하라.
${PRINCIPLE}
계획들의 실행 순서를 확정해서 ${agoraPath}/integrity-manager/execution-order.md 에 기록하고,
그 순서를 계획 name 배열로 반환하라.`,
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
    `# 임무: 강화 수행 — '${name}'
계획(${p.proposal})을 읽고 그대로 구현하라. 실행 가능한 코드를 실제로 수정한다.
선행 적용 기록(${agoraPath}/apply-*)이 있으면 현재 상태 파악에 참고하라.
**수정마다 새로 정의된 behavior를 고정하는 테스트를 추가하고**, 전체 테스트 스위트로 회귀가 없음을 확인하라.
변경 요약과 테스트 결과를 네 Agora에 기록하고 반환하라.`,
    { label: `apply:${p.label}`, phase: 'Apply', schema: APPLY_SCHEMA },
  )
  applied.push({ name, status: res?.status ?? 'unknown', testsPassed: res?.testsPassed ?? null })
  log(`applied ${applied.length}/${order.length}: ${name} (${res?.status ?? 'unknown'})`)
}

const finalReview = await synod(
  'integrity-manager',
  `# 임무: 최종 검수
적용된 모든 계획(${agoraPath}/apply-* 기록)과 실제 변경된 코드를 종합 검수하라.
각 정의가 테스트로 고정되고 이유가 기록되었는지, 전체 테스트가 통과하는지 확인하고,
확정됐으나 흡수되지 않은 hazard를 unabsorbed로 수집해 함께 반환하라.`,
  { label: 'final-review', phase: 'Apply', schema: FINAL_SCHEMA },
)

return {
  status: 'done',
  agoraPath,
  regions: regions.length,
  hazards: consensus.count,
  consensusTitles: consensus.titles ?? [],
  plans: plans.length,
  applied,
  finalReview,
}
