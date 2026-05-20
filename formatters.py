from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def fmt_catalog_item(item: dict) -> str:
    collection = item.get("collection_name") or item.get("collection_code", "")
    number     = item.get("product_number") or "—"
    name       = item.get("product_name") or "Sin nombre"
    lines = [
        f"📦 <b>{name}</b>",
        f"   <i>{collection}</i> · #{number}",
    ]
    return "\n".join(lines)


def fmt_inventory_item(item: dict) -> str:
    product    = item.get("product", {}) or {}
    collection = (item.get("collection") or {}).get("code", "")
    number     = product.get("product_number") or "—"

    translations = product.get("translations", [])
    name = translations[0].get("name") if translations else "Sin nombre"

    lang      = (item.get("language")  or {}).get("abbreviation", "—")
    condition = (item.get("condition") or {}).get("abbreviation", "—")
    qty       = item.get("quantity", 1)
    sealed    = "🔒 Sellado" if item.get("is_sealed") else ""
    notes     = item.get("notes") or ""

    lines = [
        f"🃏 <b>{name}</b>",
        f"   {collection} · #{number}",
        f"   Idioma: <b>{lang}</b> · Estado: <b>{condition}</b> · Qty: <b>{qty}</b>",
    ]
    if sealed:
        lines.append(f"   {sealed}")
    if notes:
        lines.append(f"   📝 {notes[:80]}")
    return "\n".join(lines)


def pagination_keyboard(current_page: int, total_pages: int, callback_prefix: str) -> InlineKeyboardMarkup | None:
    buttons = []
    if current_page > 1:
        buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"{callback_prefix}:{current_page - 1}"))
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton("Siguiente ➡️", callback_data=f"{callback_prefix}:{current_page + 1}"))
    if not buttons:
        return None
    return InlineKeyboardMarkup([buttons])


def catalog_item_keyboard(product_id: int, file_id: int | None) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📋 Ver inventario", callback_data=f"inv_product:{product_id}:1")],
    ]
    if file_id:
        buttons.append([InlineKeyboardButton("🖼 Ver imagen", callback_data=f"img:{file_id}")])
    return InlineKeyboardMarkup(buttons)
