from django.urls import path
from .views import TransactionReportView

urlpatterns = [
    path('transactions/report/', TransactionReportView.as_view(), name='transactions-report'),
]
