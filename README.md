# FastAPI Blog

🚧 Work in progress.

Blog API + server-rendered frontend built with FastAPI, async SQLAlchemy, and Jinja2. Users can register, log in (JWT), reset forgotten passwords by email, upload a profile picture, and create/edit/delete posts.

## Features

- **Auth**: register, JWT login (`/api/users/token`), current-user lookup, change password
- **Password reset**: forgot-password email flow with expiring tokens (background email send)
- **Users**: fetch, partial update (unique username/email re-checked on change), delete, profile picture upload/delete
- **Posts**: create, fetch (paginated), full/partial update, delete — ownership enforced (only the author can edit/delete)
- **Frontend pages**: home feed (paginated, "Load More"), single post, a user's posts, login/register/account/forgot-password/reset-password
- Centralized exception handlers: JSON for `/api/*`, rendered HTML page otherwise

## Tech Stack

- [FastAPI](https://fastapi.tiangolo.com/) + Jinja2 templates
- SQLAlchemy 2.0 (async) + aiosqlite
- `pwdlib[argon2]` for password hashing, `pyjwt` for access tokens
- `pydantic-settings` for config (`.env`)
- Pillow for profile picture processing
- `aiosmtplib` for sending password-reset emails
- uv for dependency management, ruff for linting

## Project Structure

```
main.py                    # app setup, router + exception handler registration
core/
  settings.py               # env-driven config (Settings/settings)
authetication/
  auth.py                    # password hashing, JWT create/verify, CurrentUser dependency
databases/
  database.py                 # async engine, session, Base
  models.py                    # User, Post, PasswordResetToken
routers/
  api/
    user.py                    # /api/users — auth, profile, password reset
    post.py                    # /api/posts
  frontend.py                  # HTML page routes
  exception.py                  # exception handlers
schemas/
  users_schema.py               # Pydantic schemas for users/auth
  posts_schema.py                # Pydantic schemas for posts (incl. pagination)
  password_reset.py               # forgot/reset/change password request schemas
utils/
  image_utils.py                  # profile picture validation/processing/storage
  email_utils.py                   # password-reset email sending
templates/                         # Jinja2 templates (incl. templates/email/)
static/                             # CSS, JS, icons
```

## API Overview

| Method | Path | Description |
|---|---|---|
| POST | `/api/users` | Register |
| POST | `/api/users/token` | Login (OAuth2 password flow, JWT) |
| GET | `/api/users/me` | Current user |
| POST | `/api/users/forgot-password` | Request password reset email |
| POST | `/api/users/reset-password` | Reset password with emailed token |
| PATCH | `/api/users/me/password` | Change password (logged in) |
| GET/PATCH/DELETE | `/api/users/{user_id}` | Fetch / update / delete user |
| GET | `/api/users/{user_id}/posts` | User's posts (paginated) |
| PATCH/DELETE | `/api/users/{user_id}/picture` | Upload / delete profile picture |
| GET/POST | `/api/posts` | List (paginated) / create post |
| GET/PUT/PATCH/DELETE | `/api/posts/{post_id}` | Fetch / replace / update / delete post |

Interactive docs at `/docs`.

## Setup

```bash
uv sync
echo "SECRET_KEY=change-me" > .env   # required; mail settings optional for local dev
uv run fastapi dev main.py
```

App runs at `http://127.0.0.1:8000`.
