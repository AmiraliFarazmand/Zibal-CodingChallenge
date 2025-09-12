import random
from dataclasses import dataclass

class TransientError(Exception): pass
class PermanentError(Exception): pass

@dataclass
class SMSProvider:
    name: str = "local_sms"
    fail_rate: float = 0.1
    def send(self, *, text: str, phone: str):
        if not phone or not phone.startswith("+"):
            raise PermanentError("invalid phone")
        if random.random() < self.fail_rate:  # simulate flaky network
            raise TransientError("SMS gateway timeout")
        return {"provider_id": f"sms-{random.randint(100000, 999999)}"}

@dataclass
class EmailProvider:
    name: str = "local_email"
    fail_rate: float = 0.1
    def send(self, *, subject: str, text: str, html: str, email: str):
        if not email or "@" not in email:
            raise PermanentError("invalid email")
        if random.random() < self.fail_rate:
            raise TransientError("SMTP temp fail")
        return {"provider_id": f"mail-{random.randint(100000, 999999)}"}

@dataclass
class TelegramProvider:
    name: str = "local_telegram"
    fail_rate: float = 0.1
    def send(self, *, text: str, chat_id: int):
        if not isinstance(chat_id, int):
            raise PermanentError("invalid chat_id")
        if random.random() < self.fail_rate:
            raise TransientError("Telegram 5xx")
        return {"provider_id": f"tg-{random.randint(100000, 999999)}"}
