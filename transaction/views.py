from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import jdatetime
from .serializers import ReportQuerySerializer
from .helpers import to_jalali_label
from mongo import get_collection

TZ = 'Asia/Tehran'


class TransactionReportView(APIView):
    def get(self, request):
        q = ReportQuerySerializer(data=request.data)
        if not q.is_valid():
            return Response(q.errors, status=status.HTTP_400_BAD_REQUEST)

        qd = q.validated_data
        agg_type = qd['type']
        mode = qd['mode']
        merchant_id = qd.get('merchantId')

        coll = get_collection('transaction')

        # Build match
        match = {}
        if merchant_id:
            match['merchantId'] = merchant_id

        # Ensure `createdAt` is date. If stored as string/number, cast.
        # Works on MongoDB 4.2+: $toDate exists.
        add_fields = {
            'createdAtDate': { '$toDate': '$createdAt' }
        }

        # Group by day first (Gregorian, Tehran timezone), then roll-up in Python
        group_stage = {
            '_id': {
                # string date "YYYY-MM-DD" in Tehran time
                'day': {
                    '$dateToString': {
                        'format': '%Y-%m-%d',
                        'date': '$createdAtDate',
                        'timezone': TZ
                    }
                }
            },
            'value': {'$sum': 1} if agg_type == 'count' else {'$sum': '$amount'}
        }

        pipeline = [
            {'$match': match} if match else {'$match': {}},
            {'$addFields': add_fields},
            {'$group': group_stage},

            {'$sort': {'_id.day': 1}},
        ]

        # Allow disk use for large sets
        cursor = coll.aggregate(pipeline, allowDiskUse=True)

        # Convert to Jalali and roll-up depending on mode
        from datetime import datetime

        daily = []
        for doc in cursor:
            day_str = doc['_id']['day']  # "YYYY-MM-DD"
            # parse
            g_date = datetime.strptime(day_str, '%Y-%m-%d').date()
            daily.append((g_date, doc['value']))

        if mode == 'daily':
            out = [
                {'key': to_jalali_label(d, 'daily'), 'value': v}
                for d, v in daily
            ]
        elif mode == 'weekly':
            buckets = {}
            for d, v in daily:
                key = to_jalali_label(d, 'weekly')
                buckets[key] = buckets.get(key, 0) + v
            out = [{'key': k, 'value': buckets[k]} for k in sorted(buckets.keys(), key=lambda s: (int(s.split()[0]), int(s.split()[2])))]
        elif mode == 'monthly':
            buckets = {}
            # normalize to first-of-month for stable ordering
            for d, v in daily:
                jd = jdatetime.date.fromgregorian(date=d)
                k = to_jalali_label(d, 'monthly')
                buckets[k] = buckets.get(k, 0) + v
            # sort by (year, month)
            def sort_key(label: str):
                parts = label.split()
                year = int(parts[0])
                month_name = parts[1]
                mlist = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور",
                         "مهر","آبان","آذر","دی","بهمن","اسفند"]
                return (year, mlist.index(month_name))
            out = [{'key': k, 'value': buckets[k]} for k in sorted(buckets.keys(), key=sort_key)]
        else:
            return Response({'detail': 'Invalid mode'}, status=400)

        return Response(out, status=200)