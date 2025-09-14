from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from pymongo import UpdateOne
from mongo import get_collection
from transaction.helpers import aggregate_daily_both, rollup_both
from bson import ObjectId

class Command(BaseCommand):
    help = "Build/refresh TTL-backed summaries in `transaction_summary`."

    def add_arguments(self, parser):
        parser.add_argument('--mode', choices=['daily','weekly','monthly'], nargs='*')
        parser.add_argument('--merchant-id', help='Build merchant-scoped summary; omits for global')

    def handle(self, *args, **opts):
        modes = opts['mode'] or ['daily','weekly','monthly']
        merchant = opts.get('merchant_id')
        since = opts.get('since')

        tx = get_collection('transaction')
        out = get_collection('transaction_summary')

        # Ensure indexes (idempotent)
        ttl_seconds = int(getattr(settings, 'SUMMARY_TTL_SECONDS', 86400))
        out.create_index('createdAt', expireAfterSeconds=ttl_seconds, name='ttl_createdAt')
        # Uniqueness per bucket: mode + label + merchantId (merchantId missing for global docs)
        out.create_index([('mode',1), ('label_jalali',1), ('merchantId',1)], unique=True, name='u_mode_label_merchant')

        # Build match for raw scan
        match = {}
        if merchant and ObjectId.is_valid(merchant):
            merchant = ObjectId(merchant)
            match['merchantId'] = merchant
        if merchant and not ObjectId.is_valid(merchant):
            self.stdout.write(self.style.ERROR_OUTPUT(
                f"Not a valid merchant ID:{merchant}"
            ))
            return
        # Aggregate once per day, then roll up
        daily = aggregate_daily_both(tx, match)
        now = timezone.now()
        bulk = []

        for mode in modes:
            rows = rollup_both(daily, mode)  # [{'label_jalali','count','amount'}...]
            for r in rows:
                doc = {
                    'mode': mode,
                    'label_jalali': r['label_jalali'],
                    'count': int(r['count']),
                    'amount': r['amount'],
                    'createdAt': now,
                }
                filt = {'mode': mode, 'label_jalali': r['label_jalali']}
                if merchant:
                    doc['merchantId'] = merchant
                    filt['merchantId'] = merchant
                else:
                    # enforce "no merchantId field" for global rows
                    filt['merchantId'] = {'$exists': False}

                update = {'$set': doc, '$unset': {}}
                if not merchant:
                    update['$unset']['merchantId'] = ""  # guarantee it’s absent on global docs

                bulk.append(UpdateOne(filt, update, upsert=True))

        if bulk:
            out.bulk_write(bulk, ordered=False)

        self.stdout.write(self.style.SUCCESS(
            f"Upserted {len(bulk)} docs (modes={modes}, merchant={'ALL' if not merchant else merchant})"
        ))
