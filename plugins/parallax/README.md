# Parallax

English | [한국어](README.ko.md)

**Autopilot for long, complex tasks.**

Parallax catches what Claude overlooks and surfaces it, on your behalf.  
It keeps going until the task is flawlessly done, however long that takes.

- Append `parallaxthink` to the end of your prompt to start it.
  - Example: `Make a web Tetris game. parallaxthink`
- Use it in a fresh session with no prior work history.
  - Prior work isn't passed to Parallax.
- After use, check the log with `/parallax-log`.

### [**Why Parallax's design works — Theory Document (theory.md)**](theory.md)

Explains the principles behind Parallax and the evidence that backs them. Read this if you want to understand Parallax in depth.

[**View Architecture Diagram**](https://mermaid.ai/live/view#pako:eNqNVttu4zYQ_RWCTwnWDiwn2nj1sIDgRZEWTdao6iAo_EJLY1m1RKokZTsb5N87Q8mOLt6ievBFOnN4ZubM2G88VgnwgBv4pwIZw7dMpFoUK8nwEpVVsirWoFeyuRNbpdmSCcOWhm7TzVJom8VZKaRlD3N69qDUzgwfPob08FFkks2VtHC0NWatjkyna3E1nUxGzPPxZer7Iza5mcyu2UJokefiOORbvBDfdx1vwVgtUNoQE0WEiaywgK9KwxAyfybIk9COoiutjQud_DDZZ6YPA5mcSrQcf_36MA_YQquitCxGGCacyZS4XCJ2m8ndCa4htk3ylPJ0ShWgMkxuvOl1jXlSKF7tQWN5R1EUuNrX_FG1LjLrCl5jH-Z4PmEisQemxYFVCGZlrUbIhHqY7YXNlGSF0LtTF1spOI5Pj2HAflH6IHTS5qghj-EYMWNK9M9KS0yzKHOwcKLIlSqp3qWTxq4KcWS3E6ZVJRPTpHU-avES1K4QKWCdDYaVkHyAFi9NTr8rkTADxpB4Qz39AEXRuKGi6rBMllWdr4aU4NsMefVrfYtkoOYKW3j2dq8bfSueu9HtyOJlNH8OGvdAk8FB6R15RYNIxDoHlqi4KvDJhZxcn-JKawqshVGHlDTEYKEo2SbLoRf5qXOow5N4pRMXRo1N1KGV2fy5Oe8P1HSJtq4f0YYuhx7p1W_R96frDh8ZoG5dfRiTTk-2hwtpfgOyx6WDW8a7NBCTCwMxaEFIXs2wdJWEY5njmJ_6bvqFI2goRf5qMtOxNF1heM7qCQ4n6-C0yyrPfyq55c8U_dVwazBVbk0bKHKLuoci8a1A_7e0NrTNLgnzXB0ab1nlBqQlJjfAlgPKDVlpQFjrXIBGhfYERcpmOn4m4Ff5t2tLjUeDbQCStYh33YCPxYHtzqg3ptIbEZ9VdeGuhTpLt5apDaOwZqmyshZo3LSmWh06ZaRL4TYL8fdpTJun8aqKcY56Rfy_O3agq71vF8rYeX1Oa9UOMicoDQPra9KQDEOg356eq_57zQ5Yuvsbo5ZuJETeGJEldUtICh_xVGcJD6yuYMQL0Gg__MrfiGDF7RYKWPEAPyawERi94iv5jmH4Q_iXUsUpEvdVuuXBRqAHR7wqE1xHzV-IMwSFgZ7TruWB7xh48MaPPJj6X24835_O7j1_Nvs88Ub8FSF32BR_4n3xbu_8W292_z7iP9yRHv4dQLR_N_W92WfPv5--_wsj4KGN)

### Prerequisites

**This plugin requires uv to be installed.**

Install uv: <https://docs.astral.sh/uv/getting-started/installation/>

### Install the Plugin

```
claude plugin marketplace add clomia/claude-automata
claude plugin install parallax@claude-automata
```

### Update the Plugin

```
claude plugin marketplace update claude-automata
claude plugin update parallax@claude-automata
```
