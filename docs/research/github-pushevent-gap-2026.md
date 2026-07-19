# GitHub squash-merge push의 PushEvent 결락 — post-merge workflow 침묵

- 작성일: 2026-07-20
- 질문: base로의 squash merge push가 push-trigger workflow들을 발화시키지 않을 수 있는가?
  그 경우 post-merge 배포(pages·publish)는 어떻게 복구하는가?
- 방법: landing-page mission 중 연속 3회의 PR squash merge에서 `gh api`로
  workflow run·PushEvent를 실측 (2026-07-19).

## 발견

- ✅ **1회 재현됨**: merge commit `ec2abb9`(PR #39)에서 push-trigger workflow 3종
  (test·pages·publish)이 전부 침묵했다. `gh api .../actions/runs?head_sha=` 결과 0건,
  events feed의 최신 main PushEvent는 직전 merge(`ef1e35f`)에 머묾 — **push event 자체가
  미발생**. GitHub status는 all-operational, workflow 4종 모두 active, commit message에
  skip 지시어 없음.
- ✅ **복구 경로**: workflow 파일이 default branch에 있으므로
  `gh workflow run <wf> --ref main`이 동일 결과를 재현한다 — pages·publish를 dispatch로
  완결했고 산출(사이트 배포·PyPI 발행) 정상.
- ✅ **비재현 관측 2회**: 직전 merge(`ef1e35f`, PR #38)와 직후 merge(`b91e7e4`, PR #40)는
  push-trigger가 정상 발화했다. n=3 중 1회.
- 🔶 판단: GitHub 측 transient event drop으로 보인다. tx close 후의 배포는 push-trigger가
  돌았다고 가정하지 말고 `gh api .../actions/runs?head_sha=<merge-sha>`로 실측하라 —
  0건이면 dispatch가 복구 경로다. (dispatch는 workflow 파일이 default branch에 있어야
  가능하다는 제약도 같은 mission에서 실측 — 첫 배포는 merge 전 dispatch가 불가했다.)
