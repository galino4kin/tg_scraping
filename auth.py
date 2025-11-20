import os
from dotenv import load_dotenv
from telethon.sync import TelegramClient

load_dotenv()

API_ID = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH")
SESSION_NAME = os.getenv("TG_SESSION", "telegram_session")

if not API_ID or not API_HASH:
    raise RuntimeError("Заполните TG_API_ID и TG_API_HASH в .env")

if __name__ == "__main__":
    # Первый запуск попросит номер телефона и код/2FA.
    with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        me = client.get_me()
        print("[✓] Сессия успешно авторизована.")
        print(f"    User id: {me.id}")
        print(f"    Username: @{me.username}" if me.username else f"    Name: {me.first_name}")
        print(f"    Session file: {SESSION_NAME}.session")
