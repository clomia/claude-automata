## Why

fresh-context agent에게 raw URL로 INSTALL.md를 읽혀 brownfield 설치를 시뮬레이션한 결과,
지침에 blocker 하나와 polish 셋이 드러났다. 별개로 사용자가 관문 서두 제거를 지시했다.

1. **재시작 핸드오프가 각본화돼 있지 않다(blocker).** INSTALL.md는 세션 1에게 "재시작을
   사용자에게 표면화하라"고만 한다. 그러나 마쳐야 할 주체는 재시작된 세션 2 — task 기억도
   INSTALL.md도 없는 fresh context다. 사용자가 우연히 같은 prompt를 다시 보내지 않으면 설치는
   settings만 적용된 채 seed·transaction 없이 방치된다. 회복 경로는 존재하나(세션 2가 문서를
   다시 읽으면 수렴) 문서가 세션 1에게 그 재개 방법을 사용자에게 넘기라고 지시하지 않는다.
2. **uv 전제 미명시(polish).** INSTALL.md는 자신을 유일 지침원으로 표방하지만 `uvx`가 요구하는
   uv를 언급하지 않는다. init이 전제조건 oracle인데 uv 없이는 그 init조차 못 돈다(순환).
3. **openspec-validate context 연결 미명시(polish).** 공개 술어는 seed의 workflow(memory-check)
   와 `openspec-validate` context가 같은 산출물임을 잇지 않아, agent가 호스트 CI 수술 대상을
   추론해야 한다.
4. **predicate 1과 재시작 note의 긴장(polish).** "notes에 미해결이 없다"가 init이 항상 남기는
   재시작 note(세션 내 해소 불가)와 충돌한다.
5. **관문 서두 제거(사용자 지시).** "Installation is agent work / 설치도 agent의 일입니다"류
   서두는 불필요하다.

## What Changes

- **INSTALL.md 재시작 술어에 재개 핸드오프** — agent는 자기 세션을 재시작·context 계승 못
   하므로, 재시작과 **재개 방법(재시작 후 같은 요청을 다시 보내면 돌아온 세션이 문서를 다시
   읽어 마저 수렴)**을 사용자에게 넘긴다.
- **INSTALL.md predicate 1** — uv 전제 명시 + 재시작 note는 아래 술어 소관임을 밝혀 긴장 해소.
- **INSTALL.md 공개 술어** — seed의 memory-check workflow가 `openspec-validate` context를
   운반함을 명시.
- **관문 서두 제거** — README 쌍·site 쌍 getting-started에서 "agent work" 서두를 걷고 실행
   지시만 남긴다.
- version bump 없음 — plugin·package 구현 불변.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

- `landing-page`: Agent install canon requirement에 재시작 핸드오프(재개 방법 표면화)를 술어
   요건으로 추가하고 `재시작 관문` scenario를 그에 맞춘다. 나머지(uv·context 연결·서두 제거)는
   기존 계약 안이라 문구 변경뿐.

## Impact

- `INSTALL.md`
- `README.md` · `README.ko.md` · `site/index.html` · `site/ko/index.html`
- `openspec/specs/landing-page/spec.md` (archive 시 sync)
- 시뮬레이션이 남긴 미반영 발견(보고만): brownfield spec 수리 부담·2차 tx 수렴·living-doc
   oracle 범위는 도입 고유 비용이거나 이미 문서화돼 지침 수정 대상이 아니다.
