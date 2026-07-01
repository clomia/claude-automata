---
name: log
description: 이 세션의 ploop 분석 로그를 읽고 요약한다
disable-model-invocation: true
---

`/ploop:log`

`${CLAUDE_PLUGIN_DATA}/${CLAUDE_SESSION_ID}_loop.log`를 읽으세요.

- 파일이 없으면: `이 세션에서 ploop이 아직 실행되지 않았습니다.`
- 있으면: 기록된 분석 라운드를 간결히 요약하고, 끝에 로그 파일 경로를 덧붙이세요.
