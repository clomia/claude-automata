export const meta = {
  name: 'refine-architecture',
  description: 'Code architecture optimization — cross-examine antipatterns into consensus, then apply only the highest-ROI refactors',
  phases: [
    { title: 'Map', detail: 'split the codebase into independent analysis regions' },
    { title: 'Identify', detail: 'find antipatterns per region and infer why they exist' },
    { title: 'Deliberate', detail: 'defend, critique, and settle the consensus list' },
    { title: 'Plan', detail: 'draft self-contained refactoring plans' },
    { title: 'Review', detail: 'audit each plan for ROI and side effects' },
    { title: 'Refine', detail: 'improve plans and fix the execution order' },
    { title: 'Apply', detail: 'execute plans sequentially and test' },
  ],
}

const SYNOD = 'refine-architecture:synod'
const cfg = typeof args === 'string' ? JSON.parse(args) : args
const { focusArea, projectDir, agoraPath, repomixCmd, principlesPath } = cfg
const plansDir = `${agoraPath}/refactor-manager/plans`

const slug = (s) => String(s).trim().replace(/[^a-zA-Z0-9._-]+/g, '-').replace(/^-+|-+$/g, '')

function header(agoraName) {
  return [
    `Your Agora Path: ${agoraPath}/${agoraName}/`,
    `Agora Base Path: ${agoraPath}/`,
    `Project Dir: ${projectDir}`,
    `design-principles: ${principlesPath}`,
    `repomix: ${repomixCmd}`,
    focusArea ? `집중 분석 영역: ${focusArea}` : '분석 대상: 코드베이스 전체',
    '',
  ].join('\n')
}

const synod = (agoraName, task, opts = {}) =>
  agent(header(agoraName) + task, { agentType: SYNOD, ...opts })

const PRINCIPLE = `## 리팩토링 원칙 (design-principles 해석)
- 최대한 단순한 설계로 side-effect 없이 최대한 많은 안티패턴을 제거하라.
- 모든 안티패턴 제거는 불가능하다. ROI가 가장 높은 최적해를 찾아라.
- backlog proposal 금지. ROI 낮은 계획은 과감히 폐기하라.`

const CONSTRAINTS = `## Constraints
- 외부 인프라에 영향을 주는 변경 불가(API Spec, DB Schema, 외부 저장소/서비스 등). 코드 레벨 변경만 허용.
- 실행 가능한 코드(src/tests 등)만 대상으로 한다. 본 저장소만 수정한다.`

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
          reason: { type: 'string', description: '이 안티패턴이 존재하는 추론된 이유' },
        },
      },
    },
  },
}

const CONSENSUS_SCHEMA = {
  type: 'object',
  required: ['count'],
  properties: {
    count: { type: 'integer', description: '교차검증을 통과한 합의된 안티패턴 수' },
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
    executionOrder: { type: 'array', items: { type: 'string' }, description: '계획 name 들의 실행 순서' },
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
거시적 관점에서 전체 구조를 이해하고 **독립적으로 해석 가능한 분석 영역**으로 나눠라.
모든 영역은 모호한 경계 없이 명확히 나누어 떨어져야 한다.
각 영역의 착수 컨텍스트(범위·진입점·핵심 파일)를 네 Agora에 기록하라.`,
  { label: 'map:draft', schema: REGIONS_SCHEMA },
)
const mapping = await synod(
  'cartographer',
  `# 임무: 분석 영역 검수
${agoraPath}/cartographer/ 를 읽고 분석 영역 간 책임이 명확히 나누어 떨어지는지 검수하라.
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

// 2. Identify — 영역별 안티패턴 식별 (parallel)
phase('Identify')
const found = (
  await parallel(
    regions.map((r) => () =>
      synod(
        r.dir,
        `# 임무: 안티패턴 식별 — 영역 '${r.dir}' (${r.scope})
design-principles를 기준으로 이 영역의 안티패턴을 식별하고 네 Agora에 기록하라.
**모든 안티패턴에는 합리적인 이유가 존재한다.** 코드 주변 환경과 히스토리(.claude/·문서·설정·git 등)를 탐구해서
각 안티패턴의 존재 이유를 추론하고 함께 기록하라.`,
        { label: `identify:${r.dir}`, phase: 'Identify', schema: ANTIPATTERNS_SCHEMA },
      ),
    ),
  )
).filter(Boolean)

const totalAntipatterns = found.reduce((n, x) => n + (x.antipatterns?.length ?? 0), 0)
if (totalAntipatterns === 0) return { status: 'no-antipatterns', agoraPath }
log(`${totalAntipatterns} antipatterns across ${found.length} regions`)

// 3. Deliberate — 변호·비판·합의 (barriers: 각 단계가 이전 단계 전체 산출물을 요구)
phase('Deliberate')
const names = regions.map((r) => r.dir)

if (regions.length > 1) {
  // 3.1 비판: 다른 영역의 안티패턴을 검토, 비평은 자기 Agora에 기록
  await parallel(
    regions.map((r) => () =>
      synod(
        r.dir,
        `# 임무: 비판 (회의 1/3)
너는 영역 '${r.dir}'의 변호인이자 다른 영역의 비판자다.
다른 영역들(${names.filter((n) => n !== r.dir).join(', ')})의 Agora에 기록된 안티패턴을 비판적으로 검토하고,
각 비평을 **네 Agora**에 기록하라 (누구의 어떤 안티패턴에 대한 비평인지 명시).`,
        { label: `critique:${r.dir}`, phase: 'Deliberate' },
      ),
    ),
  )

  // 3.2 반박: 자기 안티패턴에 달린 비평을 찾아 수용/반박
  await parallel(
    regions.map((r) => () =>
      synod(
        r.dir,
        `# 임무: 반박 (회의 2/3)
다른 영역들의 Agora에서 너의 안티패턴을 겨냥한 비평을 모두 찾아 검토하고,
각 비평에 대한 수용/반박 의견을 네 Agora에 기록하라.`,
        { label: `rebut:${r.dir}`, phase: 'Deliberate' },
      ),
    ),
  )
}

// 3.3 합의: cartographer가 종합
const consensus = await synod(
  'cartographer',
  `# 임무: 합의 도출 (회의 3/3)
모든 영역의 안티패턴·비평·반박(${agoraPath}/ 전체)을 종합해서 **합의된 안티패턴 리스트**를
${agoraPath}/cartographer/consensus.md 에 작성하라.
교차검증을 통과한, 실재하며 개선 가치가 있는 안티패턴만 남겨라.`,
  { label: 'consensus', phase: 'Deliberate', schema: CONSENSUS_SCHEMA },
)
if (!consensus?.count) return { status: 'no-consensus', agoraPath }
log(`consensus: ${consensus.count} antipatterns`)

// 4. Plan — 리팩토링 계획 수립
phase('Plan')
const planned = await synod(
  'refactor-manager',
  `# 임무: 리팩토링 계획 수립
합의된 안티패턴(${agoraPath}/cartographer/consensus.md)을 파악한 뒤 리팩토링 계획을 작성하라.
${PRINCIPLE}
- 전체 작업을 최대한 크게 쪼개서 계획 갯수를 적게 유지하라.
## 계획 형식
각 계획은 self-contained 마크다운으로 ${plansDir}/{순번}-{kebab-name}/proposal.md 에 작성한다.
proposal.md는 다음을 포함한다: 대상 안티패턴 / 변경 내용 / ROI 근거 / 예상 side-effect / 영향 범위.
반환하는 각 계획 name 은 그 디렉토리명 '{순번}-{kebab-name}' 과 정확히 일치시켜라.`,
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
if (!plans.length) return { status: 'no-plans', antipatterns: consensus.count, agoraPath }
log(`${plans.length} refactoring plans`)

// 5. Review — 계획별 검수 (parallel)
phase('Review')
await parallel(
  plans.map((p) => () =>
    synod(
      `review-${p.name}`,
      `# 임무: 리팩토링 계획 검수 — '${p.name}'
합의된 안티패턴(${agoraPath}/cartographer/consensus.md)과 대상 계획(${p.proposal})을 읽어라.
- 계획이 실제로 유효한 개선안인지 득실을 계산·고찰하라.
- 계획이 고려하지 못한 side-effect를 탐색하라.
이슈나 개선점을 네 Agora(review.md)에 기록하라.`,
      { label: `review:${p.label}`, phase: 'Review' },
    ),
  ),
)

// 6. Refine — 검수 반영 + 실행 순서 확정
phase('Refine')
const refined = await synod(
  'refactor-manager',
  `# 임무: 리팩토링 계획 개선 + 실행 순서 확정
${agoraPath}/ 전체(계획들과 review-* 검수 기록)를 읽어 컨텍스트를 복원하라.
검수 내용을 기반으로 각 계획을 개선하라. 판단 기준은 리팩토링 원칙이다.
${PRINCIPLE}
개선이 끝나면 계획들의 **실행 순서**를 확정해서 ${agoraPath}/refactor-manager/execution-order.md 에 기록하고,
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
    `# 임무: 리팩토링 수행 — '${name}'
계획(${p.proposal})을 읽고 그대로 구현하라. 실행 가능한 코드를 실제로 수정한다.
${CONSTRAINTS}
구현 후 프로젝트의 테스트 스위트를 실행해 회귀가 없음을 확인하고, 변경 영역을 커버하는 테스트가 없으면 추가하라.
변경 요약과 테스트 결과를 네 Agora에 기록하고 반환하라.`,
    { label: `apply:${p.label}`, phase: 'Apply', schema: APPLY_SCHEMA },
  )
  applied.push({ name, status: res?.status ?? 'unknown', testsPassed: res?.testsPassed ?? null })
  log(`applied ${applied.length}/${order.length}: ${name}`)
}

const finalReview = await synod(
  'refactor-manager',
  `# 임무: 최종 검수
적용된 모든 계획(${agoraPath}/apply-* 기록)과 실제 변경된 코드를 종합 검수하라.
모든 변경이 리팩토링 원칙에 부합하는지, side-effect가 없는지, 테스트가 통과하는지 확인하고 결과를 반환하라.`,
  { label: 'final-review', phase: 'Apply', schema: FINAL_SCHEMA },
)

return {
  status: 'done',
  agoraPath,
  regions: regions.length,
  antipatterns: consensus.count,
  consensusTitles: consensus.titles ?? [],
  plans: plans.length,
  applied,
  finalReview,
}
