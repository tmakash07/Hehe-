# Telegram Native Rich Table Maker

Commands:
- `/newtable` → 2×2 table
- `/newtable 3 4` → 3×4 table
- `/help`

Buttons let you edit cells, add/delete rows and columns, toggle border/striped/compact, preview and publish.

Render:
Build Command: `pip install -r requirements.txt`
Start Command: `python bot.py`
Environment variable: `BOT_TOKEN=your BotFather token`

Uses Telegram Bot API Rich Messages / `sendRichMessage` and `editMessageText` with `rich_message`. Current Rich Table limit is 20 columns.
