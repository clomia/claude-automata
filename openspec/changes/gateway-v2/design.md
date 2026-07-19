## Context

소유자 고도화 지시. 참고 기준 두 개를 실측(README raw + headless 스크린샷)으로 분석했다:
caveman README는 banner→tagline→즉각 Before/After→단일 install→`<details>` 접기,
caveman.so는 거대 활자 단일 주장 + 즉시 증명 그래픽 하나 + 단일 CTA. 우리 register
(document-of-record, 제도용지)는 유지하되 이 문법을 이식한다.

## Decisions

- **H1은 서술이 아니라 주장**: "Runs for days. Remembers only what's verified." — 두 문장이
  두 산출물(ploop의 지속, tx gate의 검증 기억)을 그대로 요약하며 전부 정본 검증 가능.
  기존 정체 서술("An autonomous agent environment...")은 eyebrow로 이동.
- **advisor = 메타인지의 show-don't-tell**: terminal 풍 exchange panel — agent의 "done"
  선언 → hook의 정지 차단 → advisor(clean context)의 미고려 영역 제시 → 반복 → "no further
  advice"로 종료. 연출된 대화지만 각 행이 기제의 사실 서술이다(Stop hook 차단·advisor
  소집·의미론적 종료 — 전부 ploop 정본 검증 가능). 이 panel이 사이트의 두 번째
  show-don't-tell(첫째는 기억 회로)이다.
- **자체 완결 = 이해의 완결**: 각 절 산문이 링크 없이 기제를 설명하도록 보강. KO 정본
  link는 module card의 소형 SOURCE 행으로 강등(존재는 유지 — 투명성 + canon-links CI).
  정본 전문 이식은 여전히 금지(복제는 표류) — 요약의 밀도만 올린다.
- **README hook 명명**: "Watch the memory circuit run →" — 명칭(Landing page)이 아니라
  내용의 초대. banner 직하단과 문서 말미 두 곳.
- **README 절반화**: 사용 절차·제어(off/on/docent)·refine skill 상세는 `<details>`로.
  ARCHITECTURE·MEMORY 참조 전면 제거 — 깊이는 사이트가, 사이트가 다시 필요 시 정본을
  가리킨다(위임 사슬).
- **banner**: og-card 선례 그대로 — committed source에서 생성(1280×400), 어두운 GitHub
  README 배경 위에서도 성립하도록 paper 색 card에 회로 축약. og-coupling job을 쌍 목록
  순회로 일반화.
- **한 층 더 큰 활자 허용**: H1 clamp 상한 3.4rem→5rem(두 줄 lockup). caveman 스케일은
  register가 다르므로 그대로 복제하지 않는다.

## Risks / Trade-offs

- [연출 대화가 실제 출력으로 오독] → panel에 "illustrative exchange — the mechanics are
  real" 1행 label을 단다. 과장 아님: 각 행은 기제의 사실이다.
- [README 압축으로 상세 유실] → `<details>`가 보존, 사이트 §들이 대체 서술.
- [R3에서 정본 link 요구 삭제] → SOURCE 행으로 실질 유지, spec은 자체 완결을 상위 계약으로.

## Open Questions

없음.
