from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, filters
from telegram.ext import MessageHandler

import api_client
from auth import require_auth
from formatters import fmt_list_item, fmt_detail, list_keyboard
from user_logger import _log_direct


def _get_languages_by_id() -> dict[int, dict]:
    return {lang["id"]: lang for lang in api_client.get_languages()}


def _user_info(update: Update) -> str:
    u = update.effective_user
    if u:
        return f"user#{u.id} {u.full_name or u.username or ''}"
    return "user#?"


@require_auth
async def cmd_n(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args) if context.args else ""
    _log_direct("INFO", f"[{_user_info(update)}] /n {query}")
    if not query:
        await update.message.reply_text("Uso: /n <nombre del producto>")
        return

    context.user_data["search_name"] = query
    context.user_data["cross_search"] = False
    await _send_list(update.message, context)


@require_auth
async def cmd_s(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args) if context.args else ""
    _log_direct("INFO", f"[{_user_info(update)}] /s {query}")
    if not query:
        await update.message.reply_text("Uso: /s <texto>")
        return

    context.user_data["search_name"] = query
    context.user_data["cross_search"] = True
    await _send_list(update.message, context)


@require_auth
async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _log_direct("INFO", f"[{_user_info(update)}] /id {' '.join(context.args or [])}")
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Uso: /id <id del inventario>")
        return

    inv_id = int(context.args[0])
    await _send_detail(update.message, context, inv_id)


async def _send_list(msg, context):
    search_name = context.user_data.get("search_name", "")
    cross = context.user_data.get("cross_search", False)
    languages_by_id = _get_languages_by_id()

    if cross:
        data = api_client.search_inventory_cross(search_name, page=1, per_page=20)
    else:
        data = api_client.search_inventory(search_name, page=1, per_page=20)

    if not data or not data.get("items"):
        text = f'No se encontraron resultados para "{search_name}"'
        await msg.reply_text(text, parse_mode=ParseMode.HTML)
        return

    items = data["items"]

    if len(items) == 1:
        await _send_detail(msg, context, items[0]["id"])
        return

    kb = list_keyboard(items, languages_by_id)

    await msg.reply_text(
        f'Resultados para "<b>{search_name}</b>" \u2014 {len(items)} encontrados',
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )


async def _send_detail(msg, context, inv_id: int):
    languages_by_id = _get_languages_by_id()
    item = api_client.get_inventory_item(inv_id)

    if not item:
        text = f"No se encontro el item #{inv_id}"
        await msg.reply_text(text)
        return

    product_id = (item.get("product") or {}).get("id")
    urls = api_client.get_inventory_urls(inv_id)
    text = fmt_detail(item, urls, languages_by_id)

    extra = []

    if product_id:
        tracking = api_client.get_product_tracking(product_id)
        if tracking:
            extra.append("")
            extra.append("<b>Seguimiento precios</b>")
            for tr in tracking:
                ps = tr.get("price_source") or {}
                label = ps.get("name", "Enlace")
                tr_url = tr.get("url", "")
                extra.append(f'{label}: <a href="{tr_url}">{tr_url[:60]}</a>')

    latest = api_client.get_latest_price(inv_id)
    if latest:
        extra.append("")
        extra.append("<b>Ultimo precio registrado</b>")
        p = latest.get("price")
        if p is not None:
            extra.append(f"Precio: {float(p):.2f} EUR")
        mn = latest.get("min_price")
        mx = latest.get("max_price")
        if mn is not None:
            md = (latest.get("min_price_recorded_at") or "")[:10]
            extra.append(f"Min: {float(mn):.2f} EUR ({md})")
        if mx is not None:
            xd = (latest.get("max_price_recorded_at") or "")[:10]
            extra.append(f"Max: {float(mx):.2f} EUR ({xd})")
        recorded = latest.get("recorded_at", "")[:16]
        if recorded:
            extra.append(f"Registrado: {recorded}")

    if extra:
        text += "\n" + "\n".join(extra)

    inv_files = api_client.get_inventory_files(inv_id)
    _log_direct("DEBUG", f"inv#{inv_id} inventory_files={len(inv_files)}")

    if inv_files:
        for f in inv_files:
            fid = f.get("id")
            fname = f.get("stored_name") or f.get("original_name") or f"inv_{inv_id}.jpg"
            url = api_client.get_file_url(fid)
            _log_direct("DEBUG", f"downloading inv file #{fid}: {url}")
            img_data = api_client.download_file(url)
            if img_data:
                try:
                    await msg.reply_document(document=img_data, filename=fname)
                    _log_direct("DEBUG", f"inv file #{fid} sent OK")
                except Exception as e:
                    _log_direct("ERROR", f"inv file #{fid} send failed: {e}")
            else:
                _log_direct("DEBUG", f"inv file #{fid} download returned no data")
    else:
        prod_img = item.get("product_image_url")
        _log_direct("DEBUG", f"inv#{inv_id} no inventory files, fallback to product_image_url={prod_img}")
        if prod_img:
            full_url = api_client.resolve_url(prod_img)
            _log_direct("DEBUG", f"downloading product photo: {full_url}")
            img_data = api_client.download_file(full_url)
            if img_data:
                try:
                    await msg.reply_document(document=img_data, filename=f"inv_{inv_id}.jpg")
                    _log_direct("DEBUG", "product photo sent OK")
                except Exception as e:
                    _log_direct("ERROR", f"product photo send failed: {e}")
            else:
                _log_direct("DEBUG", "product photo download returned no data")

    await msg.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    _log_direct("INFO", f"[{_user_info(update)}] callback {data}")

    if data.startswith("d:"):
        inv_id = int(data.split(":")[1])
        await _send_detail(query.message, context, inv_id)


async def cmd_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _log_direct("INFO", f"[{_user_info(update)}] unknown command: {update.message.text or ''}")
    await update.message.reply_text(_help_text, parse_mode=ParseMode.HTML)


unknown_handler = MessageHandler(filters.COMMAND, cmd_unknown)


_help_text = (
    "\U0001f916 <b>CardVault Bot</b>\n\n"
    "Comandos disponibles:\n\n"
    "n <i>texto</i> \u2014 Buscar productos por nombre en el inventario\n"
    "s <i>texto</i> \u2014 Buscar productos por c\u00f3digo colecci\u00f3n, n\u00famero o nombre\n"
    "/id <i>numero</i> \u2014 Ver detalle de un item\n\n"
    "Ejemplos:\n"
    "n pikachu\n"
    "s COL 001\n"
    "/id 42\n\n"
    "Tambi\u00e9n funciona con /n y /s"
)


@require_auth
async def cmd_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    _log_direct("INFO", f"[{_user_info(update)}] text: {text}")

    # Check for n <query> (no slash)
    if text.lower().startswith("n ") and len(text) > 2:
        query = text[2:].strip()
        if query:
            context.user_data["search_name"] = query
            context.user_data["cross_search"] = False
            await _send_list(update.message, context)
            return

    # Check for s <query> (no slash)
    if text.lower().startswith("s ") and len(text) > 2:
        query = text[2:].strip()
        if query:
            context.user_data["search_name"] = query
            context.user_data["cross_search"] = True
            await _send_list(update.message, context)
            return

    await update.message.reply_text(_help_text, parse_mode=ParseMode.HTML)


text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_text)
