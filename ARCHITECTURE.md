# claude-automata architecture

**claude-automata는 24시간 주도권을 갖는 자율 agent 환경이다.** 사용자는 event type 중
하나이며, loop는 사용자가 제공한 anchor로 정박된다. repository에 기여하는 주체는 전부
Claude Code agent다(설계 전제) — 인간은 목적을 제공하고 관찰할 뿐, 쓰기 경로의 참여자가
아니다. 세 plugin이 하나의 system을
이룬다 — **ploop은 작업기억 기반 장기 loop**(git 미추적, advisor가 메타인지), **tx는 장기기억
기반 정합 mechanism**(응고 gate),
**refine은 환경 청소기**(장기기억·코드·system의 유지보수 주기).

이 문서는 생태계 정본이다 — plugin들이 어떻게 하나로 합성되는지, 그 접면과 횡단 정책만
소유한다. 각 구성요소의 내부는 소유 정본이 담당한다 — 한 사실은 한 곳에만 존재한다.

## 진입점 지도

| 정본 | 소유 |
|---|---|
| [MEMORY.md](MEMORY.md) | 기억 system 전체 — 작업기억/장기기억, 두 표면(spec·docs), 승격 routing, 불변식, OpenSpec seam, docs 표면 규약과 그 운반 |
| [plugins/ploop/ARCHITECTURE.md](plugins/ploop/ARCHITECTURE.md) | advisor loop 설계 결정 전체 (내부 용어 포함) |
| [plugins/tx/README.md](plugins/tx/README.md) | transaction model · base 해석 · guard hook · seed · verify stage |
| plugins/refine/skills/\*/principles.md | 각 정제 workflow의 판단 axiom |
| [openspec/specs/init-cli/spec.md](openspec/specs/init-cli/spec.md) | init CLI — 전제조건 수렴(settings·marketplace·외부 CLI provisioning) 요구사항 |
| [README.ko.md](README.ko.md) / [README.md](README.md) | 관문·사용 (사람 대상, 한·영 쌍) |
| [INSTALL.md](INSTALL.md) | 설치 — installed state 술어 (설치 수행 agent 대상) |

기억 domain 용어(작업기억·장기기억·응고·표면·정본)는 MEMORY.md가, ploop 내부 용어(advisor
loop·main·anchor·advice)는 ploop 정본이 소유한다 — 여기 재정의하지 않는다.

## plugin 접면 계약

- **ploop × tx — Stop hook 동거.** 두 plugin은 조정 코드 없이 같은 Stop event를 hook한다.
  tx git-sync는 `stop_hook_active`(hook 유발 연속 정지)에서 조기 반환하고 ploop은 그 field를 보지
  않으므로, ploop이 정지를 막아 이어가는 round 체인의 **내부 정지**에는 rebase nudge가
  끼어들지 않는다 — round 중의 rebase는 진행 중 분석을 무효화하기 때문이며, **이것은 우연이
  아니라 계약이다**(이 절이 그 계약의 기록이다). 체인 **진입 정지**(launch 후 첫
  정지·background 대기 후 재개 정지)에서는 두 hook이 함께 fire해 advisor trigger와 rebase nudge가
  같이 주입되고 수행 순서는 main이 정한다. 장기 loop의 remote 정합 인지는 이 진입 정지들과
  auto-compaction마다 fire하는 branch-state-warn(SessionStart `compact` matcher)이 유지하고,
  정합의 보증 자체는 close의 강제 fetch·rebase·CI가 소유한다 — loop 중 nudge는 신선도
  최적화이지 무결성 요건이 아니다.
- **refine × tx — 청소도 gate를 지난다**(MEMORY 불변식 1). 접면은 그 gate 하나다: refine은 tx를
  참조하지 않는다(무종속 계약). refine run의 halt 구간(빈 background 정지)에 tx git-sync nudge가
  닿는 것은 알려진 접촉이고, 그 처방은 plugin 결합이 아니라 tx의 사용자 command
  (`/tx:git-sync-off`·`on`)다 — in-flight 구간은 tx의 worktree 대기 defer가 이미 비켜간다.
- **ploop × 기억 — loop는 repo를 오염하지 않는다.** ploop의 모든 상태는 repo 밖에 있다. repo로
  들어가는 유일한 경로는 응고(MEMORY 승격 routing)이며, launch rules의 승격 문구는
  행선("repo로")만 지시하고 gate·도구·세계관 어휘를 싣지 않는다 — gate의 정체는 tx
  자신의 guard 표면(쓰기 순간의 deny·SessionStart warn)이 가르치므로, tx 미설치 환경에 죽은
  구절도 미해결 어휘도 남지 않는다.
- **multi-instance — 동시성의 단위는 worktree, 수렴 지점은 origin이다.** tx 상태는 worktree 격리·
  ploop 상태는 session keying이다.
- **project-unit 격리 — install cache는 execute-only다.** plugin은 세션 스코프(머신-전역인
  user·managed scope + 현재 project)와 전역 참(published manifest, Python toolchain)만 읽는다.
  전역 write는 선언된 전제의 idempotent provisioning(uv-managed Python) 하나뿐 — cache는
  ephemeral·머신 공유라 그 안의 상태는 곧 타 project 오염이다. 각 bin runner는 stdlib-only entry를
  `uv run --no-project`로 source에서 직접 실행하며, `$0`에서 자기 root를 해석하고 module 해석을
  그 root에 고정해(-P·-B·-s) caller의 env·cwd·user site와 절연한다. runner 이름은 `-hook` 접미다 —
  plugin `bin/`은 Bash PATH에 주입되므로 bare 이름은 namespace 오염이다. 강제는
  `tests/test_plugin_runtime.py`. 의존성이 생기는 미래 plugin은 cache가 아니라
  CLAUDE_PLUGIN_DATA에 manifest-diff 패턴으로 환경을 둔다.
- **규약 운반** — docs 표면 규약의 층별 배치와 fork 경계는 MEMORY.md 운반 절이 소유한다.

## 언어·prompt 정책 (repo 전역)

단일 **"한국어 기반, 영어 활용"** — 산문은 한국어, 식별자·경로·도구 이름·역할 명칭은 영어,
ASCII 다이어그램은 정렬을 위해 영어만. **언어는 독자가 정한다**: 소유자가 감사하는 산문 —
prompt 본문·정본 — 은 한국어, 사용자 대면 출력은 사용자 언어, 그 밖의 기계·UI lane —
상태 고지 notice, description metadata, statusMessage, hook이 조립하는 발신 message, runtime
위임 prompt — 는 영어다. root README만 한·영 쌍이고, plugins/tx/README.md는 정본 겸
marketplace 대면이라, INSTALL.md는 관문의 연장(설치 수행 agent 대상)이라 영어 단일본이다. plugin 특이사항은 소유 정본에 남는다(예: ploop의
hook 주입 message 조립).

## 결정 기록 (배제 — YAGNI/오컴)

- **upstream OpenSpec prompt 미설치** — engine·format만 채택하고 정책은 전량 자작한다. 근거와
  seam은 MEMORY의 OpenSpec 채택 경계.
- **별도 session 자동화(claude -p) 기각** — 정식 nested subagent 경로만 사용한다(구독 안전).
  근거는 ploop 정본.
- **ADR·사실 DB·문서 index 기각** — 결정 기록은 각 정본의 배제·결정 section, 측정은 조사 기록,
  회상은 grep. 근거는 MEMORY의 docs 표면 규약.
- **bootstrap 예외 1회** — 기억 architecture를 완성한 transaction 자신은 자신이 설치한
  기계(plan·verify·docs gate)보다 앞서, change artifact 없이 병합되었다(2026-07).
  이후 구조 변경의 예외는 0이다.
- **marketplace auto-update 비채택** — 자동 update는 mission 중간의 새 session에 plugin을 무인
  swap해 anchor에 정박된 loop의 행동을 운영자 모르게 바꾼다. version-up-alert의 alert-only가
  도구 교체를 인간 몫으로 유지한다. uv 부재 안내도 같은 곳으로 중앙화한다 — wrapper들의 차단
  message는 기능적 사실만 나른다.
- **Claude Code 하위 호환 비목표 (auto-update 전제)** — 배포는 출시 시점의 최신 Claude Code만
  대상으로 하고, 사용자의 Claude Code는 auto-update된다고 전제한다. plugin은 harness 버전을
  탐지·분기하지 않는다 — 버전 guard는 존재하지 않는 사용자를 위한 복잡도다. (settings/env
  상태의 assertion — ploop 결정 18 — 은 버전이 아니라 구성의 문제라 이 배제 밖이다.)
- **소급 capability spec 전사 기각** — 기존 plugin behavior를 코드에서 spec으로 옮겨 적는
  것은 불변식 3이 막는 changelog 퇴화이자 결정 시점 provenance의 조작이다(verify는 change의
  delta를 읽지 main spec을 읽지 않는다). `openspec/specs/`는 첫 진짜 behavior delta의
  ADDED에서 유기적으로 태어난다.
