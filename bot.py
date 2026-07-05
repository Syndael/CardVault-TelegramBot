import logging
import sys
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

import api_client
from handlers import cmd_n, cmd_s, cmd_id, cmd_compra, callback_handler, unknown_handler, text_handler
from user_logger import init_user_logger

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

SETTING_KEY_TOKEN = "bot.telegram.token"


def main():
    if not api_client.login():
        logger.error("Error al autenticar en la API")
        sys.exit(1)
    logger.info("API login OK")

    token = api_client.get_setting(SETTING_KEY_TOKEN)
    if not token:
        logger.error(f"Setting '{SETTING_KEY_TOKEN}' no encontrado. Debes crearlo en la API.")
        sys.exit(1)

    app = ApplicationBuilder().token(token).build()

    log_file = init_user_logger()
    logger.info("User interaction log: %s", log_file)

    app.add_handler(CommandHandler("n", cmd_n))
    app.add_handler(CommandHandler("s", cmd_s))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("compra", cmd_compra))
    app.add_handler(CallbackQueryHandler(callback_handler))

    app.add_handler(text_handler)
    app.add_handler(unknown_handler)

    logger.info("CardVault Bot iniciado")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
