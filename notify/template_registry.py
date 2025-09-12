import json, os, threading
from django.conf import settings

_LOCK = threading.Lock()
_CACHE = None
_MTIME = None

def _path():
    return os.path.join(os.path.dirname(__file__), "templates", "templates.json")

def _load():
    global _CACHE, _MTIME
    p = _path()
    with open(p, "r", encoding="utf-8") as f:
        _CACHE = json.load(f)
    _MTIME = os.path.getmtime(p)

def get_templates():
    global _CACHE, _MTIME
    with _LOCK:
        p = _path()
        if _CACHE is None:
            _load()
        elif getattr(settings, "DEBUG", False):
            m = os.path.getmtime(p)
            if m != _MTIME:
                _load()
        return _CACHE

def get_block(template_key: str, channel: str):
    data = get_templates()
    t = data.get(template_key)
    if not t:
        raise KeyError(f"template '{template_key}' not found")
    ch = t.get("channels", {}).get(channel)
    if not ch:
        raise KeyError(f"channel '{channel}' not found for template '{template_key}'")
    req = set(t.get("required_vars", []))
    return ch, req
