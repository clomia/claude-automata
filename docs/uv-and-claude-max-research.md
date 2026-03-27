# Research: uv Package Manager & Claude Max Subscription

Date: 2026-03-25

---

## Topic 1: uv Package Manager with Python 3.14

### 1.1 Current uv Version and Features

**Latest version: uv 0.11.1** (released March 24, 2026)

uv is an extremely fast Python package and project manager written in Rust by Astral (makers of Ruff). It achieves 10-100x faster operations compared to pip.

**Key commands:**

| Command | Purpose |
|---------|---------|
| `uv init` | Create a new project |
| `uv add <pkg>` | Add a dependency |
| `uv remove <pkg>` | Remove a dependency |
| `uv run <script>` | Run a script in the project environment |
| `uv sync` | Sync environment with lockfile |
| `uv lock` | Generate/update lockfile |
| `uv build` | Build source and wheel distributions |
| `uv python install` | Install a Python version |
| `uv python pin` | Pin a Python version for the project |
| `uv tool install` | Install a CLI tool globally |
| `uvx` / `uv tool run` | Run a tool ephemerally (like npx) |
| `uv version` | Show project version |

### 1.2 Python 3.14 Support

**Python 3.14 status: RELEASED (stable)**

- Python 3.14.0 was released on October 7, 2025
- Current latest: Python 3.14.3 (released February 3, 2026)
- Support timeline: bugfix updates until ~October 2027, security updates until ~October 2030
- Key features: template string literals, deferred evaluation of annotations, subinterpreters in stdlib

**uv fully supports Python 3.14**, including:

```bash
# Install Python 3.14
uv python install 3.14

# Or a specific patch version
uv python install 3.14.3

# Free-threaded build (no GIL)
uv python install 3.14t
```

By default, uv automatically downloads Python versions when required -- you do not need to pre-install them. If you run `uv run` and the required Python is not present, uv downloads it.

For Python 3.14+, free-threaded interpreters work in virtual environments without additional opt-in, though the GIL-enabled build remains the default.

### 1.3 Project Structure

**Initialize a new project:**

```bash
# Application (default)
uv init my-project

# Packaged application (with entry points)
uv init --package my-project

# Library (src layout, for PyPI distribution)
uv init --lib my-project

# Minimal (just pyproject.toml)
uv init --bare my-project
```

**Generated file structure (application):**

```
my-project/
  .python-version      # Pinned Python version
  .gitignore
  README.md
  main.py              # Entry point
  pyproject.toml       # Project configuration
```

**Generated file structure (packaged application):**

```
my-project/
  .python-version
  .gitignore
  README.md
  pyproject.toml
  src/
    my_project/
      __init__.py
```

**Typical pyproject.toml for an application:**

```toml
[project]
name = "my-project"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.14"
dependencies = []
```

**Typical pyproject.toml for a packaged application with entry points:**

```toml
[project]
name = "my-project"
version = "0.1.0"
description = "An autonomous Claude Code system"
readme = "README.md"
requires-python = ">=3.14"
dependencies = [
    "click>=8.0",
    "rich>=13.0",
]

[project.scripts]
my-cli = "my_project:main"

[project.entry-points.'my_project.plugins']
plugin-a = "my_project_plugin_a"

[build-system]
requires = ["uv_build>=0.11.1,<0.12"]
build-backend = "uv_build"

[tool.uv]
# uv-specific configuration goes here
```

### 1.4 Script Execution

**Run scripts with `uv run`:**

```bash
# Run a Python script
uv run main.py

# Run a module
uv run -m pytest

# Run a command provided by a dependency
uv run -- flask run -p 3000

# Run an entry point defined in [project.scripts]
uv run my-cli
```

Before each invocation, `uv run` verifies that the lockfile is up-to-date with pyproject.toml and syncs the environment automatically.

**Entry points** are defined in `[project.scripts]`:

```toml
[project.scripts]
hello = "my_package:hello"        # CLI entry point
my-tool = "my_package.cli:main"   # CLI with submodule
```

After defining entry points in a `--package` project, `uv run hello` executes the `hello()` function from `my_package`.

### 1.5 Dependency Management

**Adding dependencies:**

```bash
# Add a package
uv add requests

# Add with version constraint
uv add 'requests==2.31.0'
uv add 'requests>=2.28,<3.0'

# Add with extras
uv add 'httpx[http2,brotli]'

# Add a dev dependency
uv add --dev pytest
uv add --dev ruff

# Add from git
uv add git+https://github.com/user/repo

# Add from requirements.txt
uv add -r requirements.txt -c constraints.txt
```

**Lock file (`uv.lock`):**

- Cross-platform lockfile in human-readable TOML format
- Contains exact resolved versions of all dependencies
- Should be committed to version control for reproducible builds
- Never edit manually -- managed entirely by uv
- Updated automatically by `uv lock` or `uv add`/`uv remove`

```bash
# Generate/update lockfile
uv lock

# Upgrade a specific package in the lockfile
uv lock --upgrade-package requests

# Upgrade all packages
uv lock --upgrade
```

**Dependency groups in pyproject.toml:**

```toml
[project]
dependencies = [
    "requests>=2.28",
    "click>=8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "ruff>=0.1.0",
]

[dependency-groups]
test = ["pytest>=7.0", "coverage"]
lint = ["ruff>=0.1.0", "mypy"]
```

### 1.6 Virtual Environment

**Location:** uv creates a `.venv` directory in the project root by default.

```
my-project/
  .venv/
    bin/          # Executables (python, pip, etc.)
    lib/          # Installed packages
    pyvenv.cfg   # Venv configuration
```

**Customizing location:** Set `UV_PROJECT_ENVIRONMENT` environment variable to override the default `.venv` path.

**Activation (optional -- `uv run` makes this unnecessary):**

```bash
# macOS/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

# Or skip activation entirely and use uv run
uv run python my_script.py
```

**Sync the environment explicitly:**

```bash
uv sync              # Install all dependencies
uv sync --frozen     # Use existing lockfile without updating
```

### 1.7 uv tool: Installing CLI Tools Globally

`uv tool install` installs Python CLI tools in isolated environments with executables on PATH (similar to pipx):

```bash
# Install a tool globally
uv tool install ruff
uv tool install mypy

# Install with extras
uv tool install 'mypy[faster-cache,reports]'

# Install with additional dependencies
uv tool install mkdocs --with mkdocs-material

# Install with specific Python version
uv tool install --python 3.14 aider-chat

# Upgrade a tool
uv tool upgrade ruff
uv tool upgrade --all

# Run a tool ephemerally (like npx)
uvx ruff check
uvx --from httpie http    # When package name differs from command

# Run specific version
uvx ruff@0.6.0 check
uvx ruff@latest check
```

**Tool directories:**

- Tool environments: `~/.local/share/uv/tools/<tool-name>/`
- Binaries: `~/.local/bin/` (must be on PATH)

Important: tools installed via `uv tool install` do NOT expose their modules to the current Python environment. They are fully isolated.

### 1.8 Integration with Claude Code

**Known considerations:**

- uv is the recommended way to manage Python projects that Claude Code works with
- Claude Code can run `uv run`, `uv add`, and other commands directly
- The `.venv` directory should be in `.gitignore`
- `uv.lock` should be committed to version control
- Claude Code respects `pyproject.toml` for project understanding

---

## Topic 2: Claude Max Subscription and Rate Limits

### 2.1 Claude Max Plan Overview

| Plan | Price | Usage vs Pro | Best For |
|------|-------|-------------|----------|
| Pro | $20/month | 1x baseline | Occasional users |
| Max 5x | $100/month | 5x Pro | Frequent users |
| Max 20x | $200/month | 20x Pro | Daily heavy users |

**What Max includes:**

- Access to all Claude models (Opus 4.6, Sonnet 4.6, Haiku)
- Claude Code terminal access with one unified subscription
- Cowork for delegating complex multi-step tasks in Claude Desktop
- Priority access to new models and features
- Priority access during peak times
- Currently available as monthly subscription only
- Prorated charges when upgrading between tiers

### 2.2 Claude Code with Max: Authentication

**Login flow:**

```bash
# 1. Install Claude Code
# (follow https://code.claude.com/docs/en/quickstart)

# 2. Run claude -- it will prompt for login
claude

# 3. Log in with the same credentials as your Claude web account
# (browser-based OAuth flow)

# 4. If already using API key, switch to subscription:
# Inside Claude Code, run:
/login
```

**CRITICAL WARNING -- API Key Override:**

If `ANTHROPIC_API_KEY` is set as an environment variable, Claude Code will use the API key instead of your Max subscription, resulting in pay-per-token API charges. This has caused users to accidentally incur $1,800+ in charges in two days.

```bash
# Check if API key is set
echo $ANTHROPIC_API_KEY

# Remove it to use subscription
unset ANTHROPIC_API_KEY
```

**Useful commands inside Claude Code:**

- `/login` -- Switch to subscription authentication
- `/logout` -- Log out
- `/status` -- Check current usage allocation
- `/model sonnet` -- Switch to Sonnet (lower token consumption)
- `/model opus` -- Switch to Opus
- `claude --account` -- Check account status and limits

### 2.3 Rate Limits: Specific Numbers

**Subscription plan token allocations (per 5-hour rolling window):**

| Plan | Tokens per 5-Hour Window | Approx Opus Messages |
|------|-------------------------|---------------------|
| Pro | ~44,000 tokens | ~10-40 prompts |
| Max 5x | ~88,000 tokens | ~50-200 prompts |
| Max 20x | ~220,000 tokens | ~200-800 prompts |

**Weekly limits (introduced August 28, 2025):**

- Two separate weekly limits exist:
  1. A general limit across all models
  2. A separate limit specifically for Opus-class models
- Weekly limits reset 7 days after your session begins
- Max subscribers can purchase additional capacity at standard API rates once limits are hit

**API tier rate limits (for direct API key usage):**

| Tier | Requirement | RPM | Input TPM | Output TPM |
|------|-------------|-----|-----------|------------|
| Tier 1 | $5 credit purchase | 50 | 30,000 | N/A |
| Tier 2 | $40 credit purchase | 1,000 | 100,000 | N/A |
| Tier 3 | $200 credit purchase | 2,000 | 400,000 | N/A |
| Tier 4 | $400 credit purchase | 4,000 | 2,000,000 | N/A |

Note: Opus rate limits are a combined total across Opus 4.6, Opus 4.5, Opus 4.1, and Opus 4. Cached input tokens do NOT count toward ITPM limits -- with 80% cache hit rate, effective throughput is 5x the nominal limit.

### 2.4 API Key vs Subscription in Headless Mode

**The critical distinction:**

| Mode | Authentication | Billing | Use Case |
|------|---------------|---------|----------|
| Interactive (`claude`) | OAuth/subscription | Max plan included | Normal development |
| Headless (`claude -p`) | Defaults to API key if set | Pay-per-token | CI/CD, automation |

**Known bug (Issue #33996):** As of March 2026, headless mode (`-p` flag) incorrectly prioritizes `ANTHROPIC_API_KEY` even when the user has explicitly configured "use custom API key" = false. Interactive mode respects this setting; headless mode does not.

**Workaround:**

```bash
# Option 1: Unset API key before headless use
unset ANTHROPIC_API_KEY
claude -p "your prompt here"

# Option 2: Use the environment variable strip
# (Some versions auto-strip ANTHROPIC_API_KEY for subprocess spawns)
export CROSS_CLI_PASSTHROUGH_API_KEY=false
```

**Bottom line for Max subscribers:** If you want to use `claude -p` with your Max subscription, ensure `ANTHROPIC_API_KEY` is NOT set in your environment. The safest approach is to authenticate via OAuth/subscription only.

### 2.5 Rate Limit Behavior

**When rate limited:**

- HTTP 429 status code returned
- Error message: "API Error: Rate limit reached"
- Response includes `retry-after` header (seconds until retry)
- Claude Code displays a warning about remaining capacity before you hit the limit
- Upon hitting limits: you can upgrade plan, enable extra usage at API rates, switch models, or wait for reset

**Token consumption patterns in Claude Code:**

- A single Claude Code command generates 8-12 internal API calls through tool use
- Each "simple" command consumes 30,000+ tokens
- Multi-file refactoring burns tokens at 3-5x the rate of single-file editing
- Claude Code calls are heavier than web chat due to system instructions, file contexts, and multi-step outputs

**Known bugs:**

- Issue #29579: Max subscriber hit rate limits showing only "16% consumption"
- Issue #33120: Rate limit error on every command regardless of actual usage
- Issue #28975: Opus 4.6 (1M context) returning rate limit errors on Max plan
- Issue #34593: Opus 4.6 model variant causes immediate rate limit error on Pro plan

### 2.6 Concurrent Sessions

**Each Claude Code instance gets its own independent context window** (1M tokens on Opus 4.6 / Sonnet 4.6). However, **all sessions share the same rate limit pool** on your account.

**Practical concurrent session limits by plan:**

| Plan | Comfortable Opus Sessions | Comfortable Sonnet Sessions |
|------|--------------------------|----------------------------|
| Pro | 1 | 2-3 |
| Max 5x | 2-3 | 5-8 |
| Max 20x | 4-5+ | 10+ |

- Pro users typically hit limits within minutes with 2 parallel Opus sessions
- All Claude Code sessions, claude.ai web chats, and Cowork sessions on the same account draw from a single rate limit pool
- 3 concurrent sessions consume quota 3x faster
- Opus throughput is the primary bottleneck

**Optimization strategies:**

1. **Model staggering**: Reserve Opus for complex architectural work; use Sonnet/Haiku for secondary tasks
2. **Rotation over parallelization**: Focused sequential blocks are often more productive than 4 simultaneous sessions
3. **Heavy/light separation**: Limit code-generation sessions to 1-2 concurrent; quick-question sessions have minimal impact

**Practical sweet spot:** 2 concurrent sessions on a Max plan provides the best balance of productivity vs. throttling avoidance.

### 2.7 Cost Considerations

**With Max subscription:**

- No additional cost beyond the monthly subscription fee ($100 or $200)
- Usage is constrained by rate limits, not billing
- When limits are hit, you can optionally purchase additional usage at standard API rates
- Auto-reload for API credits is managed separately in Console Billing settings and applies only when API credits are chosen

**API pricing comparison (if using API key instead):**

| Model | Input (per MTok) | Output (per MTok) |
|-------|-------------------|-------------------|
| Opus 4.6 | $15.00 | $75.00 |
| Sonnet 4.6 | $3.00 | $15.00 |
| Haiku 3.5 | $0.80 | $4.00 |

Typical active Claude Code API users spend $60-90/month without optimization. Heavy users can exceed this significantly -- one reported case was $1,800+ in two days using `claude -p` with an API key.

**Recommendation for autonomous systems:** Max 20x ($200/month) provides the best value for heavy Claude Code usage. It offers enough headroom for 4-5 concurrent Opus sessions and avoids per-token charges entirely. The key risk is hitting weekly/5-hour rate limits during intensive sessions.

---

## Summary: Key Decisions for Autonomous Claude Code System

### uv Setup

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create project
uv init --package claude-automata
cd claude-automata

# Pin Python version
uv python pin 3.14

# Add dependencies
uv add click rich
uv add --dev pytest ruff mypy

# Run the project
uv run claude-automata
```

### Claude Code Configuration

```bash
# Ensure no API key is set (use subscription)
unset ANTHROPIC_API_KEY

# Login with Max subscription
claude
# -> Follow OAuth flow

# Check status
/status

# For automation, be cautious with headless mode
# Until bug #33996 is fixed, always unset ANTHROPIC_API_KEY first
unset ANTHROPIC_API_KEY && claude -p "your prompt"
```

### Critical Risks

1. **Headless mode billing bug**: `claude -p` may use API key instead of Max subscription even when configured not to. Always unset `ANTHROPIC_API_KEY`.
2. **Rate limits are shared**: All Claude Code sessions + web chat + Cowork draw from one pool. Plan concurrent session count carefully.
3. **Opus rate limits are stricter**: Opus has lower limits than Sonnet at every tier, and limits are combined across all Opus model versions.
4. **Token burn rate**: Claude Code uses 30,000+ tokens per simple command. Budget accordingly for autonomous operation.

---

## Sources

### uv Package Manager
- [uv GitHub Repository](https://github.com/astral-sh/uv)
- [uv on PyPI (v0.11.1)](https://pypi.org/project/uv/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Working on Projects Guide](https://docs.astral.sh/uv/guides/projects/)
- [Configuring Projects](https://docs.astral.sh/uv/concepts/projects/config/)
- [Creating Projects](https://docs.astral.sh/uv/concepts/projects/init/)
- [Python Versions in uv](https://docs.astral.sh/uv/concepts/python-versions/)
- [Installing Python with uv](https://docs.astral.sh/uv/guides/install-python/)
- [uv Tools Guide](https://docs.astral.sh/uv/guides/tools/)
- [uv Tools Concepts](https://docs.astral.sh/uv/concepts/tools/)
- [Python 3.14 and uv - Astral Blog](https://astral.sh/blog/python-3.14)

### Python 3.14
- [Python 3.14.0 Release](https://www.python.org/downloads/release/python-3140/)
- [Python 3.14.3 Release](https://www.python.org/downloads/release/python-3143/)
- [PEP 745 - Python 3.14 Release Schedule](https://peps.python.org/pep-0745/)
- [What's New in Python 3.14](https://docs.python.org/3/whatsnew/3.14.html)

### Claude Max and Rate Limits
- [What is the Max Plan - Claude Help Center](https://support.claude.com/en/articles/11049741-what-is-the-max-plan)
- [Using Claude Code with Pro or Max Plan](https://support.claude.com/en/articles/11145838-using-claude-code-with-your-pro-or-max-plan)
- [Claude Code Rate Limits - Northflank](https://northflank.com/blog/claude-rate-limits-claude-code-pricing-cost)
- [Claude Code Pricing 2026 - SSD Nodes](https://www.ssdnodes.com/blog/claude-code-pricing-in-2026-every-plan-explained-pro-max-api-teams/)
- [Claude Code Rate Limit Fix Guide - LaoZhang](https://blog.laozhang.ai/en/posts/claude-code-rate-limit-reached)
- [Claude Max Plan Explained - IntuitionLabs](https://intuitionlabs.ai/articles/claude-max-plan-pricing-usage-limits)
- [Multiple Claude Code Instances Guide - 32blog](https://32blog.com/en/claude-code/claude-code-multiple-instances-context-guide)
- [Anthropic API Rate Limits](https://platform.claude.com/docs/en/api/rate-limits)

### Bug Reports
- [Issue #33996: API Key Override in Headless Mode](https://github.com/anthropics/claude-code/issues/33996)
- [Issue #37686: claude -p caused $1,800+ API billing for Max subscriber](https://github.com/anthropics/claude-code/issues/37686)
- [Issue #29579: Rate limit at 16% usage](https://github.com/anthropics/claude-code/issues/29579)
- [Issue #28975: Opus 4.6 1M rate limit on Max](https://github.com/anthropics/claude-code/issues/28975)
