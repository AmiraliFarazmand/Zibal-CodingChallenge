from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

from .serializers import ResetPasswordRequestSerializer
from .tasks import send_reset_password_task

class ResetPasswordNotifyView(APIView):
    """
    POST /api/v1/notify/reset-password
    body: { merchantId, channel: 'sms'|'email'|'telegram', lang?: 'fa'|'en' }
    returns: { task_id }
    """
    def post(self, request):
        s = ResetPasswordRequestSerializer(data=request.data)
        if not s.is_valid():
            return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)
        data = s.validated_data
        merchant_id = data["merchantId"]
        channel = data["channel"]
        lang = data.get("lang") or getattr(settings, "NOTIFY_DEFAULT_LANG", "fa")

        # enqueue and return Celery task id (tracking is via result backend or logs)
        async_result = send_reset_password_task.delay(merchant_id=merchant_id, channel=channel, lang=lang)
        return Response({"task_id": async_result.id, "status": "queued"}, status=status.HTTP_201_CREATED)
