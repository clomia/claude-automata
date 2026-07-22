claude-automata는 자신이 배포하는 plugin을 이 머신에서 dogfooding한다. `claude plugin
install|uninstall|update`·`uvx claude-automata init`은 머신-전역
`~/.claude/plugins/installed_plugins.json`(모든 project가 공유하는 install 레지스트리)을
재작성하고, 동시 session과 race하면 형제 project의 install record를 clobber한다 — 이 repo
개발이 실제로 형제 project들을 깨뜨렸다.

**plugin 편집 테스트는 install하지 말고 세션-한정 로드를 써라** (공식 방식):

    claude --plugin-dir ./plugins/ploop     # 반복 지정으로 여러 개: --plugin-dir A --plugin-dir B

레지스트리에 아무것도 쓰지 않고 working-tree 편집을 그대로 로드한다(반영은 `/reload-plugins`).

`init`의 설치 흐름 자체를 end-to-end로 검증할 때만(드묾) 실제 `claude plugin install`이 돈다 —
그땐 `CLAUDE_CONFIG_DIR=<빈 dir>`로 격리하라. 자동 test는 `run_claude`를 monkeypatch하므로 실
CLI를 안 부른다.
