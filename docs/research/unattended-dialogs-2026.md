# 무인 session의 dialog — hook이 답할 수 있는 것과 없는 것

- Date: 2026-09-28
- Question: bypass 모드 무인 session에서 사람을 기다리게 만드는 dialog를 plugin hook이 전부 답할 수
  있는가 — (1) slash command 확장 hook이 session의 effective permission mode를 받는가, (2)
  critical-path 삭제가 bypass에서 PermissionRequest를 타고 deny가 즉시 적용되는가, (3) subagent·
  workflow agent 안의 요청이 main session의 `session_id`를 싣는가, (4) Workflow 호출 입력에
  `scriptPath`가 실리는가, (5) `AskUserQuestion`·plan mode 도구는 어느 hook으로 오는가.
- Method: Claude Code 2.1.283(Sonnet 5, Claude Max) 대화형 session을 사설 tmux socket의 scratch
  project(system temp 아래)에서 `claude --permission-mode bypassPermissions --settings <overlay>`로
  띄웠다. overlay는 설치된 plugin 전부를 끄고, UserPromptExpansion·PreToolUse(`*`)·
  PermissionRequest·Notification·SubagentStart에 기록 hook 하나를 걸었다 — 입력의 event·
  `session_id`·`permission_mode`·`agent_id`·`agent_type`·tool·tool_input을 JSONL로 남기고,
  PermissionRequest는 `decision: deny`로 답한다. plugin registry는 건드리지 않았다(`--plugin-dir`·
  install 없음). 삭제 시험은 존재하지 않는 최상위 경로의 `rmdir`로 했다 — 실행돼도 "No such file"로
  끝난다. 모델은 `/tmp`·`.` 대상 `rmdir`를 스스로 거부해 harness까지 가지 않았으므로 새 context
  (`/clear`)에서 존재하지 않는 경로로 바꿨다.

## 발견

- ✅ **UserPromptExpansion 입력은 `permission_mode`를 싣는다** — 프로젝트 skill `/probe` 확장에서
  `"mode":"bypassPermissions"`. launch 시점 mode 검사를 settings 선언이 아니라 effective 값으로 할 수
  있다.
- ✅ **bypass에서 critical-path 삭제는 PermissionRequest를 타고, hook의 deny는 dialog 없이 즉시
  적용된다** — `rmdir /ua-probe-nonexistent`: PreToolUse → PermissionRequest(같은 초) → 화면
  `Denied by PermissionRequest hook`, 모델은 deny `message`를 도구 결과로 그대로 받았다. 2.1.281의
  2분 countdown dialog는 뜨지 않았고 Notification도 fire하지 않았다.
- ✅ **subagent 안의 요청은 main의 `session_id`를 싣는다** — foreground를 요청했지만 background로
  돈 general-purpose subagent의 PermissionRequest: `session_id` = main, `agent_id`·`agent_type`
  (`general-purpose`)이 더해진다. deny는 subagent에서도 dialog 없이 적용됐다.
- ✅ **Workflow 호출 입력은 `tool_input.scriptPath`를 싣고, workflow agent의 요청도 main의
  `session_id`를 싣는다** — `agentType` 없이 띄운 agent의 `agent_type`은 `workflow-subagent`.
- ✅ **`AskUserQuestion`의 질문 창은 PermissionRequest를 탄다** — PreToolUse에서 막지 않으면
  PermissionRequest가 fire했고, deny로 질문 창 없이 사유가 전달됐다. PreToolUse deny도 창 없이
  사유를 전달한다(`PreToolUse:AskUserQuestion hook error: …`).
- ✅ **plan mode는 함정이다** — `EnterPlanMode`는 bypass에서 hook 결정 없이 통과해 session이
  `plan` mode로 들어가고(이후 입력의 `permission_mode`가 `plan`), `ExitPlanMode`는 PermissionRequest를
  탄다. 그것을 deny하면 session은 plan mode에 남는다 — tools-reference: "permission prompts,
  including plan approval, never auto-resolve on idle". 무인 session은 진입 자체를 막아야 한다.
- ✅ **idle Notification은 멈춤 신호가 아니다** — 응답 후 약 60초에 `idle_prompt`("Claude is
  waiting for your input")가 fire했다. 멈춤 기록의 matcher에서 빼야 한다.

## 문서로 확인한 경계 (hooks·tools-reference·settings-reference, 2026-09-28)

- PermissionRequest는 sandbox command의 network 요청 prompt에는 돌지 않는다 — Notification
  `permission_prompt`만 그 대기를 알린다.
- Notification `quota_auto_resume_stale`(절전 30분 초과 뒤 Enter 대기)·`quota_auto_resume_disabled`
  (자동 재개 포기)는 사람 없이는 풀리지 않는 usage-limit 대기다.
- `autoContinueAtUsageLimit`은 user·managed scope 전용이고 기본 `true`다 — project·local 파일이 이
  key를 가지면(user·managed가 비어 있을 때) 기능이 꺼진다. plugin·init은 쓰지 않는다.
- plugin `settings.json`은 `agent`·`subagentStatusLine`만 적용된다 — dialog 기한류 설정은 plugin이
  줄 수 없다.
- background subagent의 permission prompt는 2.1.186부터 main session에 뜬다(그 전엔 자동 거부).

## Live 검증 — 구현된 guard (같은 날, 같은 버전)

작업 트리의 ploop·refine을 `--plugin-dir`로 싣고(설치본을 덮는다 — debug log "from --plugin-dir
overrides installed version") scratch project에서 대화형 session을 띄웠다. overlay로 설치본
`ploop@claude-automata`를 끄면 같은 이름의 `--plugin-dir` 사본도 꺼지고, 의존 plugin
(`version-up-alert`)을 끄면 dependency 미충족으로 둘 다 로드되지 않는다 — 켠 채로 둔다.

- ✅ auto mode의 `/ploop:launch`는 mode 한 줄만 사유로 차단됐다(나머지 전제 충족).
- ✅ bypass session에서 launch한 loop 안: `rmdir /ua-live-nonexistent` → ploop의 삭제 사유,
  `AskUserQuestion` → 질문 사유, `EnterPlanMode` → PreToolUse 사전 거부(mode는 bypass 유지) — 모두
  dialog 없이.
- ✅ `/ploop:off`로 active marker가 사라진 뒤의 같은 삭제도 거부됐다 — 무인은 session 단위다.
- 🔶 auto session의 `/refine:docs`에서 `scriptPath`(작업 디렉토리 밖)가 Workflow 도구의 입력 검증에
  걸리자(PreToolUse 이전이라 hook은 불리지 않는다) 모델이 같은 run을 inline `script`로 다시 넘기려
  했다 — `scriptPath`만으로 run을 식별하면 무인 표시와 mode 검사를 건너뛴다. args의
  `principlesPath`가 그 경우와 재개에도 남는다(설계 결정 4). 이 시도는 발사 전에 중단했다.

## 결론

무인 session의 dialog는 hook 세 갈래로 전부 답해진다 — PermissionRequest deny(삭제·ask rule·
질문·plan 승인), `EnterPlanMode` 사전 deny, Elicitation decline. 판정은 `session_id` 하나로 main·
subagent·workflow agent를 덮는다. hook이 답하지 못하는 대기(sandbox network prompt, usage-limit
자동 재개의 포기·절전 대기)는 Notification으로만 관측되므로 기록 대상이다.

재측정: 위 Method의 overlay를 다시 세워 같은 다섯 요청(`/probe`, 존재하지 않는 최상위 경로
`rmdir`, subagent 경유 같은 명령, 한 agent짜리 workflow script, `AskUserQuestion`·`EnterPlanMode`→
`ExitPlanMode`)을 보내고 JSONL의 `session_id`·`permission_mode`·event 순서를 대조한다.
