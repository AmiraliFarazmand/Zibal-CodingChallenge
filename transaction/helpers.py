

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from dateutil import tz
import jdatetime
from .serializers import ReportQuerySerializer
from mongo import get_collection

TZ = 'Asia/Tehran'

def to_jalali_label(g_date, mode: str):
    """
    Convert a naive/aware Python datetime.date to Jalali label.
    - daily   → "YYYY/MM/DD" (e.g., 1403/04/04)
    - weekly  → "YYYY سال W هفته"
    - monthly → "YYYY <MonthName>" (e.g., "1403 شهریور")
    """
    # Ensure date (not datetime)
    if hasattr(g_date, 'date'):
        g_date = g_date.date()

    jd = jdatetime.date.fromgregorian(date=g_date)
    if mode == 'daily':
        return f"{jd.year:04d}/{jd.month:02d}/{jd.day:02d}"
    elif mode == 'monthly':
        persian_months = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور",
                          "مهر","آبان","آذر","دی","بهمن","اسفند"]
        return f"{jd.year} {persian_months[jd.month-1]}"
    elif mode == 'weekly':
        # Week number within the Jalali year, starting at Farvardin 1 (Saturday)
        start_of_year = jdatetime.date(jd.year, 1, 1)
        # Convert to ordinal day delta
        day_delta = (jd.togregorian() - start_of_year.togregorian()).days
        week_no = day_delta // 7 + 1
        return f"{jd.year} سال {week_no} هفته"
    else:
        raise ValueError("Invalid mode")
    