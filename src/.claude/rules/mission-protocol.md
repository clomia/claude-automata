# Mission 실행 프로토콜

## 미션 수락
1. state/missions.json에서 가장 높은 우선순위의 pending 미션을 선택
2. status를 "in_progress"로 변경
3. started_at 타임스탬프 기록

## 미션 실행
1. description과 success_criteria를 정확히 읽는다
2. success_criteria를 하나씩 달성한다
3. 달성 불가능한 criteria가 있으면 blocker를 기록한다
4. 모든 작업에 대해 테스트를 작성하고 실행한다

## 미션 완료
1. 모든 success_criteria 달성을 확인
2. status를 "completed"로 변경
3. completed_at 타임스탬프 기록
4. result_summary 필드에 결과 요약 기록

## 미션 실패
1. 복구할 수 없는 문제가 발생하면 status를 "failed"로 변경
2. result_summary 필드에 원인 기록
3. state/friction.json에 마찰 기록

## Blocker 처리
1. state/requests.json에 Owner 요청 생성
2. 현재 미션에 blocker 추가
3. status를 "blocked"로 변경
4. 다른 pending 미션으로 전환
