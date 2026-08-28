# Tasks — verify-gate

## 1. Implementer prompts

- [x] 1.1 `skills/apply/SKILL.md` step 4: 자기 판정 기본, behavior를 움직인 delta에 verify,
      change-id alone, pass가 마지막 behavior 변경보다 새로워질 때까지 재소환; description은
      "then judge it"
- [x] 1.2 `skills/close/SKILL.md` verify 불릿: pass newer than last behavior change;
      delta-less 예외 문장 삭제

## 2. Verifier

- [x] 2.1 `agents/verify.md`: description에 소환 조건; 보고 절의 중복 PASS 문장 삭제

## 3. Canon & release

- [x] 3.1 `README.md` apply 절
- [x] 3.2 Version 0.17.2 → 0.18.0 (plugin.json · pyproject.toml · uv.lock)
