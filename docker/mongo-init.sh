#!/usr/bin/env bash
set -euo pipefail

echo ">> Listing /docker-entrypoint-initdb.d:"
ls -l /docker-entrypoint-initdb.d || true
echo ">> file(1) says:"
file /docker-entrypoint-initdb.d/transaction.agz || true

echo ">> Running initial mongorestore from /docker-entrypoint-initdb.d/transaction.agz"
mongorestore \
  --archive=/docker-entrypoint-initdb.d/transaction.agz \
  --gzip \
  --nsInclude='zibal_db.transaction' \
  --drop
echo ">> Initial restore complete."