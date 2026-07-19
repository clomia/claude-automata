## Context

ploop의 loop 상태는 hook이 단독 소유하고(설계 결정 3) main은 지난 round를 잊는다 — 그러나
소유자 대상 완전 기록(loop.log)·anchor 원문·advice history·round slice가 이미 디스크에
외부화되어 있다. docent는 이 기록 표면의 세 번째 소비자다(hook은 로그로, advisor는 입력으로,
docent는 사용자 질의 응답으로 읽는다). ploop의 표면은 셋으로 격리된다: define(사전 대화)·
loop(작업 본선)·docent(질의). 격리의 근거는 두 갈래로 수렴한다 — context 순수성(질의가 main에
닿으면 오염이 narration·loop.log까지 전파)과 보안(docent가 오염되어도 loop는 불가침).

기억 system 관점의 자리: 장기기억의 회상이 grep이듯(MEMORY.md) 작업기억의 회상은 docent다 —
저장소도 쓰기 경로도 더하지 않는 순수 read 표면이라 응고 관문·망각 등 기억 model의 불변식과
무접촉이고, "인간은 관찰자"라는 생태계 전제를 작업기억 단계까지 완결한다.

## Goals / Non-Goals

**Goals:**

- docent 표면을 loop 기계와 접점 0으로 추가한다: hook 0개, loop 상태 쓰기 0개.
- 결정론(경로·session 열거)은 resolver 코드로, 의미론(교리)은 skill 본문으로, 프로젝트 맥락은
  같은 directory의 CLAUDE.md 상속으로 분담한다.

**Non-Goals:**

- 음성 처리 — client(edge)가 이미 소유한 표면이다(받아쓰기·읽어주기). server 측 STT/TTS는 기기
  의존을 배포 표면에 박으므로 기각.
- channel 연결 — 단일 소유자의 transport는 remote-control이 우월하다(AskUserQuestion·권한
  승인·계정 인증). channel은 다수 인간 감독·기계 이벤트 주입이 필요해질 때의 별도 change다.
- docent→loop 쓰기 경로(escalation) — 개입은 인간 전용 경로(loop session 직접 지시,
  `/ploop:off`)로 남는다.
- advisor loop 자체의 변경 없음.

## Decisions

1. **표면 격리 = hook 0·쓰기 0.** docent는 hooks.json에 등록하지 않는다. expansion hook으로
   게이트하는 대안은 loop 기계에 표면을 추가해 격리를 깬다 — 기각. skill이 곧 표면의 전부다.
2. **Session 식별은 주입이 아니라 resolver 해석.** anchor·session id를 skill 인자로 받는 대안은
   새 launch(= 새 loop)에서 낡은 subject를 가리키게 된다. resolver 목록은 machine 전역(다른
   directory·지난 loop 포함)이고 docent의 subject는 이 directory의 loop 하나다 — transcript
   project dir ↔ cwd 대응으로 고르고, snapshot이 낡으면 재실행해 subject를 재획득한다. 내용의
   신선도는 별개 책임으로 응답 규율의 fresh read가 소유한다.
3. **Data dir 해석 체인 flag→env→glob.** skill 본문은 `--data-dir "${CLAUDE_PLUGIN_DATA}"`를
   넘긴다 — placeholder의 skill 본문 치환은 공식 문서(plugins-reference: "Skill and agent
   content — anywhere the placeholder appears")이고, 최종 fallback layout
   `~/.claude/plugins/data/{id}/`도 공식 문서다(persistent data directory 절 + 이 machine 실측
   2026-07-19 일치). 관측 기반 의존으로 남는 것은 transcript 쪽이다:
   `~/.claude/projects/*/{session}.jsonl` 위치와 `{session}/subagents/agent-*.jsonl` worker
   기록은 미문서 layout(실측 2026-07-19, apply 중 audit-harness-deps로 판정)이라
   audit-harness-deps의 검사 대상으로 남기고, 표류 시 "not found"/"(absent)"로 degrade한다.
4. **`disable-model-invocation: true`.** docent 교리는 session의 정체성을 다시 쓴다. loop
   main이 model-invoke하면 orchestrator 정체성과 충돌하므로 launch·off·on과 같은 explicit-only
   클래스다 (define 둘만 model-invocable로 남는다 — 어느 session에서도 안전한 순수 대화라서).
5. **Resolver 출력은 English.** 코드 발신 레인(레포 언어 정책). 교리 산문은 한국어 기반이다.
6. **Worker transcript 노출.** resolver가 project dir를 출력해 `agent-*.jsonl` 접근을 연다 —
   advisor에 비가시인 worker 내부(수용한 한계)를 docent는 사후 판독할 수 있다. 신뢰 모델은
   불변이다: 산출의 판정은 관문(독립 검증·CI)이 소유하고 docent는 설명만 한다.
7. **생태계·기억 정본 비등재.** docent는 접면 0의 add-on이라 root ARCHITECTURE(접면·횡단 정책
   소유)와 MEMORY.md(기억 기계 소유)에 등장하지 않는다 — "작업기억의 소유자 회상"이라는 역할
   서술은 아무 규약도 구속하지 않는 결과 없는 사실이라 정본 등재 기준에 미달한다(넣었다가 이
   기준으로 뺐다). 등재는 ploop 정본과 README까지다 — 생태계 정본의 침묵이 접점 0 격리의
   표현이다.
8. **교리의 층 분리.** 정적 의미론(파일이 무엇인지·신선도 특성·loop 기제 최소 프라이머)은 skill
   본문, 동적 식별(경로·phase·round)은 resolver, 프로젝트 맥락은 CLAUDE.md 상속. 응답 규율:
   매 질의 fresh read(장수 session의 stale 답변이 주 실패 모드), round 인용, 관측/추론 구분,
   기록 부재의 명시. MEMORY.md 전문 주입은 하지 않는다 — standalone ploop은 기억 도메인을
   모른 채 남는다는 기존 규율의 연장. 개입의 인간 경로 리다이렉트도 교리에서 생략한다(검수 중
   확정) — 경계의 "일절 금지"가 거부를 나르고, 안내처(`/ploop:off`·loop session)는 docent
   session에 ambient한 skill 목록에서 유도된다. 사용자 대면 안내는 README가 나른다.

## Risks / Trade-offs

- [플러그인 data dir 패턴 표류] → env-우선 체인이 1차 방어, 관측 의존 기록이 2차(주기 검사).
- [docent의 오귀속 — 기록 기반 추론의 한계] → 교리가 관측/추론 구분과 인용을 강제. compaction
  이후에는 main도 그 기억이 없다 — 기록이 최선의 증인이라는 전제는 advisor loop와 공유한다.
- [loop.log 한 정지 지연] → 교리가 신선도 특성을 명시하고 round.jsonl·transcript tail을 실황
  경로로 안내한다.
- [transcript glob 다중 매치] → session id는 UUID라 실질 유일. 다중 매치 시 전부 출력한다.
- [transcript·subagents layout 표류 — 미문서 관측 의존] → "not found"/"(absent)" degrade +
  audit-harness-deps 주기 검출. 전환 경로 기록: loop hook은 매 정지 공식 입력 `transcript_path`를
  받으므로 workspace에 영속화하면 glob 의존이 공식 입력 의존으로 바뀐다 — 현재는 loop
  불변(접점 0)을 우선해 미채택.
- [resolver 목록 무상한 성장 — 지난 session GC 없음] → 수용한 한계로 기록(ploop 정본),
  windowing은 관측 후 별도 작업(advice-history 선례와 동일 처방).
