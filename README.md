# FastAPI Blog

🚧 Work in progress.

Simple blog API + server-rendered frontend built with FastAPI, SQLAlchemy (async), and Jinja2.

## Features

- User accounts (create, fetch, partial update) with unique username/email checks
- Posts (create, fetch, full/partial update, delete) tied to a user
- Server-rendered pages: home feed, single post, user's posts
- Centralized exception handlers for HTTP + validation errors (JSON for `/api`, HTML for pages)

## Tech Stack

- [FastAPI](https://fastapi.tiangolo.com/)
- SQLAlchemy 2.0 (async) + aiosqlite
- Jinja2 templates
- uv for dependency management
- ruff for linting

## Project Structure

```
main.py                  # app setup, router + exception handler registration
databases/
  database.py            # engine, session, Base
  models.py              # SQLAlchemy models
routers/
  api/
    user.py              # /api/users routes
    post.py               # /api/posts routes
  frontend.py             # HTML page routes
  exception.py             # exception handlers
schemas/
  users_schema.py          # Pydantic schemas for users
  posts_schema.py           # Pydantic schemas for posts
templates/                  # Jinja2 templates
static/                      # CSS, JS, icons
```

## Setup

```bash
uv sync
uv run fastapi dev main.py
```

App runs at `http://127.0.0.1:8000`. Interactive docs at `/docs`.

## Lint

```bash
uv run ruff check .
```
