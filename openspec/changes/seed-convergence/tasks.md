## 1. docs-form-check scan domain (F1)

- [ ] 1.1 plugins/tx/references/memory-check.yml — docs-form-check job에 `fetch-depth: 2`,
  scan set을 "living 전량 + archive는 `git diff --name-only --no-renames --diff-filter=AM
  HEAD^1 HEAD` 유입분"으로 축소, diff 실패 시 exit 1. header 주석을 byte-수렴 계약으로 갱신
- [ ] 1.2 .github/workflows/memory-check.yml — reference와 byte-identical 동기화
- [ ] 1.3 plugins/tx/tests/test_form_check.py — yml에서 heredoc script를 추출해 실제 git
  repo(merge commit)로 검증: 동결 기존 위반 통과 / archive 유입 위반 실패 / living 위반은
  diff 무관 실패 / HEAD^1 부재 loud fail

## 2. seed 수렴 (G1·F4)

- [ ] 2.1 seed.py — `pin_drifted`·`OPENSPEC_PIN_RE` 폐기, `seed_workflow`를 byte 비교로
- [ ] 2.2 seed.py — workflow-on-base probe(`git cat-file -e origin/<base>:...`, base는
  `src.repo.base_branch`), 생성 시 checks rule 조건부 포함 + 유예 보고
- [ ] 2.3 seed.py — present 경로를 상향 수렴으로: ruleset detail에서 checks rule 부재 +
  조건 충족이면 canonical full로 PUT, downgrade 없음. module docstring 재작성
- [ ] 2.4 test_seed.py — pin_drifted 테스트 제거, byte 수렴 lifecycle로 교체, ruleset
  시나리오 추가(유예 생성 / 상향 수렴 / downgrade 없음 / probe 실패 full)

## 3. Canon 이행

- [ ] 3.1 MEMORY.md — scan-domain 문장(전 추적 `.md` → gate-at-entry 의미론)과 경합 창 절의
  up-to-date 강제 서술에 checks rule 조건 반영
- [ ] 3.2 plugins/tx/README.md — The seed 절에 checks rule 유예·수렴 1문장

## 4. Version

- [ ] 4.1 tx 0.12.11 → 0.13.0 (plugin.json + pyproject.toml + uv.lock 재생성)

## 5. Verification

- [ ] 5.1 tx 전체 테스트 통과 + 이 repo에서 새 form-check script 실측(clean) +
  root workflow byte-identity 테스트 green
