from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import api_client
from auth import require_auth, require_admin
from formatters import (
    fmt_catalog_item, fmt_inventory_item,
    pagination_keyboard, )


@require_auth
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    text = (
        f"👋 Hola, <b>{name}</b>! Bienvenido a <b>CardVault Bot</b>.\n\n"
        "Comandos disponibles:\n"
        "🔍 /buscar <i>nombre</i> — Busca cartas en el catálogo\n"
        "📦 /inventario — Lista tu inventario\n"
        "🗂 /colecciones — Lista colecciones disponibles\n"
        "ℹ️ /ayuda — Muestra esta ayuda"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


@require_auth
async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 <b>Ayuda de CardVault Bot</b>\n\n"
        "<b>Catálogo</b>\n"
        "  /buscar <i>texto</i> — Busca por nombre, número o colección\n"
        "  /buscar — Sin texto muestra los primeros resultados\n\n"
        "<b>Inventario</b>\n"
        "  /inventario — Muestra todo el inventario\n"
        "  /inventario <i>texto</i> — Busca en el inventario\n\n"
        "<b>Colecciones</b>\n"
        "  /colecciones — Lista todas las colecciones\n\n"
        "<b>Administración</b> (solo admins)\n"
        "  /adduser <i>telegram_id</i> — Autoriza un usuario\n"
        "  /deluser <i>telegram_id</i> — Revoca acceso\n"
        "  /usuarios — Lista usuarios autorizados\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


@require_auth
async def cmd_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args) if context.args else ""
    await _send_catalog_page(update, context, query=query, page=1)


async def _send_catalog_page(update_or_query, context, query: str, page: int):
    is_callback = hasattr(update_or_query, "message") and update_or_query.message is None
    send_fn = (
        update_or_query.edit_message_text
        if is_callback
        else (update_or_query.message or update_or_query).reply_text
    )

    data = api_client.catalog_search(query=query, page=page, per_page=5)
    if not data or not data.get("items"):
        await send_fn("❌ No se encontraron resultados.", parse_mode=ParseMode.HTML)
        return

    items = data["items"]
    pagination = data.get("pagination", {})
    total = pagination.get("total", 0)
    pages = pagination.get("pages", 1)

    lines = [
        f"🔍 Resultados para <b>'{query}'</b> — {total} encontrados\n" if query else f"📋 Catálogo — {total} productos\n"]
    for item in items:
        lines.append(fmt_catalog_item(item))
        lines.append("")

    text = "\n".join(lines).strip()

    prefix = f"catalog:{query}"
    nav_kb = pagination_keyboard(page, pages, prefix)
    buttons = []

    for item in items:
        pid = item["product_id"]
        file_id = item.get("file_id")
        name = (item.get("product_name") or item.get("product_number") or f"#{pid}")[:30]
        row = [InlineKeyboardButton(f"📋 {name}", callback_data=f"inv_product:{pid}:1")]
        if file_id:
            row.append(InlineKeyboardButton("🖼", callback_data=f"img:{file_id}"))
        buttons.append(row)

    if nav_kb:
        buttons.extend(nav_kb.inline_keyboard)

    kb = InlineKeyboardMarkup(buttons) if buttons else None
    await send_fn(text, parse_mode=ParseMode.HTML, reply_markup=kb)


@require_auth
async def cmd_inventario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_inventory_page(update, context, page=1)


async def _send_inventory_page(update_or_msg, context, page: int, product_id: int = None):
    is_callback = not hasattr(update_or_msg, "message") or update_or_msg.message is None
    send_fn = (
        update_or_msg.edit_message_text
        if is_callback
        else (getattr(update_or_msg, "message", None) or update_or_msg).reply_text
    )

    kwargs = {}
    if product_id:
        kwargs["product_id"] = product_id

    data = api_client.get_inventory(page=page, per_page=5, **kwargs)
    if not data or not data.get("items"):
        await send_fn("❌ No hay registros en el inventario.", parse_mode=ParseMode.HTML)
        return

    items = data["items"]
    pagination = data.get("pagination", {})
    total = pagination.get("total", 0)
    pages = pagination.get("pages", 1)

    header = f"📦 <b>Inventario</b> — {total} registros\n"
    lines = [header]
    for item in items:
        lines.append(fmt_inventory_item(item))
        lines.append("")

    text = "\n".join(lines).strip()
    prefix = f"inv_product:{product_id}" if product_id else "inv"
    nav_kb = pagination_keyboard(page, pages, f"{prefix}")
    await send_fn(text, parse_mode=ParseMode.HTML, reply_markup=nav_kb)


@require_auth
async def cmd_colecciones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = api_client.get_collections(per_page=50)
    if not data or not data.get("items"):
        await update.message.reply_text("❌ No se pudieron cargar las colecciones.")
        return

    items = data["items"]
    lines = ["🗂 <b>Colecciones disponibles</b>\n"]
    for col in items:
        card_type = (col.get("card_type") or {}).get("short_name", "")
        code = col.get("code", "")
        release = col.get("release_date", "") or ""
        release = f" ({release[:4]})" if release else ""
        lines.append(f"  <code>{card_type}</code> · <b>{code}</b>{release}")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


@require_admin
async def cmd_adduser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Uso: /adduser <telegram_id>")
        return
    tid = int(context.args[0])
    ok = api_client.add_authorized_telegram_id(tid)
    if ok:
        await update.message.reply_text(f"✅ Usuario {tid} autorizado.")
    else:
        await update.message.reply_text(f"⚠️ No se pudo añadir {tid} (¿ya existe?).")


@require_admin
async def cmd_deluser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Uso: /deluser <telegram_id>")
        return
    tid = int(context.args[0])
    ok = api_client.remove_authorized_telegram_id(tid)
    if ok:
        await update.message.reply_text(f"✅ Usuario {tid} eliminado.")
    else:
        await update.message.reply_text(f"⚠️ No se pudo eliminar {tid}.")


@require_admin
async def cmd_usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ids = api_client.get_authorized_telegram_ids()
    admins = api_client.get_bot_admin_ids()
    if not ids:
        await update.message.reply_text("No hay usuarios autorizados.")
        return
    lines = ["👥 <b>Usuarios autorizados</b>\n"]
    for tid in sorted(ids):
        tag = " 👑" if tid in admins else ""
        lines.append(f"  <code>{tid}</code>{tag}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data.startswith("catalog:"):
        parts = data.split(":")
        page = int(parts[-1])
        search_q = ":".join(parts[1:-1])
        await _send_catalog_page(query, context, query=search_q, page=page)

    elif data.startswith("inv_product:"):
        parts = data.split(":")
        product_id = int(parts[1])
        page = int(parts[2])
        await _send_inventory_page(query, context, page=page, product_id=product_id)

    elif data.startswith("inv:"):
        page = int(data.split(":")[1])
        await _send_inventory_page(query, context, page=page)

    elif data.startswith("img:"):
        file_id = int(data.split(":")[1])
        url = api_client.get_file_url(file_id)
        try:
            await query.message.reply_photo(photo=url)
        except Exception:
            await query.message.reply_text(f"🖼 Imagen: {url}")
