import os, asyncio
import requests
from telegram.ext import Application, CommandHandler, MessageHandler, filters

load_dotenv()

TOKEN = os.environ["TG_BOT_TOKEN"]
MODEL_URL = "http://127.0.0.1:8000/infer"

def _post_image_sync(url: str, jpg_bytes: bytes, timeout: int = 120) -> str:
  r = requests.post(url, files={"image": ("in.jpg", jpg_bytes, "image/jpeg")}, timeout=timeout)
  r.raise_for_status()
  return r.text.strip()

async def on_photo(update, context):
  file = await update.message.photo[-1].get_file()
  buf = await file.download_as_bytearray()
  text = await asyncio.to_thread(_post_image_sync, MODEL_URL, bytes(buf))
  await update.message.reply_text(text[:4096])

async def my_id(update, context): # needed in camera script
    await update.message.reply_text(str(update.effective_chat.id))

def main():
  app = Application.builder().token(TOKEN).build()
  app.add_handler(CommandHandler("id", my_id))
  app.add_handler(MessageHandler(filters.PHOTO, on_photo))
  app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
  main()

