from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

import api_client
from user_logger import _log_direct


def require_auth(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        u = update.effective_user
        info = f"user#{user_id} {u.full_name or u.username or ''}" if u else f"user#{user_id}"
        allowed = api_client.get_authorized_telegram_ids()
        if not allowed or user_id not in allowed:
            _log_direct("WARN", f"[{info}] acceso DENEGADO")
            await update.effective_message.reply_text(
                "No tienes acceso a este bot.\nSolicita acceso a un administrador."
            )
            return
        _log_direct("INFO", f"[{info}] acceso OK")
        return await func(update, context, *args, **kwargs)
    return wrapper
