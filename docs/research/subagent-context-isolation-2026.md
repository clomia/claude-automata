# Subagent context isolation — fresh-context 검증이 이 repo 안에서 가능한가

- 작성일: 2026-07-20
- 질문: 이 repo에서 Agent tool로 spawn된 subagent의 context에 무엇이 이미 주입되어
  있는가 — "사전 맥락 없는(fresh-context) 검증자"를 official subagent 경로로 세울 수 있는가?
- 방법: no-tools general-purpose subagent를 spawn해 자기 context를 verbatim 인용으로
  자기보고하게 함 (도구 사용 0 — 보고 내용 전부가 주입분). landing-page mission의
  검증 protocol 설계 중 실측.

## 발견

- ✅ **project CLAUDE.md와 rules 파일들은 원문 그대로 주입된다** — subagent가 각 파일
  첫 줄들을 verbatim 재현했다.
- ✅ **CLAUDE.md 첫 줄의 `@README.ko.md` import는 확장되지 않는다** — README 본문(정체
  선언 문장)은 subagent context 어디에도 없었고, literal 문자열 `@README.ko.md`만 존재.
- ✅ **세계관 어휘는 다른 경로로 누출된다** — CLAUDE.md의 정본 pointer("MEMORY.md —
  기억 시스템"), skill 목록(ploop:define-mission·tx:* 등), 최근 commit message들이
  "자율 loop + 기억 시스템 + transaction workflow"라는 골격을 사전 제공한다. 실측
  subagent는 이것만으로 project의 성격을 상당 부분 추론했다.
- 🔶 판단: **완전한 zero-context 검증자는 이 repo의 official subagent 경로에서 불가능하다.**
  별도 session(`claude -p`)이 필요하나 그 경로는 생태계가 기각했다(root ARCHITECTURE
  결정 기록 — 구독 안전). 실용 완화 두 가지가 유효했다: (1) 인용-정박 — probe에게 모든
  사실 주장마다 검증 대상 artifact의 절 인용을 요구하면 재구성의 근거가 artifact로
  고정된다, (2) 이미지 단독 판독 — rendered 그래픽만 주면 구조 판독은 어휘 누출의
  이득을 크게 받지 않는다. 오염의 bias 방향은 false PASS(재구성 fluency) 쪽이므로,
  fresh-context 계열 검증 결과를 읽을 때 이 한계를 함께 읽어야 한다.
