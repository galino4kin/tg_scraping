# Telegram Scraping Utilities

A collection of scripts for extracting structured Telegram data using Telethon.

The project supports three main operations:

1. Export posts from Telegram channels.
2. Export messages from chats and megagroups.
3. Export comments associated with specific channel posts.

All scripts rely on a persistent Telethon session created once and reused across runs.

## Project Structure

```
.
├── channels/                      # CSV exports: channel posts
├── chats/                         # CSV exports: chat histories
├── comments/                      # CSV exports: comments to channel posts
│
├── .env                           # API credentials & settings (ignored by git)
├── .gitignore
├── auth.py
├── get_channel_posts.py
├── get_chats_messages.py
├── get_comments.py
├── README.md
└── <session_name>.session         # Local Telegram session file (ignored by git)
```

## Files and Their Purpose

| File | Description |
|------|------------|
| [auth.py](./auth.py) | Initializes and saves a Telegram session (run once) |
| [get_channel_posts.py](./get_channel_posts.py) | Downloads all posts from a channel for a given date range |
| [get_chats_messages.py](./get_chats_messages.py) | Downloads messages from a chat or megagroup |
| [get_comments.py](./get_comments.py) | Extracts comments associated with a specific channel post |
| [channels/](./channels) | Output folder for channel exports |
| [chats/](./chats) | Output folder for chat exports |
| [comments/](./comments) | Output folder for comment exports |
| `.env` *(ignored)* | Stores API ID, hash, phone number, session name |
| `*.session` *(ignored)* | Local Telethon session file |

## Requirements

- Python 3.10+
- Telegram account
- Tekegram API keys from https://my.telegram.org/

Install dependencies:

```bash
pip install telethon python-dotenv
```

## Configuration

Create `.env` in the project root:

```env
TG_API_ID=123456
TG_API_HASH=your_api_hash
TG_PHONE=+12345678900
TG_SESSION=test
```

## 1. Authorization

Run once:

```bash
python auth.py
```

This creates `{session_name}.session`, which all other scripts reuse.

## 2. Export Channel Posts

Configured inside [get_channel_posts.py](./get_channel_posts.py):

```python
CHANNEL_PEER_ID = -1001271343429
FROM_DATE_STR   = "2025-11-01"
TO_DATE_STR     = "2025-12-01"
```

Run:

```bash
python get_channel_posts.py
```

Output → [`./channels`](./channels)

## 3. Export Chat Messages

Configured inside [get_chats_messages.py](./get_chats_messages.py):

```python
CHAT_PEER_ID   = -1001240453727
FROM_DATE_STR  = "2025-11-01"
TO_DATE_STR    = "2025-12-01"
```

Run:

```bash
python get_chats_messages.py
```

Output → [`./chats`](./chats)

## 4. Export Comments for a Post

Configured inside [get_comments.py](./get_comments.py):

```python
CHANNEL_PEER_ID = -1001271343429
MESSAGE_ID = 158404
```

Run:

```bash
python get_comments.py
```

Output → [`./comments`](./comments)

## Notes

- `.env` and `*.session` must not be committed to version control.
- CSV output is one-row-per-message (newlines are escaped).
- Numeric peer IDs (e.g., `-100xxxxxx`) represent channels and megagroups.
