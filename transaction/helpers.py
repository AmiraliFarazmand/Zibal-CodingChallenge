from datetime import datetime, timedelta, date as _date
import jdatetime

TZ = 'Asia/Tehran'
PERSIAN_MONTHS = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور",
                  "مهر","آبان","آذر","دی","بهمن","اسفند"]


def jalali_label(g_date: _date, mode: str) -> str:
    """Format a Gregorian date into a Jalali label per mode."""
    if hasattr(g_date, 'date'):
        g_date = g_date.date()
    jd = jdatetime.date.fromgregorian(date=g_date)
    if mode == 'daily':
        return f"{jd.year:04d}/{jd.month:02d}/{jd.day:02d}"
    if mode == 'monthly':
        return f"{jd.year} {PERSIAN_MONTHS[jd.month-1]}"
    if mode == 'weekly':
        week_no = jd.weeknumber()
        return f"{jd.year} سال {week_no} هفته"
    raise ValueError("invalid mode")


def label_to_gregorian_date(mode: str, label: str) -> _date:
    """Inverse of jalali_label function: map a label back to Gregorian start date for correct ordering."""
    if mode == 'daily':
        y, m, d = map(int, label.split('/'))
        return jdatetime.date(y, m, d).togregorian()
    if mode == 'monthly':
        y_str, mname = label.split()
        y = int(y_str)
        idx = PERSIAN_MONTHS.index(mname) + 1
        return jdatetime.date(y, idx, 1).togregorian()
    if mode == 'weekly':
        parts = label.split()
        y, w = int(parts[0]), int(parts[2])
        start = jdatetime.date(y, 1, 1).togregorian()
        return start + timedelta(days=(w-1)*7)
    raise ValueError("invalid mode")



def aggregate_daily_both(coll, match: dict):
    """
    Aggregate once per day (Asia/Tehran) and compute both metrics:
    returns list of tuples: (gregorian_date, count, amount).
    """
    pipeline = [
        {'$match': match or {}},
        {'$addFields': {'_createdAtDate': {'$toDate': '$createdAt'}}},
        {'$group': {
            '_id': {'day': {'$dateToString': {
                'format': '%Y-%m-%d', 'date': '$_createdAtDate', 'timezone': TZ
            }}},
            'count': {'$sum': 1},
            'amount': {'$sum': '$amount'}
        }},
        {'$sort': {'_id.day': 1}},
    ]
    cur = coll.aggregate(pipeline, allowDiskUse=True)
    out = []
    for d in cur:
        g = datetime.strptime(d['_id']['day'], '%Y-%m-%d').date()
        out.append((g, int(d['count']), d['amount']))
    return out


def rollup_both(daily_rows, mode: str):
    """
    Roll up (gregorian_date, count, amount) daily rows to the requested mode.
    Returns list of {'label_jalali', 'count', 'amount'} in chronological order.
    """
    if mode == 'daily':
        return [
            {'label_jalali': jalali_label(g, 'daily'), 'count': c, 'amount': a}
            for g, c, a in daily_rows
        ]
    # weekly/monthly: bucket in Python using the same Jalali logic
    buckets = {}
    for g, c, a in daily_rows:
        label = jalali_label(g, mode)
        if label not in buckets:
            buckets[label] = {'count': 0, 'amount': 0}
        buckets[label]['count'] += c
        buckets[label]['amount'] += a

    ordered = sorted(buckets.items(), key=lambda kv: label_to_gregorian_date(mode, kv[0]))
    return [{'label_jalali': lbl, **vals} for lbl, vals in ordered]
    