import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing.")

API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_rich_table(chat_id):
    # Telegram Bot API 10.1+ Rich Message.
    # This is a REAL Telegram table, not Unicode/symbol drawing.
    html = """
<h2>মেডিকেল + ভার্সিটি প্রস্তুতির স্ট্যান্ডার্ড প্রশ্ন</h2>

<table bordered striped compact>
<tr>
    <th>জীববিজ্ঞান</th>
    <th>পদার্থবিজ্ঞান</th>
</tr>
<tr>
    <td>কোষ ও এর গঠন</td>
    <td>ভেক্টর</td>
</tr>
<tr>
    <td>কোষ বিভাজন</td>
    <td>গতিবিদ্যা</td>
</tr>
<tr>
    <td>নগরজীবী আবৃতবীজী</td>
    <td>নিউটনিয়ান বলবিদ্যা</td>
</tr>
<tr>
    <td>প্রাণীর বিভিন্নতা ও শ্রেণিবিন্যাস</td>
    <td>কাজ শক্তি ক্ষমতা</td>
</tr>
<tr>
    <td>প্রাণীর পরিচিতি</td>
    <td>—</td>
</tr>
<tr>
    <td>পরিপাক ও শোষণ</td>
    <td>—</td>
</tr>
</table>

<p>✅ <b>সাল ভিত্তিক প্রশ্ন সমাধান</b></p>

<table bordered compact>
<tr>
    <th>কৃষি গুচ্ছ</th>
    <th>মেডিকেল</th>
</tr>
<tr>
    <td>২৫–২৬</td>
    <td>২৫–২৬</td>
</tr>
</table>

<hr/>
<p>🎯 Practice &amp; Web Exam: <b>@ArektaQuizBot</b></p>
"""

    payload = {
        "chat_id": chat_id,
        "rich_message": {
            "html": html,
            # Set True if you want the whole rich message RTL.
            # For mixed Bangla/English, False/omitted usually looks better.
            "is_rtl": False
        }
    }

    r = requests.post(f"{API}/sendRichMessage", json=payload, timeout=30)
    data = r.json()

    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")

    return data["result"]


def get_updates(offset=None):
    params = {"timeout": 50}
    if offset is not None:
        params["offset"] = offset
    r = requests.get(f"{API}/getUpdates", params=params, timeout=60)
    return r.json()


def main():
    print("Rich Table Bot is running...")

    offset = None

    while True:
        data = get_updates(offset)

        if not data.get("ok"):
            print("getUpdates error:", data)
            continue

        for update in data.get("result", []):
            offset = update["update_id"] + 1

            message = update.get("message")
            if not message:
                continue

            text = message.get("text", "")
            chat_id = message["chat"]["id"]

            if text == "/start":
                requests.post(
                    f"{API}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": "👋 /table লিখলে Telegram-এর native Rich Table দেখাবো."
                    },
                    timeout=30
                )

            elif text == "/table":
                try:
                    send_rich_table(chat_id)
                except Exception as e:
                    requests.post(
                        f"{API}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": f"❌ Rich Table পাঠাতে সমস্যা:\n{e}"
                        },
                        timeout=30
                    )


if __name__ == "__main__":
    main()
