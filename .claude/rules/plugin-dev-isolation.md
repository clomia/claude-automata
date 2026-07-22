claude-automata는 자신이 배포하는 plugin을 이 머신에서 dogfooding한다. 그래서
`claude plugin install|uninstall|update`·`uvx claude-automata init`을 실행하면 머신-전역
`~/.claude/plugins/installed_plugins.json`(모든 project가 공유하는 install 레지스트리)을
재작성한다. 동시 session이 이 파일을 race하면 형제 project의 install record가 소실되며, 이 repo를
개발하며 실제로 형제 project들을 그렇게 깨뜨렸다.

그러니 dev·test로 plugin을 mutate할 땐 격리된 config에서 하라:

    scripts/dev-sandbox.sh <command>

이는 `CLAUDE_CONFIG_DIR`을 repo-local sandbox로 돌려 모든 write를 격리한다. 자동 test는
`run_claude`를 monkeypatch하므로 실 CLI를 부르지 않아 이미 안전하다.
