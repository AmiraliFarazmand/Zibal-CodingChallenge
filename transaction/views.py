from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from mongo import get_collection
from .serializers import ReportQuerySerializer
from .helpers import aggregate_daily_both, rollup_both, label_to_gregorian_date

TZ = 'Asia/Tehran'



class TransactionReportView(APIView):
    def get(self, request):
        q = ReportQuerySerializer(data=request.data)
        if not q.is_valid():
            return Response(q.errors, status=status.HTTP_400_BAD_REQUEST)
        qd = q.validated_data
        metric = qd['type'] 
        mode = qd['mode']
        merchant_id = qd.get('merchantId')

        coll = get_collection('transaction')

        match = {}
        if merchant_id:
            match['merchantId'] = merchant_id

        daily = aggregate_daily_both(coll, match)
        rows = rollup_both(daily, mode)  

        data = [{'key': r['label_jalali'], 'value': r[metric]} for r in rows]
        return Response(data, status=200)
    


class TransactionReportCachedView(APIView):
    def get(self, request):
        q = ReportQuerySerializer(data=request.data)
        if not q.is_valid():
            return Response(q.errors, status=status.HTTP_400_BAD_REQUEST)
        qd = q.validated_data
        type = qd['type']  
        mode = qd['mode']
        merchant_id = qd.get('merchantId')

        coll = get_collection('transaction_summary')

        filt = {'mode': mode}
        if merchant_id:
            filt['merchantId'] = merchant_id
        else:
            # global docs omit merchantId field entirely
            filt['merchantId'] = {'$exists': False}

        # If collection doesn't exist yet, this just returns an empty cursor—safe.
        docs = list(coll.find(filt, {'_id': 0, 'label_jalali': 1, type: 1}))

        # Sort by true chronology via reconstructed Gregorian start
        docs.sort(key=lambda d: label_to_gregorian_date(mode, d['label_jalali']))

        data = [{'key': d['label_jalali'], 'value': d.get(type, 0)} for d in docs]
        return Response(data, status=200)