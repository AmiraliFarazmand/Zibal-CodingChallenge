from django.urls import path
from .views import ResetPasswordNotifyView,ResetPasswordNotifyTelegramView

urlpatterns = [
    path("reset-password/", ResetPasswordNotifyView.as_view(), name="notify-reset-password"),
    path("reset-password/telegram/", ResetPasswordNotifyTelegramView.as_view(), name="notify-reset-password-telegram"),
]