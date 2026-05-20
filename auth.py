import logging
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

import api_client

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def require_auth(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        allowed = api_client.get_authorized_telegram_ids()
        logger.info(f"El usuario {user_id} ha intentado acceder, permitido: {allowed}")
        if not allowed or user_id not in allowed:
            await update.effective_message.reply_text(
                "🚫 No tienes acceso a este bot.\n"
                "Solicita acceso a un administrador."
            )
            return
        return await func(update, context, *args, **kwargs)

    return wrapper


def require_admin(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        admins = api_client.get_bot_admin_ids()
        if not admins or user_id not in admins:
            await update.effective_message.reply_text("🚫 Solo los administradores pueden hacer eso.")
            return
        return await func(update, context, *args, **kwargs)

    return wrapper
