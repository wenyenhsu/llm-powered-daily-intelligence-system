# 1. Project and need

本次貢獻對象為 [LLM-Powered Daily Intelligence System](https://github.com/wenyenhsu/llm-powered-daily-intelligence-system)，
是一個將資訊經 LLM 分析後累積為知識節點，並使用 embedding 進行語意檢索的開源專案。
使用者表示此專案由本人開發；個人實際使用背景與選題動機：**[待本人補充]**。

既有 insight retrieval 會把查詢轉為向量，與 `state/insight_index.json` 中的 insight 向量計算 cosine similarity，
依門檻與 top-K 選出內容並放入分析提示詞。索引已有 `model` 欄位，但基準版本
`facf02b041671491cde33cc212c6b16eee79fdac` 的 `retrieve_top_insights()` 沒有核對模型。
若改用另一個 embedding 模型查詢，即使向量長度相同，程式仍會直接比較。

2026-11-22 的公開 GitHub API 調查顯示 issues 為 open 0／closed 0，PR 為 open 0／closed 1。
唯一的 [PR #1](https://github.com/wenyenhsu/llm-powered-daily-intelligence-system/pull/1) 已實作 top-K retrieval，
其合併 SHA 即本次基準。檢閱其修改與現行程式後，未發現模型一致性防護；因此本次新增工作與既有 top-K 功能可清楚區分。
調查範圍與原始 API 回應保存在 `verification.md` 與 `verification/github-search.json`。

# 2. New work

本機分支為 `codex/validate-embedding-model`。本次在 `src/embedding_memory.py` 的檢索流程加入模型驗證，
排序、分數門檻與 top-K 演算法沿用既有實作。

對非空查詢與非空索引，程式先讀取查詢模型，再與索引 `model` 精確比較。
兩者不同即拋出 `ValueError`，訊息列出索引模型、查詢模型，並提示使用者先手動執行 `--reindex`。
此時不呼叫 embedding backend，也不進行 cosine 比較。對缺少、空白或非字串模型 metadata 的舊索引，
採拒絕檢索政策，因為無法由向量維度推回其模型身分；直接補上目前模型名稱會造成未經證實的相容性假設。

通過檢查後，呼叫明確寫為 `embed_text(..., model=query_model)`。
這避免只核對設定值，實際上卻由 Python 在函式定義時綁定的預設參數選到另一個模型。
原有空索引或空白查詢回傳 `[]` 的行為保留。修正未加入自動重建或寫入索引的錯誤處理，
本次執行也沒有改寫真正的索引資料。

回歸測試補入合理模型 metadata，保留原有斷言，再新增同模型排序／top-K、同維異模型拒絕、
backend 零呼叫、未知 metadata、實際 HTTP payload 模型及空輸入案例。README 同步說明相容政策與手動復原方式。

# 3. Verification

正式前後驗證使用 macOS 15.6.1 arm64、Python 3.11.15、pytest 8.4.2 與獨立 `.venv`。
初次 Python 3.9 嘗試因專案既有 `dataclass(slots=True)` 造成 collection errors，已另存紀錄並更換環境，
沒有將其算成本次修正造成的失敗。

最小案例將索引模型設為 `model-A`、查詢模型設為 `model-B`，兩邊向量均為 `[1.0, 0.0]`。
腳本直接呼叫專案函式，使用臨時 JSON 索引並 mock HTTP 回應，完全沒有付費 API 呼叫或模型下載。
原版實際回傳分數 `1.0` 並呼叫 backend 一次，案例以 exit 1 表示未達拒絕要求；
修正後列出兩個模型與 `--reindex` 的例外，backend 呼叫為零，案例 exit 0。
兩次的臨時索引 bytes 都沒有變動。

| 實際檢查 | 修改前 | 修改後 |
|---|---|---|
| 檢索測試檔 | 5 passed | 22 passed |
| 新測試對尚未修改的 production code | 8 failed／14 passed | 22 passed |
| 完整預設測試 | 40 passed／5 failed | 57 passed／相同 5 failed |
| 額外核心測試 `src/test_core.py` | 17 passed | 17 passed |

完整測試仍有 5 項既有失敗，均與測試預期的 `--merge`／`args.merge` 不存在有關。
前後 failed node IDs 經程式比對完全相同；沒有 skip 或弱化這些測試。
`pip check`、`git diff --check`、tracked state 未變更檢查均 exit 0。
所有命令、輸出與退出狀態均保存於 `verification/`，重跑步驟列於 `verification.md`。

這些 mock 測試證明控制流程與模型相容性檢查符合設計，沒有測量真實模型的檢索品質、效能或準確率，
因此不宣稱品質或速度提升。目前成果僅在本機，尚未 commit、push、發布 PR 或取得 maintainer 回覆。

本機副本同步補充：成果其後同步到使用者指定的 `/Users/godhanko/github/llm-powered-daily-intelligence-system`，保留原有四項未提交變更。該副本檢索測試為 22 passed、全套為 57 passed／相同 5 failed；核心測試含使用者原有兩項新增案例，前後皆為 19 passed。此次紀錄另存 `sync-verification.md` 與 `verification/sync-*`，與上述原始副本 17 項核心測試結果區分。

# 4. Explanation

依本次委託提供的課程摘要，期中複習第 232–233 頁強調：特徵維度相同並不足以保證相容，
特徵的順序與定義也必須一致。將此原則延伸到 embedding retrieval，向量長度只說明座標數量，
無法保證座標的意義與整體表示空間一致。不同模型即使輸出相同維度，也不能假設它們的向量能直接用 cosine similarity 比較。

例如兩個模型各自輸出的 `[1, 0]` 在數值上可算出 cosine similarity 1，但如果其表示空間不同，
這個數字不能直接作為跨模型語意相似的可靠依據。因此本次選擇在比較之前驗證模型身分，
把課程中「特徵定義需一致」的原則轉成明確的檢索前置條件。這是原則的應用，**不是專案實作了 GNN**。
模型名稱檢查也有界線：它信任索引 metadata，尚不能偵測相同名稱背後的權重版本或前處理變動。

**AI 協助揭露：**本輪 Codex 協助讀碼、搜尋規範及 issues／PR、建立環境、設計與執行 mock 重現、
撰寫修正及回歸測試、執行檢查、保存證據，以及撰寫此草稿。這些操作由 AI 代理執行，
不能表述為本人已親自完成。個人使用經驗未由 AI 補寫。

提交課程報告前，本人應親自完成：

- 檢閱程式 diff、未知 metadata 政策及前後原始紀錄，並重跑關鍵案例與測試。
- 核對教材第 232–233 頁的原文、頁碼、正式引用方式及課程 AI 使用規定；本輪未獨立讀取教材原檔。
- 補上個人背景／動機、教材完整名稱與本人驗證結果：**[待本人補充]**。
- 整理成 2–4 頁 PDF，確認版面與 AI 揭露符合課程要求。本輪交付 Markdown 草稿，未製作或宣稱已完成 PDF。
