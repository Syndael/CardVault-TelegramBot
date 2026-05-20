import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
)

from config import TELEGRAM_BOT_TOKEN
from handlers import (
    cmd_start, cmd_ayuda, cmd_buscar,
    cmd_inventario, cmd_colecciones,
    cmd_adduser, cmd_deluser, cmd_usuarios,
    callback_handler,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("ayuda",       cmd_ayuda))
    app.add_handler(CommandHandler("help",        cmd_ayuda))
    app.add_handler(CommandHandler("buscar",      cmd_buscar))
    app.add_handler(CommandHandler("inventario",  cmd_inventario))
    app.add_handler(CommandHandler("colecciones", cmd_colecciones))
    app.add_handler(CommandHandler("adduser",     cmd_adduser))
    app.add_handler(CommandHandler("deluser",     cmd_deluser))
    app.add_handler(CommandHandler("usuarios",    cmd_usuarios))
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("CardVault Bot iniciado")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
