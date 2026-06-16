import logging
import os
import sys
from datetime import datetime

import api_client

user_logger = logging.getLogger("user_interactions")
user_logger.setLevel(logging.INFO)
user_logger.propagate = False

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
user_logger.addHandler(_console_handler)

_file_handler_added = False


_log_file_path = None


def init_user_logger():
    global _file_handler_added, _log_file_path
    if _file_handler_added:
        return _log_file_path
    log_path = api_client.get_setting("tasks.log.path") or "./logs"
    if not os.path.isabs(log_path):
        api_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "CardVault-API"))
        log_path = os.path.join(api_root, log_path)
    os.makedirs(log_path, exist_ok=True)
    fh = logging.FileHandler(os.path.join(log_path, "telegram_bot.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    user_logger.addHandler(fh)
    _file_handler_added = True
    _log_file_path = os.path.join(log_path, "telegram_bot.log")
    return _log_file_path


def _log_direct(level: str, msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} [{level}] {msg}"
    sys.stderr.write(line + "\n")
    sys.stderr.flush()
    if _log_file_path:
        try:
            with open(_log_file_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass
