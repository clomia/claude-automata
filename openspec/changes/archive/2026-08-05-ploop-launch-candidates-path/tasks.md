## 1. Address delivery

- [x] 1.1 `prompt.py`: candidates 경로 안내 문구를 단일 소스로 — trigger의 상시 라인과 launch의
      최초 배달이 같은 문장을 쓴다
- [x] 1.2 `main.py`: `UserPromptExpansion`의 `hookSpecificOutput.additionalContext` emit —
      launch가 loop를 arm한 경로에서만 호출하고, 차단 3종(active·빈 anchor·prerequisite)과 배타

## 2. Canon

- [x] 2.1 `ARCHITECTURE.md` 결정 21: queue 주소는 기계가 배달한다 — dangling reference가 낳는
      silent divergence와 `/ploop:on`·`/ploop:off` 배제 근거
- [x] 2.2 `ARCHITECTURE.md` 파일 표(`candidates.md` 안내 주체)·hook 표(launch 동작) 갱신,
      "수용한 한계"의 round 0 항목 제거

## 3. Tests and release

- [x] 3.1 tests: arm된 launch가 경로를 배달 / 차단 3종은 미배달 / launch와 trigger가 같은 경로
- [x] 3.2 version 0.53.1 -> 0.54.0 (`plugin.json`·`pyproject.toml`·`uv.lock`)
