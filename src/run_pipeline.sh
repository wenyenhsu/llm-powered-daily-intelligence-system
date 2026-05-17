#!/bin/bash

echo "Fetching news..."
python3 scripts/fetch_news.py

echo "Creating daily note..."
bash scripts/create_daily.sh

echo "Done."