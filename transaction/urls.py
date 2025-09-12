from django.urls import path
from .views import TransactionReportView, TransactionReportCachedView

urlpatterns = [
    path('transactions/report/', TransactionReportView.as_view(), name='transactions-report'),
    path('transactions/report/cached/', TransactionReportCachedView.as_view(), name='transactions-report-cached'),
]
