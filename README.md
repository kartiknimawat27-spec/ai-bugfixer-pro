# AI BugFixer Pro

An AI-powered code review and debugging assistant. Paste code, pick a
language, and get an instant explanation of what's wrong plus a
verified, re-parsed fix — backed by a deterministic static-analysis
engine for Python and optional deep review from Claude for every
supported language.

## Features

- **Landing page, auth, and dashboard** with a cohesive, modern dark UI
- **Python engine**: AST-based syntax checking with *verified* auto-fixes
  (every candidate fix is re-parsed before it's shown to you) plus a
  semantic linter (bare `except:`, mutable default args, `eval`/`exec`
  usage, `== None`, unused imports)
- **AI-powered review** (optional): when `ANTHROPIC_API_KEY` is set, every
  language gets a full Claude-powered review — bug explanation, severity,
  and a fixed version of the code — with automatic fallback to the static
  engine if the API is unavailable
- **Multi-language support**: Python, JavaScript, TypeScript, Java, C,
  C++, C#, Go, PHP, Ruby
- **Personal dashboard**: live stats, a 14-day activity trend chart, a
  by-language breakdown, and full analysis history
- **Downloadable reports** for any past analysis
- **Working auth**: registration, login (with basic brute-force
  throttling), logout, and a full forgot/reset-password flow

## Getting started

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then edit .env
python app.py
```

Visit `http://127.0.0.1:5000`.

The app works fully out of the box — no API key required. To enable
full AI-powered review, set `ANTHROPIC_API_KEY` in `.env`.

## Project structure

```
app.py                  Flask app factory / entry point
config.py                Environment-driven configuration
database/                SQLite connection + schema
models.py                 Data-access functions
ai_engine/
  engine.py               Orchestrator: routes to static or AI review
  python_analyzer.py       AST syntax check + semantic linter
  ai_client.py              Anthropic API wrapper (optional)
  multi_lang.py              Structural heuristics fallback
  result.py                   Shared AnalysisResult dataclass
routes/                  Flask blueprints (main, auth, dashboard, api)
templates/                Jinja2 templates
static/                    CSS / JS
```

## API

`POST /api/analyze` — body `{ "code": "...", "language": "Python" }`,
requires an authenticated session. Returns a JSON analysis result and
persists it to the caller's history.

## Notes

- This project has no SMTP server configured, so the "forgot password"
  flow surfaces the reset link directly in the UI instead of emailing
  it — clearly labeled as demo behavior. Wire up a mail provider
  (e.g. SendGrid, SES) in `routes/auth.py` for production use.
- The API key is only ever read from the environment and never logged
  or hard-coded.
