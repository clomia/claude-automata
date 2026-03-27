# Data Model 설계서

> **claude-automata** 시스템의 모든 데이터 스키마 정의

이 문서는 시스템의 모든 상태 파일에 대한 JSON Schema 수준의 스키마를 정의한다. 각 스키마는 필드 설명, 타입, 제약 조건, 기본값, 완전한 예시를 포함한다.

---

## 목차

1. [Purpose](#1-purpose) — `state/purpose.json`
2. [Strategy](#2-strategy) — `state/strategy.json`
3. [Missions](#3-missions) — `state/missions.json`
4. [Friction](#4-friction) — `state/friction.json`
5. [Requests](#5-requests) — `state/requests.json`
6. [Sessions](#6-sessions) — `state/sessions.json`
7. [Config](#7-config) — `state/config.toml`
8. [Current Session](#8-current-session) — `run/current_session.json`
9. [Heartbeat](#9-heartbeat) — `run/supervisor.heartbeat`
10. [Supervisor State](#10-supervisor-state) — `run/supervisor.state`
11. [Archive Files](#11-archive-files) — `state/archive/*.jsonl`

---

## 공통 규약

### 타임스탬프 형식
모든 타임스탬프는 **ISO 8601 UTC** 형식을 사용한다.
```
"2026-03-25T10:30:00Z"
```

### ID 형식
| 엔티티 | 형식 | 예시 |
|--------|------|------|
| Mission | `M-NNN` (3자리 zero-padded) | `M-001`, `M-042` |
| Friction | `F-NNN` (3자리 zero-padded) | `F-001`, `F-007` |
| Request | `R-NNN` (3자리 zero-padded) | `R-001`, `R-015` |
| Session | UUID v4 (Claude Code 발급) | `a1b2c3d4-e5f6-...` |

### 파일 관리
- `state/` 디렉토리의 파일은 Git으로 추적한다
- `run/` 디렉토리의 파일은 Git에서 제외한다 (`.gitignore`)
- 모든 파일 쓰기는 State Manager를 통해 원자적(atomic)으로 수행한다: temp 파일에 쓰고 `os.rename()`으로 교체
- 파일 인코딩은 UTF-8을 사용한다

---

## 1. Purpose

**파일**: `state/purpose.json`
**설명**: 시스템의 영속적 방향. Owner의 최초 입력으로부터 구성되며, 시스템의 모든 의사결정의 기준점이 된다. Initialization Session(P-1)에서 생성되고, 극히 드물게 진화할 수 있다.

### JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Purpose",
  "description": "시스템의 영속적 방향 정의",
  "type": "object",
  "required": ["raw_input", "purpose", "domain", "key_directions", "constructed_at", "last_evolved_at", "evolution_history"],
  "additionalProperties": false,
  "properties": {
    "raw_input": {
      "type": "string",
      "description": "Owner가 acc configure 시 입력한 원문 텍스트. 변경 불가. 시스템이 항상 원점을 참조할 수 있도록 보존한다.",
      "minLength": 1
    },
    "purpose": {
      "type": "string",
      "description": "raw_input으로부터 추출된 영속적 방향 문장. 무한히 추구할 수 있는 방향이어야 하며, 완료 가능한 목표가 아니다. Initialization Session에서 Claude가 구성한다.",
      "minLength": 1
    },
    "domain": {
      "type": "string",
      "description": "Purpose가 속하는 도메인 영역. 전략/미션 생성, 스킬 습득 방향의 기준이 된다.",
      "examples": ["웹 개발", "데이터 엔지니어링", "DevOps 자동화", "머신러닝 연구"]
    },
    "key_directions": {
      "type": "array",
      "description": "Purpose를 구체화하는 핵심 방향 목록. 3~7개를 권장한다. 전략 수립과 미션 생성의 시드(seed) 역할을 한다.",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "minItems": 1,
      "maxItems": 10
    },
    "constructed_at": {
      "type": "string",
      "format": "date-time",
      "description": "Purpose가 최초 구성된 시각. Initialization Session 완료 시점. 변경 불가."
    },
    "last_evolved_at": {
      "type": "string",
      "format": "date-time",
      "description": "Purpose가 마지막으로 진화한 시각. 최초 구성 시에는 constructed_at과 동일하다."
    },
    "evolution_history": {
      "type": "array",
      "description": "Purpose 진화 이력. 최초 구성은 포함하지 않으며, 이후 변경만 기록한다. Purpose 진화는 극히 드물어야 한다 (목표 드리프트 방지).",
      "items": {
        "type": "object",
        "required": ["timestamp", "trigger", "previous_purpose", "new_purpose", "reason"],
        "additionalProperties": false,
        "properties": {
          "timestamp": {
            "type": "string",
            "format": "date-time",
            "description": "진화가 발생한 시각"
          },
          "trigger": {
            "type": "string",
            "enum": ["owner_request", "goal_drift_correction"],
            "description": "진화를 촉발한 원인. owner_request: Owner가 명시적으로 방향 변경 요청. goal_drift_correction: 시스템이 자체 감지한 드리프트 교정."
          },
          "previous_purpose": {
            "type": "string",
            "description": "변경 전 purpose 문장"
          },
          "new_purpose": {
            "type": "string",
            "description": "변경 후 purpose 문장"
          },
          "reason": {
            "type": "string",
            "description": "진화 사유 설명"
          }
        }
      }
    }
  }
}
```

### 검증 규칙

| 규칙 | 설명 |
|------|------|
| `raw_input` 불변 | 최초 설정 이후 절대 변경하지 않는다 |
| `constructed_at` 불변 | 최초 설정 이후 절대 변경하지 않는다 |
| `purpose` 진화 제한 | purpose 변경 시 반드시 evolution_history에 기록해야 한다 |
| `key_directions` 범위 | 최소 1개, 최대 10개. 권장 3~7개 |
| 목표 드리프트 검사 | goal_drift_check_interval(Config)마다 purpose와 현재 미션 방향의 정합성을 검증한다 |

### 완전한 예시

```json
{
  "raw_input": "나는 개인 블로그를 운영하고 있어. 블로그의 품질을 지속적으로 개선하고, 새로운 콘텐츠를 자동으로 생성하고, SEO를 최적화하고, 독자 경험을 향상시키고 싶어. Next.js로 만들어져 있고, 마크다운으로 글을 쓰고 있어.",
  "purpose": "Next.js 기반 개인 블로그의 품질, 콘텐츠, 기술 수준을 영속적으로 향상시킨다",
  "domain": "웹 개발 / 콘텐츠 플랫폼",
  "key_directions": [
    "콘텐츠 품질 및 자동 생성 파이프라인 구축",
    "SEO 최적화 및 검색 엔진 가시성 향상",
    "독자 경험(UX) 지속적 개선",
    "기술 스택 현대화 및 성능 최적화",
    "분석 기반 데이터 드리븐 개선"
  ],
  "constructed_at": "2026-03-25T10:00:00Z",
  "last_evolved_at": "2026-03-25T10:00:00Z",
  "evolution_history": []
}
```

---

## 2. Strategy

**파일**: `state/strategy.json`
**설명**: Purpose를 추구하기 위한 현재 전략. Initialization Session(P-2)에서 최초 생성되며, 자기개선 루프를 통해 지속적으로 진화한다. 미션 생성의 직접적 입력이 된다.

### JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Strategy",
  "description": "Purpose를 추구하는 현재 전략",
  "type": "object",
  "required": ["summary", "approach", "skills", "principles", "created_at", "last_evolved_at", "evolution_count"],
  "additionalProperties": false,
  "properties": {
    "summary": {
      "type": "string",
      "description": "현재 전략의 한 줄 요약. TUI 대시보드와 Slack 알림에서 표시용으로 사용한다.",
      "minLength": 1,
      "maxLength": 200
    },
    "approach": {
      "type": "string",
      "description": "전략의 상세 접근 방법. 여러 문단을 포함할 수 있다. Claude가 미션을 생성하고 실행할 때 참조하는 핵심 가이드.",
      "minLength": 1
    },
    "skills": {
      "type": "array",
      "description": "시스템이 습득한 도메인 특화 스킬 목록. 새로운 스킬을 배울 때마다 추가된다. 미션 실행 능력의 현황판 역할을 한다.",
      "items": {
        "type": "object",
        "required": ["name", "level", "acquired_at"],
        "additionalProperties": false,
        "properties": {
          "name": {
            "type": "string",
            "description": "스킬 이름",
            "examples": ["Next.js App Router", "Tailwind CSS", "MDX 처리", "Google Search Console API"]
          },
          "level": {
            "type": "string",
            "enum": ["learning", "competent", "proficient", "expert"],
            "description": "스킬 숙련도. learning: 학습 중. competent: 기본 활용 가능. proficient: 능숙한 활용. expert: 전문가 수준."
          },
          "acquired_at": {
            "type": "string",
            "format": "date-time",
            "description": "스킬을 처음 습득한 시각"
          }
        }
      }
    },
    "principles": {
      "type": "array",
      "description": "미션 실행 시 지키는 원칙 목록. 경험과 Friction으로부터 학습하여 추가/수정된다.",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "minItems": 1
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "전략이 최초 생성된 시각 (Initialization Session). 변경 불가."
    },
    "last_evolved_at": {
      "type": "string",
      "format": "date-time",
      "description": "전략이 마지막으로 진화한 시각"
    },
    "evolution_count": {
      "type": "integer",
      "minimum": 0,
      "description": "전략이 진화한 총 횟수. 자기개선 활동의 빈도 지표.",
      "default": 0
    }
  }
}
```

### 검증 규칙

| 규칙 | 설명 |
|------|------|
| `created_at` 불변 | 최초 설정 이후 절대 변경하지 않는다 |
| `summary` 길이 | 최대 200자. TUI 및 Slack 표시를 위해 제한한다 |
| `skills` 고유성 | 동일 name의 스킬이 중복 존재할 수 없다. level만 업데이트한다 |
| `principles` 최소 | 최소 1개 이상의 원칙이 있어야 한다 |
| `evolution_count` 정합성 | 전략 변경 시 반드시 evolution_count를 1 증가시킨다 |
| Purpose 정합성 | 전략 진화 시 Purpose와의 정합성을 반드시 검증한다 |

### 완전한 예시

```json
{
  "summary": "콘텐츠 자동화 파이프라인 우선 구축 후 SEO/UX 순차 개선",
  "approach": "현재 블로그의 기술 기반을 분석하고, 가장 높은 ROI를 가진 영역부터 순차적으로 개선한다.\n\n1단계: 콘텐츠 자동 생성 파이프라인을 구축한다. 마크다운 기반 글 작성을 자동화하고, 주제 발굴부터 초안 생성, 검수까지의 워크플로우를 만든다.\n\n2단계: SEO 기술적 최적화를 수행한다. 메타데이터, 구조화 데이터, 사이트맵, Core Web Vitals를 체계적으로 개선한다.\n\n3단계: 독자 경험을 향상시킨다. 검색, 관련 글 추천, 반응형 디자인 개선 등을 진행한다.\n\n모든 단계에서 변경 전후 측정을 수행하여 데이터 기반으로 의사결정한다.",
  "skills": [
    {
      "name": "Next.js App Router",
      "level": "proficient",
      "acquired_at": "2026-03-25T10:30:00Z"
    },
    {
      "name": "Tailwind CSS",
      "level": "competent",
      "acquired_at": "2026-03-25T10:30:00Z"
    },
    {
      "name": "MDX 처리",
      "level": "learning",
      "acquired_at": "2026-03-25T11:00:00Z"
    },
    {
      "name": "SEO 기술적 최적화",
      "level": "competent",
      "acquired_at": "2026-03-25T14:00:00Z"
    }
  ],
  "principles": [
    "변경 전 반드시 현재 상태를 측정하고, 변경 후 결과를 비교한다",
    "기존 코드 스타일과 패턴을 존중하며, 일관성을 유지한다",
    "하나의 미션에서 너무 많은 것을 변경하지 않는다. 작고 검증 가능한 단위로 진행한다",
    "모든 변경에 테스트를 동반한다. 테스트 없는 변경은 허용하지 않는다",
    "사용자 경험에 영향을 주는 변경은 반드시 Owner에게 확인받는다"
  ],
  "created_at": "2026-03-25T10:30:00Z",
  "last_evolved_at": "2026-03-26T08:15:00Z",
  "evolution_count": 3
}
```

---

## 3. Missions

**파일**: `state/missions.json`
**설명**: 미션 큐. 시스템이 실행할 모든 미션을 관리한다. 미션은 Purpose와 Strategy에 기반하여 생성되며, Supervisor가 우선순위에 따라 다음 미션을 선택한다.

### JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Missions",
  "description": "미션 큐 및 이력",
  "type": "object",
  "required": ["missions", "next_id", "metadata"],
  "additionalProperties": false,
  "properties": {
    "missions": {
      "type": "array",
      "description": "모든 미션의 배열. 완료/실패 미션도 이력으로 보존한다.",
      "items": {
        "$ref": "#/$defs/Mission"
      }
    },
    "next_id": {
      "type": "integer",
      "minimum": 1,
      "description": "다음 미션 생성 시 사용할 ID 번호. M-{next_id} 형식으로 사용 후 1 증가시킨다.",
      "default": 1
    },
    "metadata": {
      "type": "object",
      "description": "큐 통계 메타데이터. Supervisor가 의사결정에 참조한다.",
      "required": ["total_created", "total_completed", "total_failed", "total_blocked"],
      "additionalProperties": false,
      "properties": {
        "total_created": {
          "type": "integer",
          "minimum": 0,
          "description": "생성된 미션 총 수",
          "default": 0
        },
        "total_completed": {
          "type": "integer",
          "minimum": 0,
          "description": "완료된 미션 총 수",
          "default": 0
        },
        "total_failed": {
          "type": "integer",
          "minimum": 0,
          "description": "실패한 미션 총 수",
          "default": 0
        },
        "total_blocked": {
          "type": "integer",
          "minimum": 0,
          "description": "현재 blocked 상태인 미션 수",
          "default": 0
        }
      }
    }
  },
  "$defs": {
    "Mission": {
      "type": "object",
      "required": ["id", "title", "description", "success_criteria", "priority", "status", "blockers", "dependencies", "created_at", "started_at", "completed_at", "session_id", "source", "result_summary", "friction_ids"],
      "additionalProperties": false,
      "properties": {
        "id": {
          "type": "string",
          "pattern": "^M-[0-9]{3,}$",
          "description": "미션 고유 식별자. M-NNN 형식 (3자리 이상 zero-padded)."
        },
        "title": {
          "type": "string",
          "description": "미션 제목. 간결하되 내용을 충분히 설명. TUI 및 Slack 표시에 사용.",
          "minLength": 1,
          "maxLength": 100
        },
        "description": {
          "type": "string",
          "description": "미션의 상세 설명. Claude가 미션을 실행할 때 참조하는 핵심 정보.",
          "minLength": 1
        },
        "success_criteria": {
          "type": "array",
          "description": "미션 성공 판정 기준 목록. 모든 기준을 충족해야 미션 완료로 간주한다. 객관적으로 검증 가능한 기준이어야 한다.",
          "items": {
            "type": "string",
            "minLength": 1
          },
          "minItems": 1
        },
        "priority": {
          "type": "integer",
          "minimum": 0,
          "description": "우선순위. 0이 최고. 자기개선 미션(source: friction)은 항상 0. 숫자가 작을수록 먼저 실행된다.",
          "default": 5
        },
        "status": {
          "type": "string",
          "enum": ["pending", "in_progress", "completed", "blocked", "failed"],
          "description": "미션 상태. pending: 대기 중. in_progress: 실행 중 (세션이 작업 중). completed: 성공 완료. blocked: 차단됨 (Blocker 존재). failed: 실패.",
          "default": "pending"
        },
        "blockers": {
          "type": "array",
          "description": "미션 진행을 차단하는 Blocker 목록. Blocker가 있으면 status는 blocked로 전환된다.",
          "items": {
            "type": "object",
            "required": ["type", "description"],
            "additionalProperties": false,
            "properties": {
              "type": {
                "type": "string",
                "enum": ["owner_input", "external_dependency", "prerequisite"],
                "description": "Blocker 유형. owner_input: Owner의 답변/승인이 필요. external_dependency: 외부 서비스/리소스 대기. prerequisite: 선행 미션 완료 대기."
              },
              "request_id": {
                "type": ["string", "null"],
                "pattern": "^R-[0-9]{3,}$",
                "description": "owner_input 유형일 때 연관된 Request ID. 다른 유형이면 null.",
                "default": null
              },
              "description": {
                "type": "string",
                "description": "Blocker의 상세 설명"
              }
            }
          }
        },
        "dependencies": {
          "type": "array",
          "description": "선행 미션 ID 목록. 나열된 미션이 모두 completed 상태여야 이 미션을 시작할 수 있다.",
          "items": {
            "type": "string",
            "pattern": "^M-[0-9]{3,}$"
          }
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "description": "미션 생성 시각"
        },
        "started_at": {
          "type": ["string", "null"],
          "format": "date-time",
          "description": "미션 실행 시작 시각. 아직 시작하지 않았으면 null.",
          "default": null
        },
        "completed_at": {
          "type": ["string", "null"],
          "format": "date-time",
          "description": "미션 완료 또는 실패 시각. 아직 종료되지 않았으면 null.",
          "default": null
        },
        "session_id": {
          "type": ["string", "null"],
          "description": "이 미션을 실행한(또는 실행 중인) Claude Code 세션 ID. 아직 할당되지 않았으면 null.",
          "default": null
        },
        "source": {
          "type": "string",
          "enum": ["purpose", "friction", "owner", "self", "proactive"],
          "description": "미션 생성 원천. purpose: Initialization Session에서 Purpose 기반 생성. friction: Friction 축적으로 자동 생성된 자기개선 미션. owner: Owner가 직접 주입한 미션. self: 빈 큐에서 시스템이 자율 생성(P-3). proactive: 사전 개선 주기에서 생성(S-3)."
        },
        "result_summary": {
          "type": ["string", "null"],
          "description": "미션 결과 요약. Claude가 미션 완료/실패 시 작성한다. 이후 세션에서 참조할 수 있다.",
          "default": null
        },
        "friction_ids": {
          "type": "array",
          "description": "이 미션 실행 중 발생한 Friction 레코드 ID 목록.",
          "items": {
            "type": "string",
            "pattern": "^F-[0-9]{3,}$"
          }
        }
      }
    }
  }
}
```

### 검증 규칙

| 규칙 | 설명 |
|------|------|
| ID 고유성 | 모든 미션의 id는 배열 내에서 고유해야 한다 |
| `next_id` 정합성 | next_id는 항상 현재 최대 미션 번호 + 1 이상이어야 한다 |
| 상태 전이 제약 | `pending` -> `in_progress` -> `completed`/`failed`. `pending` -> `blocked` -> `pending` (blocker 해제 시). `in_progress` -> `blocked` -> `in_progress` 가능 |
| `started_at` 필수 | status가 `in_progress`, `completed`, `failed` 중 하나면 started_at은 null이 아니어야 한다 |
| `completed_at` 필수 | status가 `completed` 또는 `failed`이면 completed_at은 null이 아니어야 한다 |
| `session_id` 필수 | status가 `in_progress`이면 session_id는 null이 아니어야 한다 |
| `blockers` 정합성 | status가 `blocked`이면 blockers 배열이 비어 있으면 안 된다 |
| `dependencies` 참조 | dependencies에 나열된 미션 ID는 missions 배열에 존재해야 한다 |
| `friction_ids` 참조 | friction_ids에 나열된 ID는 friction.json에 존재해야 한다 |
| Friction 미션 우선순위 | source가 `friction`인 미션의 priority는 항상 0이어야 한다 |
| `metadata` 정합성 | metadata의 카운트 값들은 missions 배열의 실제 상태와 일치해야 한다 |

### 미션 선택 알고리즘 (Supervisor)

Supervisor가 다음 미션을 선택하는 우선순위:
1. status가 `pending` 또는 `blocked`에서 방금 해제된 미션 중에서
2. dependencies가 모두 `completed`인 미션만 후보로
3. priority가 가장 낮은(숫자가 작은) 미션을 선택
4. 동일 priority면 created_at이 오래된 미션을 선택

### 완전한 예시

```json
{
  "missions": [
    {
      "id": "M-001",
      "title": "블로그 프로젝트 구조 분석",
      "description": "현재 블로그 프로젝트의 디렉토리 구조, 기술 스택, 빌드 설정, 배포 환경을 분석한다. 분석 결과를 기반으로 후속 미션의 방향을 결정한다.",
      "success_criteria": [
        "프로젝트 디렉토리 구조를 문서화한다",
        "사용 중인 모든 의존성과 버전을 목록화한다",
        "빌드 및 배포 파이프라인을 파악한다",
        "현재 성능 기준선(빌드 시간, 번들 크기, Lighthouse 점수)을 측정한다"
      ],
      "priority": 1,
      "status": "completed",
      "blockers": [],
      "dependencies": [],
      "created_at": "2026-03-25T10:30:00Z",
      "started_at": "2026-03-25T10:31:00Z",
      "completed_at": "2026-03-25T11:15:00Z",
      "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "source": "purpose",
      "result_summary": "Next.js 14 App Router 사용, Tailwind CSS, MDX로 글 작성, Vercel 배포. Lighthouse 점수 72, 번들 320KB. 개선 여지 다수 발견.",
      "friction_ids": []
    },
    {
      "id": "M-002",
      "title": "SEO 메타데이터 자동 생성 시스템 구현",
      "description": "각 블로그 포스트에 대해 title, description, og:image, 구조화 데이터(JSON-LD)를 자동으로 생성하는 시스템을 구현한다.",
      "success_criteria": [
        "모든 포스트 페이지에 적절한 meta title과 description이 자동 생성된다",
        "Open Graph 태그가 올바르게 출력된다",
        "JSON-LD 구조화 데이터(Article 스키마)가 포함된다",
        "기존 수동 메타데이터와 호환된다 (수동 설정이 자동 생성을 오버라이드)"
      ],
      "priority": 2,
      "status": "in_progress",
      "blockers": [],
      "dependencies": ["M-001"],
      "created_at": "2026-03-25T10:30:00Z",
      "started_at": "2026-03-25T11:20:00Z",
      "completed_at": null,
      "session_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "source": "purpose",
      "result_summary": null,
      "friction_ids": ["F-001"]
    },
    {
      "id": "M-003",
      "title": "Tailwind CSS 클래스 정리 및 디자인 시스템 구축",
      "description": "산발적으로 사용된 Tailwind CSS 클래스를 정리하고, 일관된 디자인 토큰(색상, 간격, 타이포그래피)을 정의하여 디자인 시스템을 구축한다.",
      "success_criteria": [
        "tailwind.config.js에 프로젝트 전용 디자인 토큰이 정의된다",
        "반복되는 스타일 패턴이 @apply 또는 컴포넌트로 추출된다",
        "모든 페이지에서 디자인 일관성이 유지된다",
        "다크 모드가 디자인 시스템 기반으로 올바르게 동작한다"
      ],
      "priority": 3,
      "status": "blocked",
      "blockers": [
        {
          "type": "owner_input",
          "request_id": "R-001",
          "description": "Owner에게 선호하는 색상 팔레트와 브랜드 가이드라인 확인 필요"
        }
      ],
      "dependencies": ["M-001"],
      "created_at": "2026-03-25T10:30:00Z",
      "started_at": "2026-03-25T13:00:00Z",
      "completed_at": null,
      "session_id": null,
      "source": "purpose",
      "result_summary": null,
      "friction_ids": []
    },
    {
      "id": "M-004",
      "title": "에러 분류 패턴 학습 개선",
      "description": "반복 발생하는 MDX 파싱 에러에 대한 처리를 개선한다. Friction F-001, F-002에서 감지된 패턴을 기반으로 에러 핸들링을 강화한다.",
      "success_criteria": [
        "MDX 파싱 에러 시 명확한 에러 메시지를 출력한다",
        "에러 위치(파일명, 라인)를 정확히 표시한다",
        "자동 복구가 가능한 에러는 자동으로 수정한다"
      ],
      "priority": 0,
      "status": "pending",
      "blockers": [],
      "dependencies": [],
      "created_at": "2026-03-25T14:00:00Z",
      "started_at": null,
      "completed_at": null,
      "session_id": null,
      "source": "friction",
      "result_summary": null,
      "friction_ids": []
    }
  ],
  "next_id": 5,
  "metadata": {
    "total_created": 4,
    "total_completed": 1,
    "total_failed": 0,
    "total_blocked": 1
  }
}
```

---

## 4. Friction

**파일**: `state/friction.json`
**설명**: 마찰(Friction) 기록. 시스템 운영 중 발생하는 모든 문제, 비효율, 실패를 기록한다. Friction이 임계값(Config의 friction_threshold)만큼 축적되면 자기개선 미션이 자동 생성된다(S-1, S-2).

### JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Friction",
  "description": "마찰 기록 (자기개선 입력 데이터)",
  "type": "object",
  "required": ["frictions", "next_id"],
  "additionalProperties": false,
  "properties": {
    "frictions": {
      "type": "array",
      "description": "모든 Friction 레코드 배열. 해소된 레코드도 이력으로 보존한다.",
      "items": {
        "$ref": "#/$defs/FrictionRecord"
      }
    },
    "next_id": {
      "type": "integer",
      "minimum": 1,
      "description": "다음 Friction 생성 시 사용할 ID 번호.",
      "default": 1
    }
  },
  "$defs": {
    "FrictionRecord": {
      "type": "object",
      "required": ["id", "type", "description", "source_mission_id", "source_session_id", "timestamp", "severity", "resolution", "improvement_mission_id", "pattern_key", "occurrence_count", "resolved_at", "resolved_by"],
      "additionalProperties": false,
      "properties": {
        "id": {
          "type": "string",
          "pattern": "^F-[0-9]{3,}$",
          "description": "Friction 고유 식별자. F-NNN 형식."
        },
        "type": {
          "type": "string",
          "enum": ["error", "repeated_failure", "stuck", "quality", "owner_intervention", "slow", "context_loss"],
          "description": "Friction 유형. error: 런타임 에러 발생. repeated_failure: 동일 작업의 반복 실패. stuck: 진행 불가 상태 (해법을 찾지 못함). quality: 품질 기준 미달 (테스트 실패, 린트 에러 등). owner_intervention: Owner의 비정상적 수동 개입 필요. slow: 예상 시간 초과 (비효율). context_loss: 컨텍스트 소실로 인한 중복 작업."
        },
        "description": {
          "type": "string",
          "description": "Friction의 상세 설명. 무엇이 발생했고, 어떤 영향이 있었는지 기술한다.",
          "minLength": 1
        },
        "source_mission_id": {
          "type": ["string", "null"],
          "pattern": "^M-[0-9]{3,}$",
          "description": "이 Friction이 발생한 미션의 ID. 특정 미션과 관련 없는 시스템 레벨 Friction이면 null.",
          "default": null
        },
        "source_session_id": {
          "type": ["string", "null"],
          "description": "이 Friction이 발생한 세션의 ID. 세션 외부에서 발생한 Friction이면 null.",
          "default": null
        },
        "timestamp": {
          "type": "string",
          "format": "date-time",
          "description": "Friction 발생 시각"
        },
        "severity": {
          "type": "string",
          "enum": ["low", "medium", "high", "critical"],
          "description": "심각도. low: 사소한 비효율. medium: 작업 지연을 유발. high: 미션 실패를 유발하거나 유발할 수 있음. critical: 시스템 전체에 영향을 미치는 심각한 문제."
        },
        "resolution": {
          "type": ["string", "null"],
          "description": "해소 방법 설명. 자기개선 미션에 의해 해소되었으면 그 내용을, 아직 미해소이면 null.",
          "default": null
        },
        "improvement_mission_id": {
          "type": ["string", "null"],
          "pattern": "^M-[0-9]{3,}$",
          "description": "이 Friction을 해소하기 위해 생성된 자기개선 미션의 ID. 아직 미션이 생성되지 않았으면 null.",
          "default": null
        },
        "pattern_key": {
          "type": "string",
          "description": "유사한 Friction을 그룹화하기 위한 패턴 키. 동일 pattern_key의 Friction이 friction_threshold만큼 축적되면 자기개선 미션이 트리거된다. 예: 'mdx_parse_error', 'test_flaky_timeout', 'tailwind_class_conflict'.",
          "minLength": 1
        },
        "occurrence_count": {
          "type": "integer",
          "minimum": 1,
          "description": "이 패턴(pattern_key)의 누적 발생 횟수. 동일 패턴의 새 Friction이 발생하면 기존 레코드의 occurrence_count를 증가시키거나 새 레코드를 생성한다.",
          "default": 1
        },
        "resolved_at": {
          "type": ["string", "null"],
          "format": "date-time",
          "description": "마찰이 해소된 시점. ISO 8601 UTC. 미해소 상태이면 null.",
          "default": null
        },
        "resolved_by": {
          "type": ["string", "null"],
          "pattern": "^M-[0-9]{3,}$",
          "description": "이 Friction을 해소한 개선 미션 ID. 미해소 상태이면 null.",
          "default": null
        }
      }
    }
  }
}
```

### 검증 규칙

| 규칙 | 설명 |
|------|------|
| ID 고유성 | 모든 Friction의 id는 배열 내에서 고유해야 한다 |
| `next_id` 정합성 | next_id는 항상 현재 최대 Friction 번호 + 1 이상이어야 한다 |
| `source_mission_id` 참조 | null이 아닌 경우 missions.json에 존재해야 한다 |
| `improvement_mission_id` 참조 | null이 아닌 경우 missions.json에 존재해야 한다 |
| `resolution`과 `improvement_mission_id` 정합성 | improvement_mission_id가 설정되고 해당 미션이 completed이면 resolution도 설정되어 있어야 한다 |
| 축적 임계값 트리거 | 동일 pattern_key의 미해소 Friction 수가 Config.friction_threshold에 도달하면 자기개선 미션을 생성해야 한다 |
| `occurrence_count` 최소값 | 항상 1 이상이어야 한다 |
| `resolved_at` 정합성 | resolution이 설정되어 있으면 resolved_at도 설정되어 있어야 한다 |
| `resolved_by` 참조 | null이 아닌 경우 missions.json에 존재해야 한다 |

### 완전한 예시

```json
{
  "frictions": [
    {
      "id": "F-001",
      "type": "error",
      "description": "MDX 파일에서 잘못된 JSX 구문을 만나면 빌드 전체가 실패한다. 에러 메시지가 불명확하여 원인 파일을 찾기 어렵다.",
      "source_mission_id": "M-002",
      "source_session_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "timestamp": "2026-03-25T12:30:00Z",
      "severity": "high",
      "resolution": null,
      "improvement_mission_id": "M-004",
      "pattern_key": "mdx_parse_error",
      "occurrence_count": 3,
      "resolved_at": null,
      "resolved_by": null
    },
    {
      "id": "F-002",
      "type": "repeated_failure",
      "description": "MDX 내부의 인라인 코드 블록에서 꺾쇠괄호(<>)가 JSX로 해석되어 반복적으로 빌드 실패가 발생한다.",
      "source_mission_id": "M-002",
      "source_session_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "timestamp": "2026-03-25T12:45:00Z",
      "severity": "medium",
      "resolution": null,
      "improvement_mission_id": "M-004",
      "pattern_key": "mdx_parse_error",
      "occurrence_count": 2,
      "resolved_at": null,
      "resolved_by": null
    },
    {
      "id": "F-003",
      "type": "slow",
      "description": "전체 빌드에 45초 이상 소요된다. 변경 검증 사이클이 길어져 미션 실행 효율이 떨어진다.",
      "source_mission_id": "M-001",
      "source_session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "timestamp": "2026-03-25T11:00:00Z",
      "severity": "low",
      "resolution": "next.config.js에 incremental 빌드 설정을 추가하여 빌드 시간을 12초로 단축",
      "improvement_mission_id": null,
      "pattern_key": "slow_build",
      "occurrence_count": 1,
      "resolved_at": "2026-03-25T11:45:00Z",
      "resolved_by": "M-015"
    },
    {
      "id": "F-004",
      "type": "context_loss",
      "description": "세션 재시작 후 이전 세션에서 분석한 Tailwind 커스텀 클래스 목록을 다시 분석하는 중복 작업이 발생했다.",
      "source_mission_id": "M-003",
      "source_session_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "timestamp": "2026-03-25T13:10:00Z",
      "severity": "medium",
      "resolution": null,
      "improvement_mission_id": null,
      "pattern_key": "context_loss_after_restart",
      "occurrence_count": 1,
      "resolved_at": null,
      "resolved_by": null
    }
  ],
  "next_id": 5
}
```

---

## 5. Requests

**파일**: `state/requests.json`
**설명**: Owner에 대한 비동기 요청 추적. 시스템이 Owner에게 질문/확인/승인을 요청할 때 생성된다. 각 요청은 독립된 Slack 스레드로 전달된다(O-1, O-3).

### JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Requests",
  "description": "Owner 비동기 요청 추적",
  "type": "object",
  "required": ["requests", "next_id"],
  "additionalProperties": false,
  "properties": {
    "requests": {
      "type": "array",
      "description": "모든 요청 레코드 배열",
      "items": {
        "$ref": "#/$defs/Request"
      }
    },
    "next_id": {
      "type": "integer",
      "minimum": 1,
      "description": "다음 요청 생성 시 사용할 ID 번호.",
      "default": 1
    }
  },
  "$defs": {
    "Request": {
      "type": "object",
      "required": ["id", "type", "question", "answer", "slack_thread_ts", "status", "blocker_for", "created_at", "answered_at", "timeout_minutes"],
      "additionalProperties": false,
      "properties": {
        "id": {
          "type": "string",
          "pattern": "^R-[0-9]{3,}$",
          "description": "요청 고유 식별자. R-NNN 형식."
        },
        "type": {
          "type": "string",
          "enum": ["task_delegation", "question", "approval", "info"],
          "description": "요청 유형. task_delegation: Owner에게 작업을 위임 (시스템이 직접 수행 불가). question: Owner의 판단/의견이 필요한 질문. approval: 중요한 변경에 대한 승인 요청. info: 정보 제공 목적 (응답 불필요, 즉시 answered 처리)."
        },
        "question": {
          "type": "string",
          "description": "Owner에게 보낸 메시지 텍스트. 한국어로 작성된다(O-6).",
          "minLength": 1
        },
        "answer": {
          "type": ["string", "null"],
          "description": "Owner의 응답 텍스트. 아직 응답하지 않았으면 null. Owner가 Slack 스레드에 답변하면 Slack Client가 이 필드를 업데이트한다.",
          "default": null
        },
        "slack_thread_ts": {
          "type": ["string", "null"],
          "description": "Slack 메시지의 thread_ts 값. Slack 스레드 식별에 사용. Slack 전송 전이면 null.",
          "default": null
        },
        "status": {
          "type": "string",
          "enum": ["pending", "answered", "expired", "cancelled"],
          "description": "요청 상태. pending: Owner 응답 대기 중. answered: Owner가 응답 완료. expired: timeout_minutes 초과로 만료. cancelled: 시스템이 취소 (미션 취소 등으로).",
          "default": "pending"
        },
        "blocker_for": {
          "type": ["string", "null"],
          "pattern": "^M-[0-9]{3,}$",
          "description": "이 요청이 차단하고 있는 미션 ID. 요청이 answered되면 해당 미션의 blocker가 해제된다. 미션과 연관 없는 요청이면 null.",
          "default": null
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "description": "요청 생성 시각"
        },
        "answered_at": {
          "type": ["string", "null"],
          "format": "date-time",
          "description": "Owner가 응답한 시각. 아직 응답하지 않았으면 null.",
          "default": null
        },
        "timeout_minutes": {
          "type": "integer",
          "minimum": 0,
          "description": "응답 대기 제한 시간(분). 이 시간이 지나면 status가 expired로 전환된다. 0이면 무제한.",
          "default": 1440
        }
      }
    }
  }
}
```

### 검증 규칙

| 규칙 | 설명 |
|------|------|
| ID 고유성 | 모든 요청의 id는 배열 내에서 고유해야 한다 |
| `next_id` 정합성 | next_id는 항상 현재 최대 Request 번호 + 1 이상이어야 한다 |
| `answer` 정합성 | status가 `answered`이면 answer는 null이 아니어야 한다 |
| `answered_at` 정합성 | status가 `answered`이면 answered_at은 null이 아니어야 한다 |
| `blocker_for` 참조 | null이 아닌 경우 missions.json에 존재해야 한다 |
| `slack_thread_ts` 정합성 | status가 `pending` 또는 `answered`이면 slack_thread_ts는 null이 아니어야 한다 (Slack 전송이 완료된 상태) |
| 만료 처리 | Supervisor가 주기적으로 pending 요청의 `created_at + timeout_minutes`를 확인하여 만료 처리한다 |
| info 유형 자동 완료 | type이 `info`이면 생성 즉시 status를 `answered`로 설정한다 (응답 불필요) |
| Blocker 해제 연동 | status가 `answered`로 변경되면 blocker_for에 해당하는 미션의 blocker를 자동으로 해제한다 |

### 완전한 예시

```json
{
  "requests": [
    {
      "id": "R-001",
      "type": "question",
      "question": "블로그 디자인 시스템을 구축하려고 합니다. 선호하시는 색상 팔레트나 브랜드 가이드라인이 있으신가요? 없으시면 현재 사용 중인 색상을 기반으로 정리하겠습니다.",
      "answer": null,
      "slack_thread_ts": "1711360800.000100",
      "status": "pending",
      "blocker_for": "M-003",
      "created_at": "2026-03-25T13:00:00Z",
      "answered_at": null,
      "timeout_minutes": 1440
    },
    {
      "id": "R-002",
      "type": "approval",
      "question": "SEO 최적화를 위해 URL 구조를 /blog/[slug]에서 /blog/[category]/[slug]로 변경하는 것을 제안합니다. 기존 URL에 대한 리다이렉트를 설정하겠습니다. 진행해도 될까요?",
      "answer": "좋습니다. 다만 기존 URL 리다이렉트가 확실히 동작하는지 반드시 테스트해주세요.",
      "slack_thread_ts": "1711357200.000200",
      "status": "answered",
      "blocker_for": null,
      "created_at": "2026-03-25T12:00:00Z",
      "answered_at": "2026-03-25T14:30:00Z",
      "timeout_minutes": 1440
    },
    {
      "id": "R-003",
      "type": "info",
      "question": "M-001 (블로그 프로젝트 구조 분석) 미션이 완료되었습니다. Next.js 14 App Router 기반, Tailwind CSS, MDX 사용. Lighthouse 성능 점수 72점. 자세한 분석 결과는 state/missions.json의 M-001 result_summary를 참조하세요.",
      "answer": "(자동 완료 - 정보 제공용)",
      "slack_thread_ts": "1711350000.000300",
      "status": "answered",
      "blocker_for": null,
      "created_at": "2026-03-25T11:15:00Z",
      "answered_at": "2026-03-25T11:15:00Z",
      "timeout_minutes": 0
    }
  ],
  "next_id": 4
}
```

---

## 6. Sessions

**파일**: `state/sessions.json`
**설명**: Claude Code 세션 실행 이력. 각 세션은 하나의 미션을 실행하며, Supervisor가 세션 시작/종료/모니터링을 담당한다. 성능 분석과 디버깅에 사용한다.

### JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Sessions",
  "description": "Claude Code 세션 실행 이력",
  "type": "object",
  "required": ["sessions"],
  "additionalProperties": false,
  "properties": {
    "sessions": {
      "type": "array",
      "description": "모든 세션 이력 배열. 시간순으로 정렬.",
      "items": {
        "$ref": "#/$defs/Session"
      }
    }
  },
  "$defs": {
    "Session": {
      "type": "object",
      "required": ["id", "mission_id", "started_at", "ended_at", "exit_code", "exit_reason", "tokens_used", "compaction_count", "tool_calls_count", "errors", "result_summary"],
      "additionalProperties": false,
      "properties": {
        "id": {
          "type": "string",
          "description": "Claude Code가 발급한 세션 UUID. stream-json 출력의 session_id에서 추출."
        },
        "mission_id": {
          "type": ["string", "null"],
          "pattern": "^M-[0-9]{3,}$",
          "description": "이 세션이 실행한 미션 ID. 미션 할당 전에 세션이 종료된 경우(예: 즉시 크래시) null.",
          "default": null
        },
        "started_at": {
          "type": "string",
          "format": "date-time",
          "description": "세션 시작 시각 (claude 프로세스 실행 시점)"
        },
        "ended_at": {
          "type": ["string", "null"],
          "format": "date-time",
          "description": "세션 종료 시각. 아직 실행 중이면 null.",
          "default": null
        },
        "exit_code": {
          "type": ["integer", "null"],
          "description": "Claude Code 프로세스의 exit code. 정상 종료: 0. 에러: 1. 아직 실행 중이면 null.",
          "default": null
        },
        "exit_reason": {
          "type": ["string", "null"],
          "enum": ["completed", "crashed", "rate_limited", "timeout", "manual_stop", null],
          "description": "세션 종료 사유. completed: 미션 완료 또는 정상 종료. crashed: 비정상 종료 (프로세스 크래시). rate_limited: Rate limit으로 인한 종료. timeout: session_timeout_minutes 초과. manual_stop: Owner 또는 시스템에 의한 수동 중지. null: 아직 실행 중.",
          "default": null
        },
        "tokens_used": {
          "type": "object",
          "description": "세션에서 사용한 토큰 통계. stream-json 출력에서 집계.",
          "required": ["input", "output", "total"],
          "additionalProperties": false,
          "properties": {
            "input": {
              "type": "integer",
              "minimum": 0,
              "description": "입력(프롬프트) 토큰 총 수",
              "default": 0
            },
            "output": {
              "type": "integer",
              "minimum": 0,
              "description": "출력(응답) 토큰 총 수",
              "default": 0
            },
            "total": {
              "type": "integer",
              "minimum": 0,
              "description": "총 토큰 수 (input + output)",
              "default": 0
            }
          }
        },
        "compaction_count": {
          "type": "integer",
          "minimum": 0,
          "description": "세션 중 발생한 autocompact 횟수. context_refresh_after_compactions(Config) 임계값과 비교하여 세션 갱신 여부를 판단한다.",
          "default": 0
        },
        "tool_calls_count": {
          "type": "integer",
          "minimum": 0,
          "description": "세션 중 Claude가 실행한 tool call 총 횟수.",
          "default": 0
        },
        "errors": {
          "type": "array",
          "description": "세션 중 발생한 에러 요약 목록. Error Classifier가 분류한 결과.",
          "items": {
            "type": "object",
            "required": ["timestamp", "type", "message"],
            "additionalProperties": false,
            "properties": {
              "timestamp": {
                "type": "string",
                "format": "date-time",
                "description": "에러 발생 시각"
              },
              "type": {
                "type": "string",
                "description": "에러 분류 (Error Classifier 결과). 예: transient, rate_limit, auth, corruption, network, stuck",
                "examples": ["transient", "rate_limit", "auth", "corruption", "network", "stuck"]
              },
              "message": {
                "type": "string",
                "description": "에러 메시지 요약"
              }
            }
          }
        },
        "result_summary": {
          "type": ["string", "null"],
          "description": "세션 결과 요약. Claude의 최종 출력에서 추출하거나, 세션 모니터링에서 생성한다. 비정상 종료 시에도 가능한 한 기록한다.",
          "default": null
        }
      }
    }
  }
}
```

### 검증 규칙

| 규칙 | 설명 |
|------|------|
| ID 고유성 | 모든 세션의 id는 배열 내에서 고유해야 한다 |
| `ended_at` 정합성 | exit_code가 null이 아니면 ended_at도 null이 아니어야 한다 |
| `exit_code` 정합성 | ended_at이 null이 아니면 exit_code도 null이 아니어야 한다 |
| `exit_reason` 정합성 | ended_at이 null이 아니면 exit_reason도 null이 아니어야 한다 |
| `tokens_used.total` 정합성 | total은 항상 input + output과 같아야 한다 |
| `mission_id` 참조 | null이 아닌 경우 missions.json에 존재해야 한다 |
| 시간순 정렬 | sessions 배열은 started_at 기준으로 시간순 정렬되어야 한다 |
| 동시 활성 세션 제한 | ended_at이 null인 세션은 최대 1개만 존재할 수 있다 (시스템은 단일 세션만 실행) |

### 완전한 예시

```json
{
  "sessions": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "mission_id": "M-001",
      "started_at": "2026-03-25T10:31:00Z",
      "ended_at": "2026-03-25T11:15:00Z",
      "exit_code": 0,
      "exit_reason": "completed",
      "tokens_used": {
        "input": 125000,
        "output": 48000,
        "total": 173000
      },
      "compaction_count": 2,
      "tool_calls_count": 87,
      "errors": [],
      "result_summary": "블로그 프로젝트 구조 분석 완료. Next.js 14, Tailwind CSS, MDX 기반. Lighthouse 72점. 상세 분석 결과를 미션 result_summary에 기록."
    },
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "mission_id": "M-002",
      "started_at": "2026-03-25T11:20:00Z",
      "ended_at": null,
      "exit_code": null,
      "exit_reason": null,
      "tokens_used": {
        "input": 89000,
        "output": 31000,
        "total": 120000
      },
      "compaction_count": 1,
      "tool_calls_count": 52,
      "errors": [
        {
          "timestamp": "2026-03-25T12:30:00Z",
          "type": "transient",
          "message": "MDX 빌드 실패: Unexpected token '<' in inline code block (posts/react-tips.mdx:42)"
        }
      ],
      "result_summary": null
    }
  ]
}
```

---

## 7. Config

**파일**: `state/config.toml`
**설명**: 동적 설정. 시스템의 운영 파라미터와 임계값을 정의한다. 시스템(Claude Code)이 자기개선의 일환으로 이 설정을 직접 수정할 수 있다(S-5). 모든 값은 수정 가능하다. TOML 형식을 사용하여 사람과 AI 모두가 읽기 쉽고 주석으로 변경 근거를 기록할 수 있다.

### 스키마 정의

TOML은 공식 스키마 언어가 없으므로 아래 표로 필드 타입과 제약을 정의한다.

| 키 | 타입 | 필수 | 기본값 | 제약 | 설명 |
|----|------|------|--------|------|------|
| `friction_threshold` | integer | Y | `3` | >= 1 | 동일 pattern_key의 미해소 Friction이 이 수만큼 축적되면 자기개선 미션을 자동 생성한다(S-2). 값이 낮으면 빠르게 개선하지만 미션 큐가 무거워진다. 값이 높으면 심각한 문제만 개선한다. |
| `proactive_improvement_interval` | integer | Y | `10` | >= 1 | 이 미션 수마다 Friction 없이도 사전 개선 미션을 생성한다(S-3). 시스템 전반을 검토하고 개선점을 찾는 미션이 생성된다. |
| `context_refresh_after_compactions` | integer | Y | `5` | >= 1 | 세션 내 autocompact가 이 횟수에 도달하면 Stop Hook이 세션 종료를 허용하고 Fresh Session으로 컨텍스트를 갱신한다. 컨텍스트 품질 저하를 방지한다. |
| `goal_drift_check_interval` | integer | Y | `20` | >= 1 | 이 미션 수마다 Purpose와 현재 활동 방향의 정합성을 검증한다. 목표 드리프트를 감지하면 전략을 재정렬한다. |
| `session_timeout_minutes` | integer | Y | `120` | >= 1 | 단일 세션의 최대 실행 시간(분). 이 시간이 지나면 Supervisor가 세션을 강제 종료한다. 무한 실행을 방지한다. |
| `max_consecutive_failures` | integer | Y | `3` | >= 1 | 연속 세션 실패 허용 횟수. 이 횟수를 초과하면 Supervisor가 Owner에게 긴급 알림을 보내고 시스템을 일시 중지한다. |
| `slack_notification_level` | string | Y | `"warning"` | `"info"`, `"warning"`, `"error"`, `"critical"` 중 하나 | Slack 알림 최소 레벨. 이 레벨 이상의 이벤트만 Owner에게 알린다. |
| `mission_idle_generation_count` | integer | Y | `3` | >= 1 | 미션 큐가 비었을 때(P-3) Claude에게 한 번에 생성하도록 요청하는 미션 수. |
| `owner_feedback_interval` | integer | Y | `20` | >= 1 | 이 미션 수 동안 Owner와 상호작용이 없으면 Supervisor가 자동으로 방향 확인 피드백을 요청한다. 인간 앵커로 기능한다. |
| `all_thresholds_modifiable` | boolean | Y | `true` | 항상 `true` (변경 불가) | 시스템(Claude Code)이 이 파일의 모든 값을 수정할 수 있는지 여부. 자기개선(S-5)의 핵심 원칙. |

### 검증 규칙

| 규칙 | 설명 |
|------|------|
| `all_thresholds_modifiable` 불변 | 항상 `true`. 이 값은 절대 변경할 수 없다 |
| 모든 정수 필드 최소값 | 모든 정수 필드는 1 이상이어야 한다 (0 이하 불허) |
| `slack_notification_level` 유효값 | `info`, `warning`, `error`, `critical` 중 하나만 허용 |
| 설정 변경 로깅 | Config 변경 시 TOML 주석(`#`)으로 변경 근거를 기록하고, git commit 메시지에도 변경 내역을 명시해야 한다 |
| 합리성 검증 | session_timeout_minutes는 10 이상을 권장 (너무 짧으면 미션 완료 불가) |
| 합리성 검증 | friction_threshold는 1~10 범위를 권장 (너무 높으면 개선이 지연) |
| TOML 구문 | 파일은 유효한 TOML이어야 한다. Python의 `tomllib`(읽기) / `tomli_w`(쓰기)로 처리한다 |

### 완전한 예시

```toml
# claude-automata 동적 설정
# 시스템(Claude Code)이 자기개선의 일환으로 이 값들을 직접 수정할 수 있다 (S-5)
# 값을 변경할 때는 반드시 주석으로 변경 근거를 기록한다

# Friction 축적 임계값 (S-2)
# 동일 pattern_key의 미해소 Friction이 이 수만큼 쌓이면 자기개선 미션 자동 생성
friction_threshold = 3

# 사전 개선 주기 (S-3)
# 이 미션 수마다 시스템 전반 검토 미션 생성
proactive_improvement_interval = 10

# 컨텍스트 리프레시 기준
# autocompact가 이 횟수에 도달하면 Fresh Session으로 전환
context_refresh_after_compactions = 5

# 목표 드리프트 검사 주기
# 이 미션 수마다 Purpose와 현재 방향의 정합성 검증
goal_drift_check_interval = 20

# 세션 타임아웃 (분)
# 이 시간 초과 시 Supervisor가 강제 종료
session_timeout_minutes = 120

# 연속 실패 허용 횟수
# 초과 시 Owner 긴급 알림 + 시스템 일시 중지
max_consecutive_failures = 3

# Slack 알림 최소 레벨: "info" | "warning" | "error" | "critical"
slack_notification_level = "warning"

# 빈 큐 시 자율 생성 미션 수 (P-3)
mission_idle_generation_count = 3

# Owner 피드백 주기
# 이 미션 수 동안 Owner 상호작용이 없으면 방향 확인 요청
owner_feedback_interval = 20

# 자기개선 허용 플래그 - 이 값은 절대 false로 변경 불가
all_thresholds_modifiable = true
```

---

## 8. Current Session

**파일**: `run/current_session.json`
**설명**: 현재 실행 중인 Claude Code 세션의 런타임 정보. Supervisor가 실시간으로 갱신하며, TUI 대시보드와 Watchdog이 읽는다. 세션이 없으면 파일이 존재하지 않거나 빈 상태이다. `run/` 디렉토리에 위치하므로 Git에서 제외된다.

### JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CurrentSession",
  "description": "현재 활성 세션 런타임 정보",
  "type": "object",
  "required": ["session_id", "mission_id", "started_at", "pid", "status", "last_event_at", "compaction_count", "stream_position"],
  "additionalProperties": false,
  "properties": {
    "session_id": {
      "type": "string",
      "description": "현재 실행 중인 Claude Code 세션 UUID"
    },
    "mission_id": {
      "type": ["string", "null"],
      "pattern": "^M-[0-9]{3,}$",
      "description": "현재 실행 중인 미션 ID. 미션 할당 전이면 null.",
      "default": null
    },
    "started_at": {
      "type": "string",
      "format": "date-time",
      "description": "세션 시작 시각"
    },
    "pid": {
      "type": "integer",
      "minimum": 1,
      "description": "Claude Code 프로세스의 PID. Supervisor가 프로세스 상태를 모니터링하는 데 사용."
    },
    "status": {
      "type": "string",
      "enum": ["running", "rate_limited", "stopping"],
      "description": "세션 상태. running: 정상 실행 중. rate_limited: Rate limit 감지, 대기 중. stopping: 종료 진행 중.",
      "default": "running"
    },
    "last_event_at": {
      "type": "string",
      "format": "date-time",
      "description": "마지막 stream-json 이벤트 수신 시각. Watchdog이 이 값과 현재 시각의 차이로 세션 응답성을 판단한다. 일정 시간 이상 갱신이 없으면 세션이 stuck 상태로 간주된다."
    },
    "compaction_count": {
      "type": "integer",
      "minimum": 0,
      "description": "현재 세션에서 발생한 autocompact 횟수. context_refresh_after_compactions(Config)와 비교하여 세션 갱신 판단에 사용.",
      "default": 0
    },
    "stream_position": {
      "type": "integer",
      "minimum": 0,
      "description": "stream-json 출력에서 마지막으로 처리한 바이트 위치. 크래시 후 복구 시 중복 처리를 방지한다.",
      "default": 0
    }
  }
}
```

### 검증 규칙

| 규칙 | 설명 |
|------|------|
| PID 유효성 | pid가 가리키는 프로세스가 실제 존재해야 한다 (Watchdog이 주기적 검증) |
| `last_event_at` 신선도 | `현재시각 - last_event_at`이 session_timeout_minutes를 초과하면 stuck으로 간주 |
| 파일 생명주기 | 세션 시작 시 생성, 세션 종료 시 삭제. 비정상 종료 시 Supervisor 재시작 시 정리 |
| 단일 파일 | 시스템은 단일 세션만 실행하므로 이 파일은 항상 하나만 존재 |

### 완전한 예시

```json
{
  "session_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "mission_id": "M-002",
  "started_at": "2026-03-25T11:20:00Z",
  "pid": 54321,
  "status": "running",
  "last_event_at": "2026-03-25T14:52:30Z",
  "compaction_count": 1,
  "stream_position": 2457600
}
```

---

## 9. Heartbeat

**파일**: `run/supervisor.heartbeat`
**설명**: Supervisor의 헬스체크 파일. Supervisor가 주기적(5초)으로 갱신하며, Watchdog(launchd LaunchAgent)이 읽어 Supervisor의 생존을 확인한다(E-4). JSON 형식이지만 확장자는 `.heartbeat`로 구분한다.

### JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Heartbeat",
  "description": "Supervisor heartbeat (Watchdog 모니터링용)",
  "type": "object",
  "required": ["pid", "timestamp", "state", "children", "uptime_seconds", "current_mission_id"],
  "additionalProperties": false,
  "properties": {
    "pid": {
      "type": "integer",
      "minimum": 1,
      "description": "Supervisor 프로세스의 PID"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "이 heartbeat가 기록된 시각. Watchdog은 이 값과 현재 시각의 차이로 Supervisor 생존을 판단한다."
    },
    "state": {
      "type": "string",
      "enum": ["starting", "running", "launching_session", "monitoring", "recovering", "shutting_down"],
      "description": "Supervisor의 현재 상태. starting: 초기화 중. running: 정상 실행 (세션 간 유휴). launching_session: Claude Code 세션 시작 중. monitoring: 활성 세션 모니터링 중. recovering: 에러 복구 진행 중. shutting_down: 종료 진행 중."
    },
    "children": {
      "type": "array",
      "description": "Supervisor가 관리하는 자식 프로세스 PID 목록. 주로 Claude Code 프로세스. Watchdog이 고아 프로세스를 감지하는 데 사용.",
      "items": {
        "type": "integer",
        "minimum": 1
      }
    },
    "uptime_seconds": {
      "type": "number",
      "minimum": 0,
      "description": "Supervisor의 가동 시간(초). Supervisor 시작 시점부터 현재까지의 경과 시간."
    },
    "current_mission_id": {
      "type": ["string", "null"],
      "pattern": "^M-[0-9]{3,}$",
      "description": "현재 실행 중인 미션 ID. 활성 세션이 없으면 null.",
      "default": null
    }
  }
}
```

### 검증 규칙

| 규칙 | 설명 |
|------|------|
| PID 유효성 | pid가 가리키는 프로세스가 실제 Supervisor이어야 한다 |
| `timestamp` 신선도 | Watchdog은 `현재시각 - timestamp`가 30초를 초과하면 Supervisor 사망으로 간주 |
| `children` PID 유효성 | 나열된 PID가 실제 존재하는 프로세스여야 한다. Watchdog이 Supervisor 사망 시 고아 프로세스를 정리 |
| 갱신 주기 | Supervisor는 5초마다 이 파일을 갱신해야 한다 |
| 파일 생명주기 | Supervisor 시작 시 생성, 종료 시 삭제. 비정상 종료 시 파일이 남아 있을 수 있으므로 timestamp 신선도로 판단 |

### 완전한 예시

```json
{
  "pid": 12345,
  "timestamp": "2026-03-25T14:52:35Z",
  "state": "monitoring",
  "children": [54321],
  "uptime_seconds": 16355.0,
  "current_mission_id": "M-002"
}
```

---

## 10. Supervisor State

**파일**: `run/supervisor.state`
**설명**: Supervisor의 영속적 상태. 크래시 복구에 사용된다. Supervisor가 재시작될 때 이 파일을 읽어 이전 상태를 복원한다. JSON 형식이지만 확장자는 `.state`로 구분한다.

### JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SupervisorState",
  "description": "Supervisor 영속적 상태 (크래시 복구용)",
  "type": "object",
  "required": [
    "restart_count",
    "last_restart_at",
    "consecutive_failures",
    "last_successful_session_at",
    "total_sessions",
    "total_missions_completed"
  ],
  "additionalProperties": false,
  "properties": {
    "restart_count": {
      "type": "integer",
      "minimum": 0,
      "description": "Supervisor가 재시작된 총 횟수. launchd에 의한 자동 재시작 포함. 시스템 안정성 지표.",
      "default": 0
    },
    "last_restart_at": {
      "type": ["string", "null"],
      "format": "date-time",
      "description": "마지막 재시작 시각. 한 번도 재시작하지 않았으면 null.",
      "default": null
    },
    "consecutive_failures": {
      "type": "integer",
      "minimum": 0,
      "description": "연속 세션 실패 횟수. 세션 성공 시 0으로 리셋. max_consecutive_failures(Config) 초과 시 시스템 일시 중지 및 Owner 긴급 알림.",
      "default": 0
    },
    "last_successful_session_at": {
      "type": ["string", "null"],
      "format": "date-time",
      "description": "마지막으로 세션이 성공적으로 완료된 시각. 한 번도 성공하지 않았으면 null. 시스템 건강 상태 지표.",
      "default": null
    },
    "total_sessions": {
      "type": "integer",
      "minimum": 0,
      "description": "실행된 총 세션 수. sessions.json의 배열 크기와 일치해야 한다.",
      "default": 0
    },
    "total_missions_completed": {
      "type": "integer",
      "minimum": 0,
      "description": "완료된 총 미션 수. missions.json의 metadata.total_completed와 일치해야 한다.",
      "default": 0
    }
  }
}
```

### 검증 규칙

| 규칙 | 설명 |
|------|------|
| `total_sessions` 정합성 | sessions.json의 sessions 배열 크기와 일치해야 한다 |
| `total_missions_completed` 정합성 | missions.json의 metadata.total_completed와 일치해야 한다 |
| `consecutive_failures` 리셋 | 세션이 성공(exit_reason: completed)하면 0으로 리셋한다 |
| `consecutive_failures` 임계값 | max_consecutive_failures(Config) 초과 시 Owner 긴급 알림 + 시스템 일시 중지 |
| `restart_count` 단조 증가 | 항상 증가만 한다. 감소하지 않는다 |
| 파일 생명주기 | 최초 Supervisor 실행 시 생성 (기존 파일 없으면). 이후 Supervisor 종료/재시작에 관계없이 보존 |
| 원자적 쓰기 | 크래시 복구에 사용되므로 반드시 원자적으로 쓰기해야 한다 |

### 완전한 예시

```json
{
  "restart_count": 2,
  "last_restart_at": "2026-03-25T09:15:00Z",
  "consecutive_failures": 0,
  "last_successful_session_at": "2026-03-25T11:15:00Z",
  "total_sessions": 5,
  "total_missions_completed": 3
}
```

---

## 엔티티 관계도

```
                    ┌──────────────────────────────────────────┐
                    │              Purpose                      │
                    │         state/purpose.json                │
                    └────────────────┬─────────────────────────┘
                                     │ 방향 제공
                                     ▼
                    ┌──────────────────────────────────────────┐
                    │              Strategy                     │
                    │         state/strategy.json               │
                    └────────────────┬─────────────────────────┘
                                     │ 미션 생성 가이드
                                     ▼
┌───────────────┐   ┌──────────────────────────────────────────┐
│   Friction    │──▶│              Missions                     │
│state/friction │   │         state/missions.json               │
│   .json       │◀──│                                          │
└───────┬───────┘   └────────┬──────────────┬──────────────────┘
        │                    │              │
        │ 발생 기록          │ 실행         │ Blocker 생성
        │                    ▼              ▼
        │           ┌──────────────┐ ┌─────────────────┐
        │           │   Sessions   │ │    Requests     │
        │           │state/sessions│ │ state/requests  │
        │           │   .json      │ │    .json        │
        │           └──────┬───────┘ └─────────────────┘
        │                  │                    │
        │                  │ 런타임 상태        │ Slack 통신
        │                  ▼                    ▼
        │           ┌──────────────┐    ┌──────────────┐
        │           │Current Sess. │    │    Slack      │
        │           │run/current_  │    │  Workspace    │
        │           │session.json  │    └──────────────┘
        │           └──────────────┘
        │
        │ 임계값 참조
        ▼
┌───────────────┐   ┌──────────────┐   ┌──────────────────┐
│    Config     │   │  Heartbeat   │   │ Supervisor State │
│ state/config  │   │run/supervisor│   │  run/supervisor  │
│   .toml       │   │ .heartbeat   │   │     .state       │
└───────────────┘   └──────────────┘   └──────────────────┘
        ▲                   ▲                   ▲
        │                   │                   │
        └───────── Supervisor (Python 데몬) ────┘
```

### 엔티티 간 참조 관계

| 출발 엔티티 | 참조 필드 | 대상 엔티티 | 관계 설명 |
|-------------|-----------|-------------|-----------|
| Mission | `session_id` | Session | 미션을 실행한 세션 |
| Mission | `dependencies` | Mission | 선행 미션 |
| Mission | `blockers[].request_id` | Request | 미션을 차단하는 요청 |
| Mission | `friction_ids` | Friction | 미션 실행 중 발생한 Friction |
| Friction | `source_mission_id` | Mission | Friction이 발생한 미션 |
| Friction | `source_session_id` | Session | Friction이 발생한 세션 |
| Friction | `improvement_mission_id` | Mission | Friction 해소를 위한 자기개선 미션 |
| Request | `blocker_for` | Mission | 요청이 차단하는 미션 |
| Session | `mission_id` | Mission | 세션이 실행한 미션 |
| Current Session | `mission_id` | Mission | 현재 실행 중인 미션 |
| Heartbeat | `current_mission_id` | Mission | 현재 실행 중인 미션 |

---

## 초기 상태 (부트스트랩)

`acc configure` 완료 후, Initialization Session 실행 전의 초기 상태이다. Initialization Session이 이 파일들을 채운다.

### `state/purpose.json` (초기)
```json
{
  "raw_input": "",
  "purpose": "",
  "domain": "",
  "key_directions": [],
  "constructed_at": "",
  "last_evolved_at": "",
  "evolution_history": []
}
```
> Note: raw_input은 `acc configure`에서 설정. 나머지는 Initialization Session이 채운다.

### `state/strategy.json` (초기)
```json
{
  "summary": "",
  "approach": "",
  "skills": [],
  "principles": [],
  "created_at": "",
  "last_evolved_at": "",
  "evolution_count": 0
}
```

### `state/missions.json` (초기)
```json
{
  "missions": [],
  "next_id": 1,
  "metadata": {
    "total_created": 0,
    "total_completed": 0,
    "total_failed": 0,
    "total_blocked": 0
  }
}
```

### `state/friction.json` (초기)
```json
{
  "frictions": [],
  "next_id": 1
}
```

### `state/requests.json` (초기)
```json
{
  "requests": [],
  "next_id": 1
}
```

### `state/sessions.json` (초기)
```json
{
  "sessions": []
}
```

### `state/config.toml` (초기 = 기본값)
```toml
friction_threshold = 3
proactive_improvement_interval = 10
context_refresh_after_compactions = 5
goal_drift_check_interval = 20
session_timeout_minutes = 120
max_consecutive_failures = 3
slack_notification_level = "warning"
mission_idle_generation_count = 3
all_thresholds_modifiable = true
```

### `run/supervisor.state` (초기)
```json
{
  "restart_count": 0,
  "last_restart_at": null,
  "consecutive_failures": 0,
  "last_successful_session_at": null,
  "total_sessions": 0,
  "total_missions_completed": 0
}
```

> `run/current_session.json`과 `run/supervisor.heartbeat`는 런타임에만 존재하므로 초기 상태 파일은 없다.

---

## 11. Archive Files

**디렉토리**: `state/archive/`
**설명**: 운영 상태 파일(missions.json, friction.json, sessions.json)이 일정 크기를 초과하면 완료/해소된 레코드를 아카이브 파일로 이동한다. JSONL(JSON Lines) 형식을 사용하여 한 줄에 하나의 완전한 JSON 객체를 저장한다. Git으로 추적한다.

### JSONL 형식 규약

- 파일 확장자: `.jsonl`
- 각 줄은 독립적이고 완전한 JSON 객체이다 (줄바꿈으로 구분)
- 각 줄의 스키마는 원본 활성 파일의 개별 레코드 스키마와 동일하다
- 아카이브 시점을 기록하는 `archived_at` 필드가 각 레코드에 추가된다
- 파일 내 레코드는 아카이브된 순서(시간순)로 정렬된다

### 아카이브 파일 명명 규칙

| 원본 파일 | 아카이브 파일명 패턴 | 주기 | 예시 |
|-----------|---------------------|------|------|
| `state/missions.json` | `missions-{YYYY}-Q{N}.jsonl` | 분기별 | `missions-2026-Q1.jsonl` |
| `state/friction.json` | `friction-{YYYY}-Q{N}.jsonl` | 분기별 | `friction-2026-Q2.jsonl` |
| `state/sessions.json` | `sessions-{YYYY}-{MM}.jsonl` | 월별 | `sessions-2026-03.jsonl` |

### 로테이션 규칙

| 원본 파일 | 로테이션 조건 | 아카이브 대상 |
|-----------|--------------|--------------|
| `state/missions.json` | 완료(`completed`) + 실패(`failed`) 미션이 **50개** 이상 | `status`가 `completed` 또는 `failed`인 미션 |
| `state/friction.json` | 해소(`resolved`) friction이 **100개** 이상 | `status`가 `resolved`인 friction |
| `state/sessions.json` | 세션 레코드가 **100개** 이상 | 가장 오래된 레코드부터 활성 파일에 최근 20개만 유지 |

### 로테이션 프로세스

1. State Manager가 파일 쓰기 시 로테이션 조건을 확인한다
2. 조건 충족 시 아카이브 대상 레코드를 추출한다
3. 해당 분기/월의 아카이브 파일에 JSONL 형식으로 **append**한다
4. 각 레코드에 `archived_at` (ISO 8601 UTC) 필드를 추가한다
5. 원본 활성 파일에서 아카이브된 레코드를 제거한다
6. 원본 파일의 metadata(next_id 등)는 유지한다
7. 아카이브 쓰기와 원본 갱신을 원자적으로 수행한다 (아카이브 먼저 쓰고, 성공 시 원본 갱신)

### 아카이브 레코드 예시

**missions-2026-Q1.jsonl** (각 줄이 하나의 미션):
```jsonl
{"id":"M-001","title":"초기 블로그 분석","status":"completed","archived_at":"2026-03-25T12:00:00Z",...}
{"id":"M-002","title":"SEO 메타데이터 추가","status":"completed","archived_at":"2026-03-25T12:00:00Z",...}
```

**friction-2026-Q1.jsonl** (각 줄이 하나의 friction):
```jsonl
{"id":"F-001","pattern_key":"test_timeout","status":"resolved","archived_at":"2026-03-25T12:00:00Z",...}
```

**sessions-2026-03.jsonl** (각 줄이 하나의 세션):
```jsonl
{"session_id":"a1b2c3d4-...","started_at":"2026-03-25T10:00:00Z","exit_reason":"completed","archived_at":"2026-03-25T12:00:00Z",...}
```

### 검증 규칙

| 규칙 | 설명 |
|------|------|
| 스키마 동일성 | 아카이브 레코드는 `archived_at` 필드 추가를 제외하고 원본 스키마와 동일하다 |
| 원자적 로테이션 | 아카이브 파일 쓰기 성공 후에만 원본에서 레코드를 제거한다 |
| ID 보존 | 아카이브된 레코드의 ID는 재사용하지 않는다 (next_id는 계속 증가) |
| 파일명 정합성 | 아카이브 파일명의 날짜는 로테이션 실행 시점의 UTC 기준 분기/월이다 |
| Append-only | 아카이브 파일은 append만 허용한다. 기존 내용을 수정하거나 삭제하지 않는다 |
