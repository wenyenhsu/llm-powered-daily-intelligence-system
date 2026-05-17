#!/bin/bash

DATE=$(date +%Y-%m-%d)
FILE="daily/$DATE.md"

if [ ! -f "$FILE" ]; then
cat <<EOF > "$FILE"
# $DATE

## 📰 News Summary
-

## 🧠 Key Insights
-

## 📊 Market Impact
-

## 💡 Thoughts
-
EOF
fi