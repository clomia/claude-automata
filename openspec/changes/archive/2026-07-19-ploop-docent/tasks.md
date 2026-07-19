## 1. Resolver

- [x] 1.1 `src/docent.py` — session 열거·경로 해석·English 출력 (data dir 체인: flag→env→glob,
  read-only)
- [x] 1.2 pyproject `[project.scripts]`에 `docent` 등록
- [x] 1.3 `tests/test_docent.py` — 열거·빈 dir·env 체인·read-only·transcript 해석
  (subprocess/disk 구동, 구현 독립)

## 2. Docent skill

- [x] 2.1 `skills/docent/SKILL.md` — 교리: 경계(read-only)·기록 표면 의미론·응답 규율·resolver
  호출 (`disable-model-invocation: true`)

## 3. 문서·버전

- [x] 3.1 `plugins/ploop/ARCHITECTURE.md` — 3표면 구조 절, docent 설계 결정, 파일 맵 갱신
- [x] 3.2 README.ko.md ploop 절에 docent 사용법 추가 + README.md 동기화
- [x] 3.3 version 0.46.5 → 0.47.0 (pyproject.toml·plugin.json)
