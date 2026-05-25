# miniserve

A minimal embeddable HTTP file server for development use.

No third-party dependencies — built entirely on Python's standard library.

## Install

```bash
pip install miniserve
```

## CLI usage

```bash
# Serve the current directory on port 8080
miniserve

# Custom port and directory
miniserve --port 3000 --dir ./public

# Open browser automatically after starting
miniserve --open
```

## Python API

```python
from miniserve import start_server

server = start_server(port=8080, directory="./public")
# ... do other work ...
server.shutdown()
```

## Development

```bash
make install      # install deps and create virtual environment
make check        # full pipeline — lint, type-check, tests
make lint         # lint only
make fix          # auto-fix lint issues then format
make fmt          # format only
make type-check   # type-check only
make test         # tests only
make build        # build .whl and .tar.gz for publishing
make publish      # push to PyPI (requires PYPI_TOKEN env var)
```

---

## Publishing

### How it works

When you run `make publish`, uv:
1. Reads the built `.whl` and `.tar.gz` from `dist/`
2. Uploads them to PyPI's API (`https://upload.pypi.org/legacy/`)
3. PyPI stores the files and makes them available via `pip install miniserve`

Always run `make build` before `make publish`.

### Automated publishing via GitHub Actions

The recommended approach is to never publish manually from a laptop. Instead, pushing a version tag triggers the publish workflow in `.github/workflows/publish.yml`:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow builds the package, runs the full quality pipeline, and publishes to PyPI — all without any stored credentials (see Trusted Publishing below).

### Authentication

**Trusted Publishing (recommended)** — PyPI's modern approach. No API token is stored anywhere. Instead, you configure PyPI to trust a specific GitHub Actions workflow from a specific repo. GitHub's OIDC issues a short-lived token automatically at publish time. Nothing to rotate, nothing to leak.

Setup steps:
1. Go to pypi.org → Your project → Manage → Publishing
2. Add a Trusted Publisher entry:
   - Owner: your GitHub username
   - Repository: `miniserve`
   - Workflow: `publish.yml`
3. That's it — the workflow handles everything from there

**API token (fallback)** — if you need to publish manually:
1. Go to pypi.org → Account Settings → API Tokens
2. Create a token scoped to this package only (not your whole account)
3. Pass it at publish time:
```bash
UV_PUBLISH_TOKEN=pypi-... make publish
```

### Supply chain security

Four attack vectors and how they are mitigated:

| Threat | Mitigation |
|---|---|
| Stolen credentials | Trusted Publishing — no long-lived token exists |
| Tampered artefact | Sigstore attestations — cryptographically links the artefact to the exact CI run that built it |
| Name squatting | Register the package name on PyPI early, even with a `0.0.1` placeholder |
| Compromised deps | Commit `uv.lock` and pin versions in `pyproject.toml` |

**Sigstore attestations** are enabled in the publish workflow via `attestations: true`. This cryptographically signs the artefact so users can verify it came from your exact GitHub Actions run:

```bash
pip download miniserve
python -m sigstore verify miniserve-*.whl
```

---

Two tools are configured, both invoked via `make`:

**`ruff`** — covers linting and formatting in a single fast tool. Replaces `flake8`, `isort`, and `black`.

| Rule group | What it checks |
|---|---|
| `E` / `W` | Basic style (indentation, whitespace, line length) |
| `F` | Unused imports, undefined names |
| `I` | Import ordering (replaces `isort`) |
| `UP` | Suggests modern Python syntax (e.g. `list[str]` instead of `List[str]`) |
| `B` | Common bugs — things that work but are likely wrong |
| `SIM` | Code that can be simplified |

**`mypy`** — static type checker. Validates that type annotations are correct and consistent across the codebase. Configured in strict mode, meaning all functions must be annotated and `Any` is disallowed unless explicitly justified.

---

## Project structure

```
miniserve/
├── .github/
│   └── workflows/
│       └── publish.yml         ← publishes to PyPI on version tag push
├── pyproject.toml              ← package config, build system, scripts
├── Makefile                    ← developer commands
├── README.md
├── uv.lock                     ← locked dependencies
├── .venv/                      ← virtual environment (git-ignored)
├── src/
│   └── miniserve/
│       ├── __init__.py         ← public API: start_server(...)
│       ├── server.py           ← HTTP server logic
│       └── cli.py              ← CLI entry point
└── tests/
    └── test_miniserve.py       ← 9 tests
```

### `pyproject.toml` — the single source of truth

Replaces the old `setup.py` / `setup.cfg` / `requirements.txt` trio. Everything lives in one place:

- **`[build-system]`** — tells `uv build` (and pip) to use `hatchling` to package the code. Hatchling is a modern, fast build backend.
- **`[project]`** — the package identity: name, version, Python requirement, license, PyPI classifiers. `dependencies = []` means no third-party runtime deps (only Python's standard library is used).
- **`[project.scripts]`** — creates the `miniserve` terminal command when someone installs the package. Points to the `main` function in `cli.py`.
- **`[dependency-groups] dev`** — pytest, coverage, ruff, and mypy are only needed for development, not by users who install the package.
- **`[tool.hatch.build.targets.wheel]`** — tells the build tool where the source code lives (`src/miniserve`). This is the `src/` layout pattern — it prevents accidental imports of local code instead of the installed package.

### `src/miniserve/__init__.py` — the public API

```python
from miniserve.server import start_server
__all__ = ["start_server"]
```

This is the only file users of the library interact with. When someone writes `from miniserve import start_server`, Python executes this file. The `__all__` list declares what is officially public. Anything not listed is considered an implementation detail.

### `src/miniserve/server.py` — the core logic

Three key Python concepts used here:

**`functools.partial`** — Python's `SimpleHTTPRequestHandler` doesn't accept `directory` in its constructor directly. `partial` pre-fills the `directory` argument, producing a new callable that behaves like the handler class but with the directory baked in.

**`threading.Thread(daemon=True)`** — `serve_forever()` would block the entire program if called directly. Running it in a daemon thread means: (a) it runs in the background, (b) it dies automatically when the main process exits — no manual cleanup needed in the common case.

**`*` in the function signature** — the `*` before `open_browser` makes it keyword-only. Callers must write `start_server(open_browser=True)`, not `start_server(8080, ".", True)`. This prevents mistakes when argument order isn't obvious.

### `src/miniserve/cli.py` — the command-line interface

**`argparse`** is Python's standard library for parsing CLI arguments. `_build_parser()` is extracted as its own function (rather than inlined in `main`) so tests can call it directly without starting a server.

**`while True: time.sleep(1)`** — after the server starts in its background thread, the main thread has nothing to do. This loop keeps the process alive. When Ctrl+C is pressed, Python raises `KeyboardInterrupt`, which breaks out of the loop into the `except` block for a clean shutdown.

### `tests/test_miniserve.py` — the tests

Three test classes, each testing a different layer:

**`TestStartServer`** — integration tests. Start a real server on an OS-assigned port, make an actual HTTP request with `urllib.request`, and verify the response. `_free_port()` asks the OS for an available port to avoid collisions between tests.

**`TestCLIParser`** — pure unit tests for the argument parser. No server is started. Fast and deterministic.

**`TestCLIMain`** — uses `monkeypatch` (a pytest built-in fixture) to replace `time.sleep` with a fake that immediately raises `KeyboardInterrupt`. This simulates "user pressed Ctrl+C" without actually waiting or blocking.

---

### Request flow

```
uv run miniserve --port 3000 --dir ./public
        │
        └─▶ cli.py:main()
                │
                ├─▶ argparse parses --port 3000, --dir ./public
                │
                └─▶ server.py:start_server(port=3000, directory="./public")
                            │
                            ├─▶ HTTPServer created on port 3000
                            └─▶ serve_forever() running in background thread
                                        │
                                        └─▶ responds to HTTP requests
```
