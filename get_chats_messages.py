# get_chat_messages.py

import os
import asyncio
import csv
import json
import datetime as dt
from typing import Any, Dict

from dotenv import load_dotenv
from telethon import TelegramClient, errors
from telethon.tl.functions.messages import SearchRequest
from telethon.tl.types import (
    InputMessagesFilterEmpty,
    Message,
)

# ------------- CONFIG (EDIT THIS BLOCK) -------------

# Numeric peer id only, e.g. user, group or supergroup:
#   user:           123456789
#   basic group:    -123456789
#   supergroup:     -1001234567890
CHAT_PEER_ID = -1001240453727

# Time window (FROM inclusive, TO exclusive)
FROM_DATE_STR = "2025-11-01"
TO_DATE_STR = "2025-11-02"

OUTPUT_DIR = "chats"
BATCH_LIMIT = 100  # page size for SearchRequest

# ----------------------------------------------------

load_dotenv()

API_ID = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH")
SESSION_NAME = os.getenv("TG_SESSION", "telegram_session")

if not API_ID or not API_HASH:
    raise RuntimeError("Please set TG_API_ID and TG_API_HASH in .env")

FROM_DT = dt.datetime.fromisoformat(FROM_DATE_STR)
TO_DT = dt.datetime.fromisoformat(TO_DATE_STR)
FROM_TS = int(FROM_DT.timestamp())
TO_TS = int(TO_DT.timestamp())


def dt_to_iso(d: dt.datetime | None) -> str | None:
    if d is None:
        return None
    return d.isoformat()


def obj_to_dict_safe(obj: Any) -> Any:
    """
    Convert TL objects and nested structures to JSON-serializable structures.
    """
    if obj is None:
        return None

    if isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, (bytes, bytearray)):
        return obj.hex()

    if isinstance(obj, dt.datetime):
        return obj.isoformat()

    if isinstance(obj, dict):
        return {k: obj_to_dict_safe(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [obj_to_dict_safe(x) for x in obj]

    if hasattr(obj, "to_dict"):
        try:
            raw = obj.to_dict()
        except Exception:
            return repr(obj)
        return obj_to_dict_safe(raw)

    return repr(obj)


def message_to_record(msg: Message) -> Dict[str, Any]:
    """
    Extract as many metadata fields as possible for a single chat message.
    """
    rec: Dict[str, Any] = {
        # basic fields
        "id": msg.id,
        "peer_id": obj_to_dict_safe(getattr(msg, "peer_id", None)),
        "date": dt_to_iso(getattr(msg, "date", None)),
        "date_ts": int(msg.date.timestamp()) if msg.date else None,
        "edit_date": dt_to_iso(getattr(msg, "edit_date", None)),
        "post": getattr(msg, "post", None),
        "legacy": getattr(msg, "legacy", None),
        "ttl_period": getattr(msg, "ttl_period", None),

        # text
        "message": getattr(msg, "message", None),
        "raw_text": getattr(msg, "raw_text", None),

        # author / source
        "from_id": obj_to_dict_safe(getattr(msg, "from_id", None)),
        "sender_id": getattr(msg, "sender_id", None),
        "sender": obj_to_dict_safe(getattr(msg, "sender", None)),
        "post_author": getattr(msg, "post_author", None),
        "via_bot_id": getattr(msg, "via_bot_id", None),
        "via_business_bot_id": getattr(msg, "via_business_bot_id", None),
        "fwd_from": obj_to_dict_safe(getattr(msg, "fwd_from", None)),

        # content and formatting
        "entities": obj_to_dict_safe(getattr(msg, "entities", None)),
        "media": obj_to_dict_safe(getattr(msg, "media", None)),
        "reply_markup": obj_to_dict_safe(getattr(msg, "reply_markup", None)),
        "grouped_id": getattr(msg, "grouped_id", None),

        # media helpers
        "reply_to_msg_id": getattr(msg, "reply_to_msg_id", None),
        "photo": obj_to_dict_safe(getattr(msg, "photo", None)),
        "document": obj_to_dict_safe(getattr(msg, "document", None)),
        "video": obj_to_dict_safe(getattr(msg, "video", None)),
        "audio": obj_to_dict_safe(getattr(msg, "audio", None)),
        "voice": obj_to_dict_safe(getattr(msg, "voice", None)),
        "gif": obj_to_dict_safe(getattr(msg, "gif", None)),
        "sticker": obj_to_dict_safe(getattr(msg, "sticker", None)),
        "poll": obj_to_dict_safe(getattr(msg, "poll", None)),
        "web_preview": obj_to_dict_safe(getattr(msg, "web_preview", None)),
        "file": obj_to_dict_safe(getattr(msg, "file", None)),

        # metrics and replies (views/forwards usually None in chats)
        "views": getattr(msg, "views", None),
        "forwards": getattr(msg, "forwards", None),
        "replies": obj_to_dict_safe(getattr(msg, "replies", None)),
        "reactions": obj_to_dict_safe(getattr(msg, "reactions", None)),

        # behavior flags
        "pinned": getattr(msg, "pinned", False),
        "silent": getattr(msg, "silent", False),
        "noforwards": getattr(msg, "noforwards", False),
        "from_scheduled": getattr(msg, "from_scheduled", False),
        "edit_hide": getattr(msg, "edit_hide", False),
        "out": getattr(msg, "out", None),
        "mentioned": getattr(msg, "mentioned", None),
        "media_unread": getattr(msg, "media_unread", None),
        "restriction_reason": obj_to_dict_safe(
            getattr(msg, "restriction_reason", None)
        ),

        # service / action
        "action": obj_to_dict_safe(getattr(msg, "action", None)),
    }
    return rec


async def fetch_chat_history() -> None:
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        raise RuntimeError(
            "Session is not authorized. Run auth_telegram.py first."
        )

    entity = await client.get_entity(CHAT_PEER_ID)
    # entity can be User, Chat, or Channel (megagroup); all are fine here

    peer = entity  # for SearchRequest we can pass the entity directly
    peer_id_str = str(CHAT_PEER_ID)
    title = getattr(entity, "title", None) or getattr(entity, "username", None) or peer_id_str

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"{peer_id_str}_chat_messages.csv")

    print(f"[+] Chat: {title} (peer id={peer_id_str})")
    print(f"[+] Range (ts): {FROM_TS} .. {TO_TS}")
    print(f"[+] Output: {output_path}")

    csv_file = open(output_path, "w", encoding="utf-8", newline="")
    writer = None
    total = 0
    offset_id = 0

    try:
        while True:
            try:
                result = await client(
                    SearchRequest(
                        peer=peer,
                        q="",  # no keyword filter
                        filter=InputMessagesFilterEmpty(),
                        min_id=0,
                        max_id=0,
                        offset_id=offset_id,
                        add_offset=0,
                        limit=BATCH_LIMIT,
                        min_date=FROM_TS,
                        max_date=TO_TS,
                        hash=0,
                    )
                )
            except errors.FloodWaitError as e:
                print(f"[!] FloodWait: need to wait {e.seconds} seconds and rerun.")
                break

            messages = result.messages or []
            if not messages:
                break

            min_id_in_batch = None

            for msg in messages:
                if not isinstance(msg, Message):
                    continue
                if not msg.date:
                    continue

                msg_ts = int(msg.date.timestamp())
                if msg_ts < FROM_TS or msg_ts >= TO_TS:
                    continue

                rec = message_to_record(msg)

                if writer is None:
                    fieldnames = list(rec.keys())
                    writer = csv.DictWriter(
                        csv_file,
                        fieldnames=fieldnames,
                        quoting=csv.QUOTE_MINIMAL,
                    )
                    writer.writeheader()

                row: Dict[str, Any] = {}
                for k, v in rec.items():
                    if isinstance(v, (dict, list)):
                        row[k] = json.dumps(v, ensure_ascii=False)
                    elif isinstance(v, str):
                        # escape line breaks to keep one physical line per CSV row
                        row[k] = v.replace("\r", "\\r").replace("\n", "\\n")
                    else:
                        row[k] = v

                writer.writerow(row)
                total += 1

                if min_id_in_batch is None or msg.id < min_id_in_batch:
                    min_id_in_batch = msg.id

            if total and total % 500 == 0:
                print(f"[+] Collected: {total}")

            if min_id_in_batch is None:
                break

            offset_id = min_id_in_batch  # paginate backwards

        if total == 0:
            print("[=] No messages in the given interval.")
        else:
            print(f"[✓] Done. Saved {total} messages.")

    finally:
        csv_file.close()
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(fetch_chat_history())
