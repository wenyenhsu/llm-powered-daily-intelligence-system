# 本機副本同步驗證

日期：2026-11-22（America/Los_Angeles）。經使用者確認，同步目標為 `/Users/godhanko/github/llm-powered-daily-intelligence-system`。

本次將先前已完成的 embedding model 一致性修正同步到此副本。套用前 HEAD 為
`a01dc65c8a56753fd4f8c11074f964c0bff7c37e`、分支為 `cursor/insight-retrieval-top-k`，另建立 `codex/validate-embedding-model`。
來源貢獻的基準仍是 `facf02b041671491cde33cc212c6b16eee79fdac`；兩個基準的三個待修改檔案逐 byte 相同。
沒有 pull、merge、commit、push、發布 PR 或聯絡他人。

原有 `src/generate_reports.py`、`src/test_core.py`、`state/insight_index.json`、
`state/topic_index.json` 四項未提交變更完整保留。`verification/sync-initial-state.json`
與 `verification/sync-integrity.json` 記錄套用前後 SHA-256，四個檔案的內容均未改變。
本副本的索引在同步前就已修改，故不將它們宣稱為與 Git HEAD 相同。

| 本副本實際執行 | 同步前 | 同步後 |
|---|---|---|
| 檢索測試檔 | 5 passed，exit 0 | 22 passed，exit 0 |
| 完整預設測試 | 40 passed／5 failed，exit 1 | 57 passed／相同 5 failed，exit 1 |
| 核心測試（包含本人原有新增測試） | 19 passed，exit 0 | 19 passed，exit 0 |
| 同維異模型最小案例 | 錯誤接受、mock HTTP 呼叫一次，exit 1 | ValueError、零呼叫，exit 0 |

五個既有失敗仍是 `--merge`／`args.merge` 測試，前後 failed node IDs 經程式比對相同。
`git apply --check`、實際套用及 `git diff --check` 均 exit 0。
所有本次重跑紀錄為 `verification/sync-*.txt`，每份均含實際指令、工作目錄、輸出與退出狀態。

本次重用來源副本的 Python 3.11.15／pytest 8.4.2 虛擬環境：
`/Users/godhanko/Documents/ChatGPT/CSCI-566/llm-powered-daily-intelligence-system/.venv/bin/python`。`verification/sync-environment.txt` 明確確認匯入的是本目標副本的
`src/embedding_memory.py`。pytest 關閉 cache，Python 停用 bytecode 寫入；
沒有下載模型或呼叫真實 embedding 服務。於本目錄可重跑：

```sh
/Users/godhanko/Documents/ChatGPT/CSCI-566/llm-powered-daily-intelligence-system/.venv/bin/python -m pytest -p no:cacheprovider -q tests/test_insight_retrieval.py
/Users/godhanko/Documents/ChatGPT/CSCI-566/llm-powered-daily-intelligence-system/.venv/bin/python -m pytest -p no:cacheprovider -q
/Users/godhanko/Documents/ChatGPT/CSCI-566/llm-powered-daily-intelligence-system/.venv/bin/python -m pytest -p no:cacheprovider -q src/test_core.py
env OLLAMA_EMBED_MODEL=model-B /Users/godhanko/Documents/ChatGPT/CSCI-566/llm-powered-daily-intelligence-system/.venv/bin/python verification/reproduce_model_mismatch.py
```

`verification.md` 與 `report-draft.md` 中原始調查／重現數字指前一輪來源副本的工作；
本文件與 `sync-*` 檔案為此次目標副本的額外證據。來源副本的核心測試為 17 項，
本副本因使用者已有兩個額外測試而為 19 項，不應混為一次執行。
來源歷史證據與原始 checksum 清單保留；`original-delivery-SHA256SUMS` 對應同步前來源交付，
目前所有交付檔案另由更新的 `verification/SHA256SUMS` 記錄。

以上同步、測試與紀錄由 Codex 執行，並非聲稱使用者已親自驗證。
個人經驗、教材頁碼核對、課程 AI 規定及本人重跑結果仍為 [待本人補充]。
Mock 結果只支持流程與模型相容檢查，沒有宣稱真實檢索品質提升。
