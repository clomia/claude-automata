# Parallax

[English](README.md) | 한국어

**길고 복잡한 작업을 위한 자율 주행 시스템.**

Parallax는 사용자 대신 클로드가 놓친 부분을 찾고 제시합니다.  
시간이 오래 걸리더라도 작업이 완벽히 끝날 때까지 계속합니다.

- 프롬프트 끝에 `parallaxthink`를 붙이면 시작됩니다.
  - 예시: `웹 테트리스 게임 만들어줘. parallaxthink`
- 작업 히스토리가 없는 새로운 세션에서 사용하세요.
  - 이전 작업 내역은 Parallax에게 전달되지 않습니다.
- 사용 후 `/parallax-log` 커멘드로 로그를 확인하세요.

### [**Parallax 설계가 왜 유효한가? - 이론 문서 (theory.ko.md)**](theory.ko.md)

Parallax의 원리와 이를 뒷받침하는 근거를 설명합니다. Parallax를 깊이 이해하고 싶다면 읽어보세요.

[**아키텍처 다이어그램 보기**](https://mermaid.ai/live/view#pako:eNqNVttu4zYQ_RWCTwnWDiwn2nj1sIDgRZEWTdao6iAo_EJLY1m1RKokZTsb5N87Q8mOLt6ievBFOnN4ZubM2G88VgnwgBv4pwIZw7dMpFoUK8nwEpVVsirWoFeyuRNbpdmSCcOWhm7TzVJom8VZKaRlD3N69qDUzgwfPob08FFkks2VtHC0NWatjkyna3E1nUxGzPPxZer7Iza5mcyu2UJokefiOORbvBDfdx1vwVgtUNoQE0WEiaywgK9KwxAyfybIk9COoiutjQud_DDZZ6YPA5mcSrQcf_36MA_YQquitCxGGCacyZS4XCJ2m8ndCa4htk3ylPJ0ShWgMkxuvOl1jXlSKF7tQWN5R1EUuNrX_FG1LjLrCl5jH-Z4PmEisQemxYFVCGZlrUbIhHqY7YXNlGSF0LtTF1spOI5Pj2HAflH6IHTS5qghj-EYMWNK9M9KS0yzKHOwcKLIlSqp3qWTxq4KcWS3E6ZVJRPTpHU-avES1K4QKWCdDYaVkHyAFi9NTr8rkTADxpB4Qz39AEXRuKGi6rBMllWdr4aU4NsMefVrfYtkoOYKW3j2dq8bfSueu9HtyOJlNH8OGvdAk8FB6R15RYNIxDoHlqi4KvDJhZxcn-JKawqshVGHlDTEYKEo2SbLoRf5qXOow5N4pRMXRo1N1KGV2fy5Oe8P1HSJtq4f0YYuhx7p1W_R96frDh8ZoG5dfRiTTk-2hwtpfgOyx6WDW8a7NBCTCwMxaEFIXs2wdJWEY5njmJ_6bvqFI2goRf5qMtOxNF1heM7qCQ4n6-C0yyrPfyq55c8U_dVwazBVbk0bKHKLuoci8a1A_7e0NrTNLgnzXB0ab1nlBqQlJjfAlgPKDVlpQFjrXIBGhfYERcpmOn4m4Ff5t2tLjUeDbQCStYh33YCPxYHtzqg3ptIbEZ9VdeGuhTpLt5apDaOwZqmyshZo3LSmWh06ZaRL4TYL8fdpTJun8aqKcY56Rfy_O3agq71vF8rYeX1Oa9UOMicoDQPra9KQDEOg356eq_57zQ5Yuvsbo5ZuJETeGJEldUtICh_xVGcJD6yuYMQL0Gg__MrfiGDF7RYKWPEAPyawERi94iv5jmH4Q_iXUsUpEvdVuuXBRqAHR7wqE1xHzV-IMwSFgZ7TruWB7xh48MaPPJj6X24835_O7j1_Nvs88Ub8FSF32BR_4n3xbu_8W292_z7iP9yRHv4dQLR_N_W92WfPv5--_wsj4KGN)

### 사전 요구사항

**이 플러그인을 사용하려면 uv가 설치되어 있어야 합니다.**

uv 설치 방법: <https://docs.astral.sh/uv/getting-started/installation/>

### 플러그인 설치

```
claude plugin marketplace add clomia/claude-automata
claude plugin install parallax@claude-automata
```

### 플러그인 업데이트

```
claude plugin marketplace update claude-automata
claude plugin update parallax@claude-automata
```
