from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def _resolve_name(item: dict, languages_by_id: dict[int, dict]) -> str:
    translations = (item.get("product") or {}).get("translations", [])
    inv_lang_id = (item.get("language") or {}).get("id")

    if inv_lang_id:
        for t in translations:
            if t.get("language_id") == inv_lang_id and t.get("name"):
                return t["name"]

    best = None
    best_priority = 999
    for t in translations:
        lang = languages_by_id.get(t.get("language_id"))
        priority = lang.get("priority_order", 999) if lang else 999
        if priority < best_priority and t.get("name"):
            best = t["name"]
            best_priority = priority

    return best or (item.get("product") or {}).get("product_number") or "\u2014"


def _resolve_alt_name(item: dict, languages_by_id: dict[int, dict]) -> str | None:
    translations = (item.get("product") or {}).get("translations", [])
    inv_lang_id = (item.get("language") or {}).get("id")
    main_name = _resolve_name(item, languages_by_id)

    best = None
    best_priority = 999
    for t in translations:
        lang_id = t.get("language_id")
        if lang_id == inv_lang_id:
            continue
        if not t.get("name") or t["name"] == main_name:
            continue
        lang = languages_by_id.get(lang_id)
        priority = lang.get("priority_order", 999) if lang else 999
        if priority < best_priority:
            best = t["name"]
            best_priority = priority

    return best


def fmt_list_item(item: dict, languages_by_id: dict[int, dict]) -> str:
    inv_id = item["id"]
    code = (item.get("collection") or {}).get("code", "")
    number = (item.get("product") or {}).get("product_number", "")
    name = _resolve_name(item, languages_by_id)
    alt = _resolve_alt_name(item, languages_by_id)

    parts = [f"<b>{inv_id}</b> (<i>{code}</i> {number}) {name}"]
    if alt:
        parts.append(f"({alt})")
    return " ".join(parts)


def fmt_detail(item: dict, urls: list[dict], languages_by_id: dict[int, dict]) -> str:
    inv_id = item["id"]
    code = (item.get("collection") or {}).get("code", "")
    number = (item.get("product") or {}).get("product_number", "")
    name = _resolve_name(item, languages_by_id)
    lang = (item.get("language") or {}).get("abbreviation", "\u2014")
    cond = (item.get("condition") or {}).get("abbreviation", "\u2014")
    qty = item.get("quantity", 1)
    sealed = "Sellado" if item.get("is_sealed") else ""
    notes = item.get("notes") or ""

    lines = [
        f"<b>{name}</b>",
        f"<i>{code}</i> #{number}  |  <b>{inv_id}</b>",
        f"Idioma: {lang}  |  Estado: {cond}  |  Qty: {qty}",
    ]
    if sealed:
        lines.append(f"  {sealed}")
    if notes:
        lines.append(f"")
        lines.append(f"Notas: {notes}")

    acq = item.get("acquisition_price")
    cur = item.get("current_price")
    mn = item.get("min_price")
    mx = item.get("max_price")
    lines.append(f"")
    prices = []
    if acq is not None:
        prices.append(f"Adq: {float(acq):.2f} EUR")
    if cur is not None:
        prices.append(f"Act: {float(cur):.2f} EUR")
    if mn is not None:
        prices.append(f"Min: {float(mn):.2f} EUR")
    if mx is not None:
        prices.append(f"Max: {float(mx):.2f} EUR")
    if prices:
        lines.append("  |  ".join(prices))

    purchase_item = item.get("purchase_item")
    purchase = item.get("purchase")
    if purchase:
        entity = (purchase.get("entity") or {}).get("name", "")
        total = purchase.get("total_amount")
        shipping = purchase.get("shipping_cost", 0)
        currency = purchase.get("currency", "EUR")
        p_notes = purchase.get("notes") or ""
        lines.append(f"")
        lines.append(f"<b>Compra</b>")
        if entity:
            lines.append(f"Tienda: {entity}")
        unit_price = (purchase_item or {}).get("unit_price")
        split_qty = (purchase_item or {}).get("split_quantity") or 1
        if unit_price is not None:
            display_price = float(unit_price) / split_qty
            lines.append(f"Precio unitario: {display_price:.2f} {currency}" + (f" (repartido entre {split_qty})" if split_qty > 1 else ""))
        if total is not None:
            lines.append(f"Total: {float(total):.2f} {currency}")
        if shipping and float(shipping) > 0:
            lines.append(f"Gastos envio: {float(shipping):.2f} {currency}")
        # Mostrar info de moneda original si existe
        orig_amount = purchase.get("original_amount")
        orig_currency = purchase.get("original_currency")
        if orig_amount and orig_currency:
            lines.append(f"Importe original: {float(orig_amount):.2f} {orig_currency}")
        if p_notes:
            lines.append(f"Notas compra: {p_notes[:200]}")

    if urls:
        lines.append(f"")
        lines.append(f"<b>Enlaces</b>")
        for u in urls:
            label = u.get("name") or u["url"]
            lines.append(f'<a href="{u["url"]}">{label}</a>')

    return "\n".join(lines)


def list_keyboard(items: list[dict], languages_by_id: dict[int, dict]) -> InlineKeyboardMarkup:
    buttons = []
    for item in items:
        inv_id = item["id"]
        code = (item.get("collection") or {}).get("code", "")
        number = (item.get("product") or {}).get("product_number", "")
        name = _resolve_name(item, languages_by_id)
        alt = _resolve_alt_name(item, languages_by_id)

        label = f"({code} {number}) {name}"
        if alt:
            label += f" ({alt})"
        if len(label) > 60:
            label = label[:57] + "..."
        buttons.append([InlineKeyboardButton(label, callback_data=f"d:{inv_id}")])
    return InlineKeyboardMarkup(buttons)
