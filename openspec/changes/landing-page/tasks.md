## 1. Landing page

- [ ] 1.1 시각 방향 개발 (frontend-design skill) — 정밀 기계 인상 축, 기억 시각화 concept 확정
- [ ] 1.2 `site/` 작성 — 단일 English page: hero + 기억 system 시각화(inline SVG, JS 무의존
      rendering), plugin 4종 소개+정본 link, getting-started(init 실동작 공개), unaffiliated
      고지, viewport meta + 소형 화면 대응
- [ ] 1.3 정적 무의존 serve 실측 — build 없이 local static serve로 완전 rendering 확인

## 2. 배포

- [ ] 2.1 `.github/workflows/pages.yml` 작성 — main push(site/·workflow path filter) +
      workflow_dispatch, 공식 Pages actions
- [ ] 2.2 GitHub Pages 활성화 — `gh api`로 `build_type=workflow`; 권한 차단 시 지점 기록
- [ ] 2.3 branch ref dispatch로 live 배포 시도 — environment policy 차단 시 조정, 불가 시
      merge 직후 검증으로 이월을 기록

## 3. README 관문화

- [ ] 3.1 README.ko.md 재작성 — 정체 한 줄 + plugin 인벤토리 + init 단일 경로(실동작 공개) +
      사이트 link, plugin 섹션 h2, Install·Update 블록·marketplace 단독 안내 제거
- [ ] 3.2 README.md 번역 정합 (translate 규율 — 의미 무손실 재검토 포함)
- [ ] 3.3 root pyproject version 0.1.1

## 4. 검증

- [ ] 4.1 fresh-context 재구성 probe — 사전 맥락 0 agent가 (a) 사이트만, (b) README만 보고
      "무엇/왜/어떻게"를 재구성, ground-truth 사실 목록과 대조
- [ ] 4.2 claim audit — 사이트·README의 전 사실 주장을 코드·정본과 대조 (과장=결함)
- [ ] 4.3 반응형 실측 — headless browser 가용 시 desktop·mobile viewport 실측, 불가 시
      media query·layout 감사로 대체하고 그 사실을 기록
