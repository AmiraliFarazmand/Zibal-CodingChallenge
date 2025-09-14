import random
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from faker import Faker

from .template_registry import get_block
from .providers import SMSProvider, EmailProvider, TelegramProvider, TransientError, PermanentError
from .logging import log_attempt

# Helpers
def _faker_params(merchant_id: str) -> dict:
    fk = Faker('fa_IR')
    return {
        "merchantId": merchant_id,
        "name": fk.name(),
        "otp_code": str(random.randint(100000, 999999)),
        "reset_link": fk.url() + "?token=" + fk.md5(),
        "expiry_minutes": 15,
    }

def _render(template_key: str, channel: str, lang: str, params: dict):
    block, required = get_block(template_key, channel)
    missing = [k for k in required if k not in params]
    if missing:
        raise PermanentError(f"missing vars: {missing}")

    if channel in ("sms", "telegram"):
        key = "fa" if lang == "fa" else "en"
        return {"text": block[key].format(**params)}
    if channel == "email":
        subj = block["fa_subject" if lang == "fa" else "en_subject"].format(**params)
        txt  = block["fa_text" if lang == "fa" else "en_text"].format(**params)
        html = block["fa_html" if lang == "fa" else "en_html"].format(**params)
        return {"subject": subj, "text": txt, "html": html}
    raise PermanentError("unsupported channel")

def _provider(channel: str):
    return {"sms": SMSProvider, "email": EmailProvider, "telegram": TelegramProvider}[channel]()

def _recipient(channel: str):
    fk = Faker()
    if channel == "sms":      return {"phone": "+989" + str(random.randint(100000000, 999999999))}
    if channel == "email":    return {"email": fk.email()}
    if channel == "telegram": return {"chat_id": random.randint(10_000_000, 99_999_999)}
    return {}


@shared_task(bind=True, name="notify.send_reset_password", queue="notifications")
def send_reset_password_task(self, merchant_id: str, channel: str, lang: str, *args, **kwargs):
    # We compute attempt_no from how many logs exist for this task_id
    from mongo import get_collection
    task_id = self.request.id

    template_key = "reset_password"
    params = _faker_params(merchant_id)
    payload = _render(template_key, channel, lang, params)
    prov = _provider(channel)
    rcpt = _recipient(channel)

    # for logging; calculate size of text and other data
    req_meta = {"provider": prov.name}
    if channel == "sms":
        req_meta.update({"to": rcpt["phone"], "size": len(payload["text"])})
    elif channel == "telegram":
        req_meta.update({"chat_id": rcpt["chat_id"], "size": len(payload["text"])})
    else:
        req_meta.update({"to": rcpt["email"], "subject_len": len(payload["subject"]), "text_len": len(payload["text"])})

    # what attempt number is this?
    logs = get_collection("notification_logs")
    attempt_no = logs.count_documents({"task_id": task_id}) + 1

    try:
        print("".join(["\n", "#"*10,"\n",'\t'*2,payload["text"],"\n","#"*10,"\n"]))
        if channel == "sms":
            resp = prov.send(text=payload["text"], phone=rcpt["phone"])
        elif channel == "email":
            resp = prov.send(subject=payload["subject"], text=payload["text"], html=payload["html"], email=rcpt["email"])
        else:
            chat_id = kwargs.get("chat_id", rcpt["chat_id"])
            resp = prov.send(text=payload["text"], chat_id=chat_id)

        # success
        log_attempt(task_id=task_id, channel=channel, merchant_id=merchant_id, lang=lang,
                    attempt_no=attempt_no, status="sent", provider=prov.name,
                    request_meta=req_meta, response_meta=resp, error=None)
        return {"ok": True, "provider_id": resp.get("provider_id")}

    except PermanentError as e:
        log_attempt(task_id=task_id, channel=channel, merchant_id=merchant_id, lang=lang,
                    attempt_no=attempt_no, status="failed", provider=prov.name,
                    request_meta=req_meta, response_meta=None, error=str(e))
        return {"ok": False, "error": str(e)}

    except (TransientError, SoftTimeLimitExceeded) as e:
        log_attempt(task_id=task_id, channel=channel, merchant_id=merchant_id, lang=lang,
                    attempt_no=attempt_no, status="failed", provider=prov.name,
                    request_meta=req_meta, response_meta=None, error=str(e))

        # retry policy
        max_retries = int(getattr(settings, "NOTIFY_MAX_RETRIES", 3))
        base = int(getattr(settings, "NOTIFY_BACKOFF_BASE", 2))
        jitter = int(getattr(settings, "NOTIFY_BACKOFF_JITTER_SEC", 3))

        if self.request.retries + 1 >= max_retries:
            # final failure; no more retries
            return {"ok": False, "error": str(e)}

        countdown = (base ** self.request.retries) + random.randint(0, max(0, jitter))
        raise self.retry(exc=e, countdown=countdown)
