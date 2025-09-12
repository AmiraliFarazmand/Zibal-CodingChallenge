from django.urls import path
from .views import ResetPasswordNotifyView

urlpatterns = [
    path("reset-password/", ResetPasswordNotifyView.as_view(), name="notify-reset-password"),
]