## 1. Host-level trust 문구

- [x] 1.1 site·README 한·영의 bypassPermissions 설명을 host-level scope로 교정 —
      mitigation 처방 없이 정의적 사실만

## 2. Link binding

- [x] 2.1 site-truth-check.yml에 `canon-links` job — 표면 3종의 blob·tree link 전수를
      tree 경로 존재로 검증 (offline·결정론)
- [x] 2.2 red 실증 — 존재하지 않는 경로 link를 임시 주입해 fail 확인 후 원복

## 3. 재발행

- [x] 3.1 root pyproject 0.1.4

## 실측 기록

- 2.2: checker 현행 tree GREEN — 표면 3종에서 repo-내부 link 대상 15개 전부 존재.
  사본에서 MEMORY.md link를 MEMORY-RENAMED.md로 변조 → RED. canon rename이 관문 link
  수정 전까지 PR을 막는다.
