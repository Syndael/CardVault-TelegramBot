import httpx
from datetime import datetime, timezone
from config import API_BASE_URL, API_USERNAME, API_PASSWORD

TIMEOUT = 15

_token: str | None = None
_token_expires_at: datetime | None = None
_SETTINGS_CACHE: dict[str, str] | None = None
_LANGUAGES_CACHE: list[dict] | None = None


def login() -> bool:
    return _login()


def _login() -> bool:
    global _token, _token_expires_at
    try:
        r = httpx.post(
            f"{API_BASE_URL}/auth/login",
            json={"username": API_USERNAME, "password": API_PASSWORD},
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return False
        data = r.json()
        _token = data["token"]
        _token_expires_at = datetime.fromisoformat(data["expires_at"]).replace(tzinfo=timezone.utc)
        return True
    except Exception:
        return False


def _get_token() -> str | None:
    global _token, _token_expires_at
    now = datetime.now(timezone.utc)
    if not _token or not _token_expires_at or _token_expires_at <= now:
        _login()
    return _token


def _headers() -> dict:
    token = _get_token()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _get(path: str, params: dict = None) -> dict | list | None:
    try:
        r = httpx.get(f"{API_BASE_URL}{path}", params=params, headers=_headers(), timeout=TIMEOUT)
        if r.status_code == 401:
            if _login():
                r = httpx.get(f"{API_BASE_URL}{path}", params=params, headers=_headers(), timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _post(path: str, body: dict) -> httpx.Response | None:
    try:
        r = httpx.post(f"{API_BASE_URL}{path}", json=body, headers=_headers(), timeout=TIMEOUT)
        if r.status_code == 401:
            if _login():
                r = httpx.post(f"{API_BASE_URL}{path}", json=body, headers=_headers(), timeout=TIMEOUT)
        return r
    except Exception:
        return None


def _put(path: str, body: dict) -> bool:
    try:
        r = httpx.put(f"{API_BASE_URL}{path}", json=body, headers=_headers(), timeout=TIMEOUT)
        if r.status_code == 401:
            if _login():
                r = httpx.put(f"{API_BASE_URL}{path}", json=body, headers=_headers(), timeout=TIMEOUT)
        return r.status_code < 300
    except Exception:
        return False


def _load_all_settings() -> dict[str, str]:
    result: dict[str, str] = {}
    page = 1
    while True:
        data = _get("/settings/", params={"page": page, "per_page": 100})
        if not data:
            break
        for item in data.get("items", []):
            result[item["setting_key"]] = item.get("setting_value") or ""
        if not data.get("pagination", {}).get("has_next"):
            break
        page += 1
    return result


def _get_settings() -> dict[str, str]:
    global _SETTINGS_CACHE
    if _SETTINGS_CACHE is None:
        _SETTINGS_CACHE = _load_all_settings()
    return _SETTINGS_CACHE


def invalidate_settings_cache():
    global _SETTINGS_CACHE
    _SETTINGS_CACHE = None


def get_setting(key: str) -> str | None:
    return _get_settings().get(key)


def _find_setting_id(key: str) -> int | None:
    page = 1
    while True:
        data = _get("/settings/", params={"page": page, "per_page": 100})
        if not data:
            return None
        for item in data.get("items", []):
            if item["setting_key"] == key:
                return item["id"]
        if not data.get("pagination", {}).get("has_next"):
            return None
        page += 1


def _upsert_setting(key: str, value: str) -> bool:
    setting_id = _find_setting_id(key)
    if setting_id:
        ok = _put(f"/settings/{setting_id}", {"setting_key": key, "setting_value": value})
    else:
        r = _post("/settings/", {"setting_key": key, "setting_value": value})
        ok = r is not None and r.status_code < 300
    if ok:
        invalidate_settings_cache()
    return ok


def get_authorized_telegram_ids() -> set[int]:
    raw = get_setting("bot.telegram.allowed.ids") or ""
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids


def add_authorized_telegram_id(telegram_id: int) -> bool:
    current = get_setting("bot.telegram.allowed.ids") or ""
    parts = [p.strip() for p in current.split(",") if p.strip()]
    sid = str(telegram_id)
    if sid in parts:
        return False
    parts.append(sid)
    return _upsert_setting("bot.telegram.allowed.ids", ",".join(parts))


def remove_authorized_telegram_id(telegram_id: int) -> bool:
    current = get_setting("bot.telegram.allowed.ids") or ""
    parts = [p.strip() for p in current.split(",") if p.strip() and p.strip() != str(telegram_id)]
    return _upsert_setting("bot.telegram.allowed.ids", ",".join(parts))


def get_bot_admin_ids() -> set[int]:
    raw = get_setting("bot.telegram.admin.ids") or ""
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids


# --- Inventory API ---

def search_inventory(product_name: str, page: int = 1, per_page: int = 8) -> dict | None:
    return _get("/inventory/", params={
        "product_name": product_name,
        "page": page,
        "per_page": per_page,
        "all": "1",
        "sort": "newest",
    })


def get_inventory_item(inventory_id: int) -> dict | None:
    return _get(f"/inventory/{inventory_id}")


def get_inventory_urls(inventory_id: int) -> list[dict]:
    data = _get(f"/inventory-urls/by-inventory/{inventory_id}")
    if isinstance(data, list):
        return data
    return []


def get_file_url(file_id: int) -> str:
    token = _get_token()
    base = API_BASE_URL.rstrip("/api") if API_BASE_URL.endswith("/api") else API_BASE_URL
    if token:
        return f"{base}/api/product-catalog/files/{file_id}/content?token={token}"
    return f"{base}/api/product-catalog/files/{file_id}/content"


def get_languages() -> list[dict]:
    global _LANGUAGES_CACHE
    if _LANGUAGES_CACHE is None:
        data = _get("/languages/", params={"per_page": 100})
        if data:
            _LANGUAGES_CACHE = data.get("items", data if isinstance(data, list) else [])
        else:
            _LANGUAGES_CACHE = []
    return _LANGUAGES_CACHE


def invalidate_languages_cache():
    global _LANGUAGES_CACHE
    _LANGUAGES_CACHE = None


def download_file(url: str) -> bytes | None:
    try:
        r = httpx.get(url, headers=_headers(), timeout=TIMEOUT)
        r.raise_for_status()
        return r.content
    except Exception:
        return None


def resolve_url(relative_url: str | None) -> str | None:
    if not relative_url:
        return None
    token = _get_token()
    base = API_BASE_URL.rstrip("/api") if API_BASE_URL.endswith("/api") else API_BASE_URL
    sep = "&" if "?" in relative_url else "?"
    if token:
        return f"{base}{relative_url}{sep}token={token}"
    return f"{base}{relative_url}"


def get_product_tracking(product_id: int) -> list[dict]:
    items = []
    page = 1
    while True:
        data = _get("/product-price-tracking/", params={"product_id": product_id, "page": page, "per_page": 50})
        if not data:
            return items
        batch = data.get("items", []) if isinstance(data, dict) else []
        items.extend(batch)
        if isinstance(data, dict) and not data.get("pagination", {}).get("has_next"):
            break
        page += 1
    return items


def get_latest_price(inventory_id: int) -> dict | None:
    data = _get("/inventory-price-history/", params={"inventory_id": inventory_id, "page": 1, "per_page": 1})
    if not data:
        return None
    items = data.get("items", []) if isinstance(data, dict) else []
    return items[0] if items else None
