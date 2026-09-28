# unattended-runs — design

## Context

See proposal.md — Why; 요구는 specs/unattended-runs. 실측은
`docs/research/unattended-dialogs-2026.md`(2.1.283). 제약: plugin은 settings를 쓰지 않는다(ploop 결정
12, plugin `settings.json`은 `agent`·`subagentStatusLine`만 적용). plugin 상태는 자기
`CLAUDE_PLUGIN_DATA`에만 둔다(root 접면 계약 — project-unit 격리). 선례: lora worker의 hook 네 개
(PreToolUse shell guard·PermissionRequest catch-all·Elicitation decline·Notification stall log)와
`EnterPlanMode` deny·AskUserQuestion timeout.

## Goals / Non-Goals

**Goals:** 무인 run 중 사람을 기다리는 dialog가 0이다 — 답할 수 있는 것은 즉시 답하고, 답할 수 없는
것은 기록된다. lora의 해당 장치가 plugin으로 대체돼 하류에서 걷힐 수 있다.

**Non-Goals:** harness의 wake 억제(clomia/claude-automata #146) — session 밖 기계(lora daemon)의 몫.
heartbeat sleeper 누적 — 별개 결함. dialog 기한·usage-limit 설정의 provision — user scope라 plugin이
줄 수 없고, 기본값이 이미 무인에 맞다(`autoContinueAtUsageLimit` true, `dialogExpiry` 5m).

## Decisions

1. **무인의 범위는 run의 armed 구간이 아니라 run을 시작한 session 전체다.** armed 구간만 지키면
   `/ploop:off` 뒤의 turn이 무방비다 — lora의 정지는 off 뒤 shutdown prompt로 무인 turn을 하나 더
   돌리고(릴리스·push·maintain), 그 turn의 권한 요청은 정지 ceiling까지 멈춘다. 사람이 개입할 일은
   바닐라 session의 몫이라는 전제(owner)가 경계를 session으로 정한다. ploop은 "launch한 적 있다"를
   이미 가진 사실 — `{session}_anchor.md` 존재(launch만 쓰고 아무도 지우지 않는다) — 로 읽는다: 같은
   사실의 두 번째 marker는 두지 않는다. refine은 그런 사실이 없어 발사 시점에
   `{session}_unattended`를 쓴다. 기각: armed-only(위 공백), 종료 시 해제(해제 시점이 곧 무인
   turn이다).
2. **응답은 세 갈래 — PermissionRequest deny가 그물이다.** 실측으로 critical-path 삭제·
   `AskUserQuestion`·`ExitPlanMode`가 모두 PermissionRequest로 온다. 그래서 tool별 PreToolUse
   guard는 두지 않는다 — 예외는 `EnterPlanMode` 하나: 진입은 hook 결정 없이 통과하고 이탈만 승인을
   요구해, 이탈을 deny하면 plan mode에 갇힌다. Elicitation은 decline. 어떤 요청도 allow하지 않는다 —
   승인은 사람의 것이고, 무인 계약은 기다림만 없앤다. 사유는 tool에 맞춘다: 질문 → 스스로 결정·가정
   명시·계속, 그 밖 → 같은 형태 재시도 금지·승인 불요로 고치거나 미완으로 두고 계속 + 삭제의 절대 경로
   규칙(에이전트는 critical-path 판정 기준을 모른다).
3. **lora의 shell pre-guard는 옮기지 않는다.** 그것은 harness의 critical-path 판정을 shell로 재구현한
   것이다 — root canon이 부채로 규정하는 형태 열거다. harness가 판정해 PermissionRequest로 보내면 같은
   deny가 즉시 난다(실측). 잃는 것은 조금 이른 deny 시점뿐이다.
4. **mode 검사는 hook 입력의 `permission_mode`로 한다(effective).** 결정 18의 "effective 우선"과 같다 —
   settings 선언은 project scope에서 무시되고 CLI flag를 못 본다. bypass만 허용한다(owner): auto는
   classifier 연속 3·누적 20 차단 뒤 prompting으로 돌아가 그물이 모든 행동을 deny하는 불능 session을
   만든다. ploop은 arm하는 두 문(launch·on)에서, refine은 Workflow PreToolUse에서 — refine skill은
   사용자 입력과 model 호출 두 경로로 들어오지만 둘 다 Workflow 호출로 모이고, 재개도 그렇다(실측
   `scriptPath`). 호출이 refine의 것인지는 그것이 가리키는 refine 자료로 안다: bootstrap이 찍는
   `scriptPath`, 또는 args가 싣는 `principlesPath`. live 시험에서 `scriptPath`가 도구 검증에 걸리자
   모델이 같은 run을 inline `script`로 다시 넘기려 했다 — `scriptPath`만 보면 그 run은 무인 표시와 mode
   검사를 건너뛴다. args의 `principlesPath`는 inline 전달·재개(같은 args)에도 남는다.
5. **plugin마다 자기 guard.** 공유 plugin·공유 marker는 기각: plugin 간 상태 경로는 plugin id(마켓
   이름 포함)에 묶이고, session scratchpad는 system temp라 며칠짜리 run의 marker를 못 버틴다. 계약
   문장은 root ARCHITECTURE에 한 번 두고, 각 plugin은 자기 범위 판정과 사유 문구를 소유한다 — 사유는
   run의 맥락이 다르다(loop main vs Agora worker). 형태 일관은 plugin runner의 선례처럼 repo 수준
   test가 결속한다.
6. **멈춤 기록은 ploop만, loop.log에.** Notification `permission_prompt`·`elicitation_dialog`·
   `elicitation_url_dialog`·`quota_auto_resume_stale`·`quota_auto_resume_disabled`만 멈춤이다
   (`idle_prompt`는 정상 idle). loop.log는 advisor·docent가 읽는 유일한 기록이라 `[[ Stall - ts ]]`가
   세 번째 entry 형이 된다 — 새 파일은 읽는 자가 없다. refine은 기록할 자리가 없고(Agora 경로는 hook이
   모른다) workflow 화면이 멈춘 agent를 보인다.
7. **init은 mode를 쓰지 않고, 무시되는 값을 걷는다.** project scope의 `bypassPermissions`·`auto`는
   무효이고 user scope mode를 가려 Manual을 만든다(2.1.283 번들: "only policy/user/flag settings may
   grant bypass mode"). 이전 init이 쓴 값을 제거해 기존 도입처도 수렴한다. 다른 값(`plan` 등)은 사용자
   선택이라 둔다.

## Risks / Trade-offs

- [run 뒤 같은 session으로 돌아온 사람의 질문·승인 요청도 deny] → 전제대로 수용: 사람 작업은 새
  session. deny는 안전 방향이다.
- [run 없는 session에서도 permission prompt마다 plugin hook이 uv로 한 번 뜬다] → 첫 판정(marker 부재)에서
  즉시 exit 0. prompt가 드문 bypass·auto에서 무시할 수준.
- [harness가 새 dialog를 PermissionRequest 밖에 둔다] → Notification 멈춤 기록이 드러내고, 대응은 다음
  change.
- [hook 실패(uv 부재 등)] → 결정 없음 = 평소 dialog. launch·arm은 uv 없이 거부되므로 무인 run은 시작
  자체가 안 된다.

## Migration Plan

도입처는 `uvx claude-automata@latest init` 재실행으로 무효 mode가 걷힌다. 운영자는 무인 run용 session을
`claude --permission-mode bypassPermissions`로 연다(또는 user settings). lora는 이 version을 pin한 뒤
중복 장치를 걷는다(follow-up change).
