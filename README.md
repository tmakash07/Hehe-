# Telegram Native Rich Table Bot

This is a minimal test bot for Telegram's native Rich Messages / Table API.

## Files

- `bot.py` — main bot
- `requirements.txt` — dependency

## Environment variable

Set:

BOT_TOKEN=your_bot_token

## Render

Runtime: Python

Build Command:
pip install -r requirements.txt

Start Command:
python bot.py

Then open the bot and send:

/table

The bot uses:

POST https://api.telegram.org/bot<TOKEN>/sendRichMessage

with `rich_message.html` containing a real `<table>`.

## Important

This requires a Telegram Bot API version that supports Rich Messages (Bot API 10.1+).
Telegram added Rich Messages in Bot API 10.1 and `is_compact` for tables in Bot API 10.3.
