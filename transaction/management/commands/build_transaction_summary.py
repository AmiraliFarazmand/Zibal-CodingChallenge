from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from pymongo import UpdateOne
from pymongo.errors import OperationFailure
from mongo import get_collection
from transaction.helpers import aggregate_daily_both, rollup_both
from bson import ObjectId

TTL_INDEX_NAME = "ttl_createdAt"
UNIQ_INDEX_NAME = "u_mode_label_merchant"


class Command(BaseCommand):
    help = "Build/refresh TTL-backed summaries in `transaction_summary`."

    def add_arguments(self, parser):
        parser.add_argument('--mode', choices=['daily','weekly','monthly'], nargs='*')
        parser.add_argument('--merchant-id', help='Build merchant-scoped summary; omits for global')

    def handle(self, *args, **opts):
        modes = opts['mode'] or ['daily','weekly','monthly']
        merchant_str = opts.get('merchant_id')

        tx = get_collection('transaction')
        out = get_collection('transaction_summary')

        # Ensure indexes (idempotent)
        ensure_indexes(out)
        
        # Build match for raw scan
        match = {}
        merchant = None
        if merchant_str:
            if ObjectId.is_valid(merchant_str):
                merchant = ObjectId(merchant_str)
                match["merchantId"] = merchant
            else:
                self.stdout.write(self.style.ERROR(f"Not a valid merchant ID: {merchant_str}"))
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


def ensure_indexes(out):
    existing = {idx["name"]: idx for idx in out.list_indexes()}

    # TTL index
    ttl_seconds = int(getattr(settings, "SUMMARY_TTL_SECONDS", 86400))
    if TTL_INDEX_NAME in existing:
        current_ttl = existing[TTL_INDEX_NAME].get("expireAfterSeconds")
        if current_ttl != ttl_seconds:
            # Update TTL in place (preferred) or fall back to drop+recreate
            try:
                out.database.command(
                    "collMod",
                    out.name,
                    index={"name": TTL_INDEX_NAME, "expireAfterSeconds": ttl_seconds},
                )
            except OperationFailure:
                # Older server or mismatch: drop + recreate
                out.drop_index(TTL_INDEX_NAME)
                out.create_index(
                    "createdAt",
                    expireAfterSeconds=ttl_seconds,
                    name=TTL_INDEX_NAME,
                )
    else:
        out.create_index(
            "createdAt",
            expireAfterSeconds=ttl_seconds,
            name=TTL_INDEX_NAME,
        )

    # Uniqueness per bucket: (mode, label_jalali, merchantId?)
    if UNIQ_INDEX_NAME not in existing:
        out.create_index(
            [("mode", 1), ("label_jalali", 1), ("merchantId", 1)],
            unique=True,
            name=UNIQ_INDEX_NAME,
        )
