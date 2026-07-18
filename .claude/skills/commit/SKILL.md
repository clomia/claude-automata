---
name: commit
description: 전체 변경사항을 git commit 한다. (push 인수로 push까지 수행)
disable-model-invocation: true
model: haiku
argument-hint: "[push]"
---

별도의 지시가 없으면 전체 변경사항을 `git commit` 하라. **untracked 파일을 남기지 마라.**
변경사항이 없으면 아무 작업도 하지 말고 무시하라.

- base 브랜치(GitHub 기본 브랜치) 위에서는 커밋하지 마라 — 변경은 트랜잭션(`/tx:open`)으로 시작하라.
- 커밋 형식은 [Conventional Commits 가이드](conventional-commits.md)를 따르라.
- git 커맨드로 변경사항을 이해한 뒤 직관적인 커밋 메시지를 작성하라.
- 커밋 메시지는 영어로 작성하라.
- 모든 변경사항을 하나의 commit으로 묶지 않아도 된다.
- **인수가 `push`이면 커밋 완료 후 `git push`까지 수행하라. (변경사항이 없으면 `git push`만 수행)**

인수: $ARGUMENTS
