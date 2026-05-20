import httpx
from datetime import datetime, timezone
from config import API_BASE_URL, API_USERNAME, API_PASSWORD

TIMEOUT = 10

_token: str | None = None
_token_expires_at: datetime | None = None
_SETTINGS_CACHE: dict[str, str] | None = None


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


def get_bot_admin_ids() -> set[int]:
    raw = get_setting("bot.telegram.admin.ids") or ""
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


def catalog_search(query: str = "", page: int = 1, per_page: int = 5) -> dict | None:
    return _get("/product-catalog/", params={"q": query, "page": page, "per_page": per_page})


def get_inventory(page: int = 1, per_page: int = 5, **filters) -> dict | None:
    params = {"page": page, "per_page": per_page}
    params.update({k: v for k, v in filters.items() if v is not None})
    return _get("/inventory/", params=params)


def get_collections(page: int = 1, per_page: int = 50) -> dict | None:
    return _get("/collections/", params={"page": page, "per_page": per_page})


def get_file_url(file_id: int) -> str:
    return f"{API_BASE_URL}/product-catalog/files/{file_id}/content"
