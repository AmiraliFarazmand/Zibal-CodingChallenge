from django.utils import timezone
from mongo import get_collection

def log_attempt(*, task_id: str, channel: str, merchant_id: str, lang: str,
                attempt_no: int, status: str, provider: str,
                request_meta: dict, response_meta: dict | None, error: str | None):
    coll = get_collection("notification_logs")
    coll.insert_one({
        "task_id": task_id,
        "channel": channel,
        "merchantId": merchant_id,
        "lang": lang,
        "attempt_no": attempt_no,
        "status": status,  # 'sent' | 'failed'
        "provider": provider,
        "request_meta": request_meta,       # sizes / recipient preview (no secrets)
        "response_meta": response_meta or {},
        "error": error,
        "timestamp": timezone.now(),
    })
