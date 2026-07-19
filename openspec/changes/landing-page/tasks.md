## 1. Landing page

- [x] 1.1 시각 방향 개발 (frontend-design skill) — 정밀 기계 인상 축, 기억 시각화 concept 확정
      (확정: document-of-record register — 제도용지·ink·copper→verdigris 산화 palette,
      순수 CSS 9s choreography, JS 0)
- [x] 1.2 `site/` 작성 — 단일 English page: hero + 기억 system 시각화(inline SVG, JS 무의존
      rendering), plugin 4종 소개+정본 link, getting-started(init 실동작 공개), unaffiliated
      고지, viewport meta + 소형 화면 대응
- [x] 1.3 정적 무의존 serve 실측 — build 없이 local static serve로 완전 rendering 확인
      (python http.server + headless Chrome 1440·390 viewport 실측)

## 2. 배포

- [x] 2.1 `.github/workflows/pages.yml` 작성 — main push(site/·workflow path filter) +
      workflow_dispatch, 공식 Pages actions
- [x] 2.2 GitHub Pages 활성화 — `gh api`로 `build_type=workflow`; 권한 차단 시 지점 기록
      (성공 — https://clomia.github.io/claude-automata/ 등록, 차단 없음)
- [x] 2.3 branch ref dispatch로 live 배포 시도 — environment policy 차단 시 조정, 불가 시
      merge 직후 검증으로 이월을 기록
      (실측: GitHub는 default branch에 없는 workflow의 dispatch를 거부(HTTP 404) —
      merge push가 site/** path filter로 자동 배포하므로 live 검증은 merge 직후 수행)

## 3. README 관문화

- [x] 3.1 README.ko.md 재작성 — 정체 한 줄 + plugin 인벤토리 + init 단일 경로(실동작 공개) +
      사이트 link, plugin 섹션 h2, Install·Update 블록·marketplace 단독 안내 제거
- [x] 3.2 README.md 번역 정합 (translate 규율 — 의미 무손실 재검토 포함)
- [x] 3.3 root pyproject version 0.1.1

## 4. 검증

- [x] 4.1 fresh-context 재구성 probe — 사전 맥락 0 agent가 (a) 사이트만, (b) README만 보고
      "무엇/왜/어떻게"를 재구성, ground-truth 사실 목록과 대조
      (양쪽 모두 정확 재구성. 지적 3건 — Claude Code 전제 미명시·bypassPermissions 의미
      한 문장 부재·README 문제 서술 부재 — 즉시 수리 반영)
- [x] 4.2 claim audit — 사이트·README의 전 사실 주장을 코드·정본과 대조 (과장=결함)
      (77건 판정: 70 OK · 5 EXAGGERATED · 2 UNVERIFIED(live URL, merge 후 해소) · 0 WRONG.
      EXAGGERATED 전건 수리: README 쌍의 "never loses context"→anchor 생존+기록 파일 정확
      서술, recap 조건 명시, site aria-label·reject pulse를 "gate 거부"에서 "작업기억 폐기"로)
- [x] 4.3 반응형 실측 — headless Chrome으로 desktop 1440·mobile 390 viewport 실측
      (schematic 양방향 성립, animation은 virtual-time으로 중간 시점 실측)
