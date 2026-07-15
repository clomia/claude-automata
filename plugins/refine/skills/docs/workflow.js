export const meta = {
  name: 'refine-docs',
  description: 'Documentation-to-code alignment — verify every claim in every non-executable text against the code, cross-examine discrepancies into consensus, then apply only the highest-ROI fixes',
  phases: [
    { title: 'Census', detail: 'inventory every non-executable text and split into verification regions' },
    { title: 'Verify', detail: 'check every claim in every document against the code' },
    { title: 'Deliberate', detail: 'defend, critique, and settle the consensus list' },
    { title: 'Plan', detail: 'draft self-contained alignment plans' },
    { title: 'Review', detail: 'audit each plan for ROI and side effects' },
    { title: 'Refine', detail: 'improve plans and fix the execution order' },
    { title: 'Apply', detail: 'execute plans sequentially and re-verify' },
  ],
}

const SYNOD = 'refine:synod'
const cfg = typeof args === 'string' ? JSON.parse(args) : args
const { focusArea, projectDir, agoraPath, repomixCmd, principlesPath } = cfg
const plansDir = `${agoraPath}/doc-manager/plans`

const slug = (s) => String(s).trim().replace(/[^a-zA-Z0-9._-]+/g, '-').replace(/^-+|-+$/g, '')

function header(agoraName) {
  return [
    `Your Agora Path: ${agoraPath}/${agoraName}/`,
    `Agora Base Path: ${agoraPath}/`,
    `Project Dir: ${projectDir}`,
    `principles: ${principlesPath}`,
    `repomix: ${repomixCmd}`,
    focusArea ? `집중 분석 영역: ${focusArea}` : '분석 대상: 레포지토리 전체',
    '',
  ].join('\n')
}

const synod = (agoraName, task, opts = {}) =>
  agent(header(agoraName) + task, { agentType: SYNOD, ...opts })

const DOMAIN = `**실행시킬 수 없는 텍스트는 모두 문서다** — 마크다운, 문서 시스템(openspec 등), 주석·docstring, 설정의 설명 텍스트.`

const PRINCIPLE = `## 정합 원칙 (principles 해석)
- 모든 발견 해소는 불가능하다. ROI가 가장 높은 최적해를 찾아라.
- backlog proposal 금지. ROI 낮은 계획은 과감히 폐기하라.`

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
          scope: { type: 'string', description: '이 영역이 책임지는 문서 집합과 그 문서들이 서술하는 코드 범위' },
        },
      },
    },
  },
}

const FINDINGS_SCHEMA = {
  type: 'object',
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['title', 'kind'],
        properties: {
          title: { type: 'string' },
          kind: {
            type: 'string',
            enum: ['mismatch', 'duplication', 'dead-doc', 'restating-comment', 'code-defect'],
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
    count: { type: 'integer', description: '교차검증을 통과한 합의된 발견 수' },
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
    codeFindings: {
      type: 'array',
      items: { type: 'string' },
      description: '문서가 드러낸 코드 결함들 — 이 워크플로우가 수정하지 않고 보고만 하는 것',
    },
  },
}

// 1. Census — 문서 전수조사 + 완전성 검수
phase('Census')
await synod(
  'cartographer',
  `# 임무: 문서 전수조사와 검증 영역 정의
${DOMAIN}
레포지토리의 문서를 하나도 빠짐없이 목록화하고, **독립적으로 검증 가능한 영역**으로 나눠라.
한 영역은 문서 집합과 그 문서들이 서술하는 코드 범위로 구성된다. 모든 영역은 모호한 경계 없이 명확히 나누어 떨어져야 한다.
영역별 문서 인벤토리와 착수 컨텍스트를 네 Agora에 기록하라.`,
  { label: 'census:draft', schema: REGIONS_SCHEMA },
)
const mapping = await synod(
  'cartographer',
  `# 임무: 전수조사 완전성 검수
${DOMAIN}
${agoraPath}/cartographer/ 를 읽고 실제 파일 시스템과 대조해 인벤토리에서 누락된 문서를 찾아라.
영역 간 책임이 명확히 나누어 떨어지는지도 검수하라.
누락·모호가 있으면 수정해서 네 Agora에 반영하고, 최종 영역 목록을 반환하라.`,
  { label: 'census:review', schema: REGIONS_SCHEMA },
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

// 2. Verify — 영역별 주장 검증 (parallel)
phase('Verify')
const found = (
  await parallel(
    regions.map((r) => () =>
      synod(
        r.dir,
        `# 임무: 주장 검증 — 영역 '${r.dir}' (${r.scope})
${DOMAIN}
인벤토리의 모든 문서를 읽고, 문서의 모든 주장(claim)을 코드와 대조해 검증하라.
발견은 다음으로 분류한다: mismatch(코드와 다른 주장) / duplication(같은 정보의 다중 서술 — 다른 영역 문서와의 중복 포함) / dead-doc(대상이 사라진 문서) / restating-comment(코드를 재언하는 주석) / code-defect(문서가 의도를 담고 코드가 결함인 충돌).
각 발견의 근거(문서 위치·코드 위치)를 네 Agora에 기록하라. code-defect는 보고 대상이며 이 워크플로우의 수정 대상이 아니다.`,
        { label: `verify:${r.dir}`, phase: 'Verify', schema: FINDINGS_SCHEMA },
      ),
    ),
  )
).filter(Boolean)

const totalFindings = found.reduce((n, x) => n + (x.findings?.length ?? 0), 0)
if (totalFindings === 0) return { status: 'no-findings', agoraPath }
log(`${totalFindings} findings across ${found.length} regions`)

// 3. Deliberate — 비판·반박·합의 (barriers: 각 단계가 이전 단계 전체 산출물을 요구)
phase('Deliberate')
const names = regions.map((r) => r.dir)

if (regions.length > 1) {
  // 3.1 비판: 다른 영역의 발견을 검토, 비평은 자기 Agora에 기록
  await parallel(
    regions.map((r) => () =>
      synod(
        r.dir,
        `# 임무: 비판 (회의 1/3)
너는 영역 '${r.dir}'의 변호인이자 다른 영역의 비판자다.
다른 영역들(${names.filter((n) => n !== r.dir).join(', ')})의 Agora에 기록된 발견을 비판적으로 검토하라 —
문서가 실제로는 옳은 오검출을 지목하고, 영역 경계에 걸쳐 놓친 중복·불일치를 찾아라.
각 비평을 **네 Agora**에 기록하라 (누구의 어떤 발견에 대한 비평인지 명시).`,
        { label: `critique:${r.dir}`, phase: 'Deliberate' },
      ),
    ),
  )

  // 3.2 반박: 자기 발견에 달린 비평을 찾아 수용/반박
  await parallel(
    regions.map((r) => () =>
      synod(
        r.dir,
        `# 임무: 반박 (회의 2/3)
다른 영역들의 Agora에서 너의 발견을 겨냥한 비평을 모두 찾아 검토하고,
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
모든 영역의 발견·비평·반박(${agoraPath}/ 전체)을 종합해서 **합의된 발견 리스트**를
${agoraPath}/cartographer/consensus.md 에 작성하라.
교차검증을 통과한, 실재하며 정합 가치가 있는 발견만 남겨라. code-defect 발견은 별도 섹션으로 모아라.`,
  { label: 'consensus', phase: 'Deliberate', schema: CONSENSUS_SCHEMA },
)
if (!consensus?.count) return { status: 'no-consensus', agoraPath }
log(`consensus: ${consensus.count} findings`)

// 4. Plan — 정합 계획 수립
phase('Plan')
const planned = await synod(
  'doc-manager',
  `# 임무: 정합 계획 수립
합의된 발견(${agoraPath}/cartographer/consensus.md)을 파악한 뒤 문서 정합 계획을 작성하라.
${PRINCIPLE}
- 전체 작업을 최대한 크게 쪼개서 계획 갯수를 적게 유지하라.
## 계획 형식
각 계획은 self-contained 마크다운으로 ${plansDir}/{순번}-{kebab-name}/proposal.md 에 작성한다.
proposal.md는 다음을 포함한다: 대상 발견 / 변경 내용 / ROI 근거 / 예상 side-effect / 영향 범위.
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
if (!plans.length) return { status: 'no-plans', findings: consensus.count, agoraPath }
log(`${plans.length} alignment plans`)

// 5. Review — 계획별 검수 (parallel)
phase('Review')
await parallel(
  plans.map((p) => () =>
    synod(
      `review-${p.name}`,
      `# 임무: 정합 계획 검수 — '${p.name}'
합의된 발견(${agoraPath}/cartographer/consensus.md)과 대상 계획(${p.proposal})을 읽어라.
- 계획의 새 텍스트가 그 자체로 코드와 어긋나는 새 주장을 만들지 않는지 검증하라.
- 계획이 irreducible한지 — 더 삭제·축약할 수 있는지 — 고찰하라.
- 계획이 고려하지 못한 side-effect를 탐색하라.
이슈나 개선점을 네 Agora(review.md)에 기록하라.`,
      { label: `review:${p.label}`, phase: 'Review' },
    ),
  ),
)

// 6. Refine — 검수 반영 + 실행 순서 확정
phase('Refine')
const refined = await synod(
  'doc-manager',
  `# 임무: 정합 계획 개선 + 실행 순서 확정
${agoraPath}/ 전체(계획들과 review-* 검수 기록)를 읽어 컨텍스트를 복원하라.
검수 내용을 기반으로 각 계획을 개선하라. 판단 기준은 정합 원칙이다.
${PRINCIPLE}
개선이 끝나면 계획들의 **실행 순서**를 확정해서 ${agoraPath}/doc-manager/execution-order.md 에 기록하고,
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
    `# 임무: 정합 수행 — '${name}'
계획(${p.proposal})을 읽고 그대로 구현하라. **실행되지 않는 텍스트만 수정한다.**
주석·docstring 수정으로 코드 파일을 건드렸다면 프로젝트의 테스트 스위트로 behavior가 불변임을 확인하라.
변경 요약과 확인 결과를 네 Agora에 기록하고 반환하라.`,
    { label: `apply:${p.label}`, phase: 'Apply', schema: APPLY_SCHEMA },
  )
  applied.push({ name, status: res?.status ?? 'unknown', testsPassed: res?.testsPassed ?? null })
  log(`applied ${applied.length}/${order.length}: ${name}`)
}

const finalReview = await synod(
  'doc-manager',
  `# 임무: 최종 검수
적용된 모든 계획(${agoraPath}/apply-* 기록)과 실제 변경된 문서를 종합 검수하라.
변경된 모든 문서를 코드와 재대조해 남은 불일치가 없는지, 실행되는 behavior가 불변인지 확인하라.
consensus.md의 code-defect 섹션을 codeFindings 로 수집해 함께 반환하라.`,
  { label: 'final-review', phase: 'Apply', schema: FINAL_SCHEMA },
)

return {
  status: 'done',
  agoraPath,
  regions: regions.length,
  findings: consensus.count,
  consensusTitles: consensus.titles ?? [],
  plans: plans.length,
  applied,
  finalReview,
}
