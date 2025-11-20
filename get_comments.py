import os
import asyncio
import csv
import json
import datetime as dt
from typing import Any, Dict

from dotenv import load_dotenv
from telethon import TelegramClient, errors
from telethon.tl.types import Message, Channel

# -------- CONFIG (ONLY NUMERIC PEER ID + MESSAGE ID) --------

CHANNEL_PEER_ID = -1001271343429   # channel peer id
MESSAGE_ID = 158404                # post id in this channel

OUTPUT_DIR = "comments"

# ------------------------------------------------------------

load_dotenv()

API_ID = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH")
SESSION_NAME = os.getenv("TG_SESSION", "telegram_session")


def dt_to_iso(d: dt.datetime | None) -> str | None:
    return d.isoformat() if d else None


def obj_to_dict_safe(obj: Any) -> Any:
    """
    Convert Telethon objects to JSON-safe structures.
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
    Extract rich metadata for a single comment.
    """
    return {
        # basic
        "id": msg.id,
        "date": dt_to_iso(msg.date),
        "date_ts": int(msg.date.timestamp()) if msg.date else None,

        # text
        "message": msg.message,
        "raw_text": msg.raw_text,

        # author
        "from_id": obj_to_dict_safe(getattr(msg, "from_id", None)),
        "sender": obj_to_dict_safe(getattr(msg, "sender", None)),

        # threading
        "reply_to_msg_id": getattr(msg, "reply_to_msg_id", None),

        # formatting / content
        "entities": obj_to_dict_safe(getattr(msg, "entities", None)),
        "media": obj_to_dict_safe(getattr(msg, "media", None)),
        "reactions": obj_to_dict_safe(getattr(msg, "reactions", None)),
    }


async def fetch_post_comments() -> None:
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        raise RuntimeError("Session not authorized. Run auth_telegram.py first.")

    channel = await client.get_entity(CHANNEL_PEER_ID)
    if not isinstance(channel, Channel):
        print(f"[!] Peer {CHANNEL_PEER_ID} is not a Channel, got {type(channel)}")

    # Just to be sure the post exists and has replies
    post: Message = await client.get_messages(channel, ids=MESSAGE_ID)
    print("[+] Post loaded")
    print(f"    text: {post.message[:80]!r}")
    print(f"    replies meta: {post.replies}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(
        OUTPUT_DIR,
        f"{CHANNEL_PEER_ID}_{MESSAGE_ID}_comments.csv",
    )

    print(f"[+] Output: {output_path}")

    csv_file = open(output_path, "w", encoding="utf-8", newline="")
    writer = None
    total = 0

    try:
        # Core idea: let Telethon resolve discussion chat internally
        async for msg in client.iter_messages(
            channel,
            reply_to=MESSAGE_ID,
        ):
            if not isinstance(msg, Message):
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
                    # keep CSV one physical row per message
                    row[k] = v.replace("\r", "\\r").replace("\n", "\\n")
                else:
                    row[k] = v

            writer.writerow(row)
            total += 1

            if total % 20 == 0:
                print(f"[+] Collected comments: {total}")

        print(f"[✓] Done. Comments collected: {total}")

    except errors.FloodWaitError as e:
        print(f"[!] FloodWait: wait {e.seconds} seconds and rerun.")
    finally:
        csv_file.close()
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(fetch_post_comments())
