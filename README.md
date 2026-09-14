# Telegram Native Rich Table Maker

A generic Telegram bot for creating native Telegram Rich Tables.

## Commands
- `/newtable` → 2×2 table
- `/newtable 3 4` → 3×4 table
- `/help`

Buttons let you edit cells, add/delete rows and columns, toggle border/striped/compact, preview and publish.

## Render Free Web Service

This bot is a long-running Telegram polling process. It also starts a tiny HTTP health server so it can run as a Render **Web Service**.

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python bot.py`
- **Environment variable:** `BOT_TOKEN=your BotFather token`

The HTTP server binds to `0.0.0.0:$PORT` (Render's expected port) and provides `/health`.

### Important Free-plan limitation
Render Free Web Services can spin down after 15 minutes without inbound HTTP/WebSocket traffic. The tiny health server only makes the service compatible with Render's Web Service port requirement; it does **not** prevent Render's free-tier sleep behavior. If the service sleeps, Telegram polling stops until the service receives an inbound request and wakes up again.

For uninterrupted polling, use a hosting option that provides an always-on free worker, or use a webhook-based architecture where appropriate.

## Notes
- Draft table state is stored in RAM, so unfinished drafts are lost after a restart/redeploy/spin-down.
- Published Telegram messages remain in Telegram.
- Current Rich Table limit is 20 columns.
