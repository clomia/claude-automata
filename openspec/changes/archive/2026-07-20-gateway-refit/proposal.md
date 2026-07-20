## Why

소유자 지시 4건: (1) version-up-alert는 claude-automata 이론(기억 구조)에 기반하지 않는
add-on이므로 방문자 표면(README·사이트)에서 생략 — 독자의 불필요한 인지부하 제거.
(2) license를 "재가공·재배포 시 claude-automata 기반임을 명시"하는 것으로 변경하고,
unaffiliated 고지를 제거하며, "claude-automata는 claude-automata로 개발된다"를 재귀적
자기개선 문구로 승격. (3) 사이트의 한국어 정본 SOURCE link 제거 — repo를 열지 않아도
사이트만으로 이해가 완결되어야 한다. (4) 카피라이팅 조사·검토·개선.

## What Changes

- **License**: MIT → **Apache-2.0 + NOTICE**. 근거 — 표준 OSS license 중 유일하게
  attribution 전파 기제가 내장(§4(d): 재배포·파생물은 NOTICE의 attribution을 유지해야
  하고, §4(b): 변경 사실 고지). CC BY는 code에 부적합(CC 공식 권고), BSD-4(광고 조항)는
  폐기·GPL 비호환, custom license는 도입 마찰과 tooling(badge·GitHub 감지·PyPI) 파손.
  경계 명시: 저작권 license는 표현의 복제·재가공을 결속할 뿐 "영감(inspiration)"까지는
  법적으로 결속 불가 — NOTICE는 실제 재사용 전부를 결속한다.
- **Unaffiliated 고지 제거** (소유자 override — gateway-v2까지의 요구를 폐기): titleblock
  STATUS field, footer 문단, og/banner head 배지, README footer 문구, meta description 꼬리.
- **재귀적 자기개선 copy 승격**: footer lead·og/banner head를 "모든 기여가 이 환경을
  돌리는 Claude Code agent의 작성"이라는 검증 가능한 사실로 교체.
- **version-up-alert 생략**: README 표 행(3행으로), 사이트 §04 module card(3종으로),
  "plugin 4종" 계수 표현 제거. 내부 정본·marketplace metadata는 불변(기능 표면).
- **SOURCE 행 제거**: §04의 .canon-link 4행(en·ko) + 관련 CSS. page의 repo link들은
  전부 repo root 한 곳으로만 수렴.
- **카피라이팅 pass** (Ogilvy 원칙 조사 기반 — headline 지배, 구체성>수사, 문장당 benefit):
  §05 lede의 engineer-speak 완화, refine 소요시간 구체화(3–12h), thesis 압축.
- root 0.1.6 (README 재발행), spec delta는 R3를 REMOVED+ADDED로 재작성.

## Capabilities

### New Capabilities

<!-- 없음 -->

### Modified Capabilities

- `landing-page`: "Site 내용 계약"을 "Site 서사 계약"으로 재작성(REMOVED+ADDED) —
  plugin 소개 3종, module 정본 link 금지, unaffiliated 요구 폐기, 자기개발 표기 SHALL,
  나머지 결속(init 공개·image 쌍·내부 link 존재·반응형·/ko/·정본 비복제)은 유지.

## Impact

- `LICENSE`(교체)·`NOTICE`(신규)·`pyproject.toml`(license·0.1.6)
- `plugins/*/.claude-plugin/plugin.json`·`plugins/*/pyproject.toml` — license field 이관 + patch bump 4종
- `README.md`·`README.ko.md`, `site/index.html`·`site/ko/index.html`·`site/style.css`
- `site/assets/og-card.html`·`og.png`·`banner-card.html`·`banner.png` (쌍 재생성)
- `openspec/specs/landing-page/spec.md` (archive 시 sync)
