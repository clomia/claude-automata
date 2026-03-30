# 자기개선 규칙

## Friction 기록
모든 마찰을 state/friction.json에 기록한다:
- error: 에러 발생
- slow: 예상보다 느린 실행
- repeated_failure: 같은 패턴 반복 실패
- quality: 품질 이슈
- context_loss: 컨텍스트 유실
- stuck: 진행 불가
- owner_intervention: Owner 수동 개입 필요

## 개선 미션 실행 시
1. 수정 전: git tag로 checkpoint 생성
2. 수정 대상 제한 없음: CLAUDE.md, hooks, system/, tui/, config 모두 가능
3. 수정 후: 관련 테스트 실행
4. 테스트 실패 시: checkpoint로 롤백하고 다른 접근법 시도
5. 성공 시: friction.json에서 해당 마찰을 resolved로 표시

## 수정 가능 범위
- CLAUDE.md (이 파일 포함)
- .claude/rules/*.md
- state/strategy.json
- state/config.toml (모든 임계값)
- system/hooks/*.py
- system/*.py
- tui/*.py
