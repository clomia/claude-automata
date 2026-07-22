# Design — docent-project-scope

## Context

data dir는 plugin 단위(machine 전역)이고 loop 상태 파일은 session_id로만 key된다. Bash
env에는 `CLAUDE_SESSION_ID`·`CLAUDE_PROJECT_DIR`·`CLAUDE_PLUGIN_DATA`가 없음을 실측했다
(v2.1.216) — env 주입은 hook·MCP·LSP process 한정이고, Bash lane 전달은 skill 본문
placeholder 치환뿐이다. hook process는 `CLAUDE_PROJECT_DIR`를 받는다(공식 문서).

stale loop 간섭 조사: loop 기계의 전 진입점(stop·launch·off·on)은 현재 session_id로만
상태를 찾으므로 과거 세션의 loop 파일은 기계에 불활성이다 — 유일한 교차 세션 표면이
docent 열거다.

소유자 최종 확정 요구: (1) 해당 directory에서 launch된 loop만 최신순으로 보여라,
(2) 다른 directory에서 launch된 loop는 노출하지 마라. 추가 요구: 완료된 loop를 제외하는
option.

## Goals / Non-Goals

- Goal: "launch된 directory"를 판정 기준으로 하는 양성 포함 열거 — 판정 불가는 노출하지
  않는다(요구 2가 지배한다).
- Goal: loop 수명(몇 달)이 transcript 보존기간(cleanupPeriodDays, 활동 기준)에 결박되지
  않는 판정 — launch 시점 기록이 유일하게 이를 보장한다.
- Non-Goal: staleness 추정 — transcript 부재·launch 경과일 같은 신호로 고령을 판정하는
  logic은 두지 않는다(소유자 지적: loop은 몇 달씩 계속될 수 있다). 시간 축의 표현은
  최신순 정렬이 전부다.
- Non-Goal: 기록 GC — disk 축적은 canon의 기술 risk로 기록된 별도 사안이다.

## Decisions

- **판정의 정본은 launch 시점 기록(`{session}_project`)이다** — 소유자 기준이 "launch된
  directory"이므로 launch가 그 사실을 기록하는 것이 근원 oracle이다. transcript 부모
  이름 대응은 기록 도입 이전 fleet의 fallback로만 쓰고, 기록이 있으면 기록이 이긴다.
  설계 경위: 최초안(transcript 부재 + 타 session 귀속 성립 → 보존기간 경과로 은닉)은
  장기 pause loop을 자기 repo에서 은닉하는 오판으로 철회됐고, 차안(판정 불가 나열 +
  정렬)은 transcript가 정리된 타 directory loop이 전 repo에 재노출되는 잔존을 남겨
  소유자가 최종 요구로 대체했다. launch 기록은 두 결함이 모두 구조적으로 불가능하다 —
  자기 loop은 영구 판정되고, 타 loop은 영구 은닉된다.
- **기존 fleet의 수렴은 Stop hook backfill** — 기록 도입 이전에 launch된 active loop은
  다음 정지에서 기록을 얻는다(gate 조기 exit보다 앞에 둔다). 영영 재정지하지 않는
  loop만 transcript fallback → 그마저 소멸하면 판정 불가로 미노출된다(요구 2의 극성;
  기록 파일은 data dir에 남는다).
- **encoding matcher는 규칙 변형을 관용한다** — 관측 표본은 `/`→`-`·문자 보존만
  확정한다. 문자 단위 대응(ASCII 영숫자는 대소문자 무시 동일성, 그 외 `-` 또는 동일성,
  길이 일치)으로 실제 규칙이 어느 변형(case folding 포함)이든 fallback이 자기 loop을
  숨기지 않는다. 오판 방향은 과포함. 손상된 provenance 기록은 기록 부재로 강등된다 —
  한 session의 손상이 목록 전체를 죽이는 극성을 금지한다(설계 검수에서 재현된 crash의
  수리).
- **완료 제외는 opt-in flag(`--exclude-converged`)** — docent의 1급 용례에 "끝난 loop
  회고"가 있어(SKILL: running or finished) 기본 배제는 그 용례를 죽인다. 필터 축은
  phase==converged(재개 불가한 완결)다 — running-only(active marker)는 stall 진단이라는
  docent의 구조 용도를 가리므로 채택하지 않는다.
- **모든 숨김·제외는 개수 1행으로 고지** — 내용 없는 계수만 노출해 무언의 절삭과 내용
  누출을 동시에 없앤다.
- **skill 교리에서 수동 선별 제거** — 결정론이 코드로 이동했다. "너의 subject는 이
  directory의 loop 하나다"는 유지 — 같은 directory 복수 loop에서의 subject 선택은
  여전히 docent 몫이고 active 우선·최근순 정렬이 그것을 돕는다.

## Risks / Trade-offs

- [repo directory 이동 시 기록 불일치로 자기 loop이 새 경로에서 미노출] → 숨김 개수
  1행이 단서이고, `--project-dir <구 경로>`로 즉시 열람 가능하다. 이동은 드물고 기록은
  불변이라 데이터 손실이 없다.
- [encoding 규칙이 관용 범위 밖으로 표류] → legacy fallback만 영향(기록 loop 무영향),
  방향은 미노출 + 개수 고지로 가시적이다. audit-harness-deps의 관측 의존 감사 lane이
  치유 지점이다.
- [기록 없는 legacy가 영영 정지하지 않고 transcript도 소멸] → 판정 불가로 미노출 —
  요구 2가 요구하는 극성이며, 기록 파일 자체는 남는다.

## Migration Plan

plugin release로 배포. 기 시드 기기의 active loop은 갱신 후 첫 정지에서 기록을 얻고,
docent는 첫 실행부터 launch 기준으로 좁아진다. rollback은 version 복귀로 완결 —
`{session}_project`는 잔존해도 구판이 읽지 않는 불활성 파일이다.

## Open Questions

없음.
