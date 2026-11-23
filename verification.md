# Embedding model consistency — verification

## 範圍與完成狀態

日期：2026-11-22（America/Los_Angeles）。本次由 Codex 在本機執行調查、重現、修改及測試。
修正限於 `retrieve_top_insights()` 的模型一致性，並補上回歸測試及 README 說明。
沒有重新實作 top-K、沒有呼叫真實 embedding／付費 API、沒有下載模型，亦沒有執行真正的 `--reindex`。
沒有 push、建立 PR、留言或聯絡他人；修改保留於工作目錄，尚未 commit。

## 基準、工作區與環境

| 項目 | 實際紀錄 |
|---|---|
| 專案 | [wenyenhsu/llm-powered-daily-intelligence-system](https://github.com/wenyenhsu/llm-powered-daily-intelligence-system) |
| 本機位置 | `/Users/godhanko/Documents/ChatGPT/CSCI-566/llm-powered-daily-intelligence-system` |
| 基準 SHA | `facf02b041671491cde33cc212c6b16eee79fdac` |
| 分支 | `codex/validate-embedding-model`，以 `git switch -c codex/validate-embedding-model` 建立 |
| 作業系統 | macOS 15.6.1，arm64 |
| 正式驗證 Python | CPython 3.11.15，既有 `/Users/godhanko/.local/bin/python3.11` 建立 `.venv` |
| 測試工具 | pytest 8.4.2；pip 24.0；`pytest.ini` 設定 `pythonpath = .`、`testpaths = tests` |
| 依賴 | 安裝專案 `requirements` 加上固定版本 pytest；完整解析版本見 `verification/requirements-lock.txt` |

第一次檢查時，課程工作區沒有此專案，也沒有 `embedding_memory.py`。外層 Git 是尚無 commit 的
`master`，已有未追蹤的 `finder-copy-backups/`、`output/`、`restored-starter-backups/`、`tmp/`；
這些既有內容未改動。另在專案名稱目錄 clone，clone 後第一次 `git status --short --branch`
只輸出 `## main...origin/main`，沒有未提交變更，因此沒有覆蓋既有專案工作。
最初沙箱內 clone 因 DNS 失敗（exit 128），獲准使用網路後 clone 成功（exit 0）。

系統預設 `/usr/bin/python3` 是 3.9.6。第一次建置環境後，原版全套測試因既有
`src/generate_reports.py` 使用 `@dataclass(slots=True)` 而出現 4 個 collection errors（exit 2）。
同環境的獨立模型不一致案例仍可重現。這些原始紀錄完整保留在
`verification/initial-py39-*.txt`，之後以 Python 3.11 重建自己建立的 `.venv`，沒有修改專案來遷就 3.9。

環境／安裝證據：`verification/environment.txt`、`verification/setup.txt`、
`verification/requirements-lock.txt`。第一次與第二次環境解析出的間接依賴可能不同，兩者分別記錄，
前後正式比較都使用同一個 Python 3.11 環境。

## 規範與重複工作調查

已讀取基準的完整 `README.md`、`LICENSE`、`requirements`、`pytest.ini`，以及相關程式與測試。

- 儲存庫所有 tracked files 與包含隱藏檔案的檔案清單中，都沒有 `CONTRIBUTING*`、`AGENTS.md`、
  `.github/` 或專門的 AI／生成式 AI 貢獻政策。各層祖先目錄的 `AGENTS.md` 也不存在。
- GitHub 預設社群規範來源 `wenyenhsu/.github` 的公開 contents API 回傳 404；只能確認沒有讀到可公開取得的規範，
  不推論私人文件不存在。若課程另有 AI 政策，須由本人核對。
- README 要求以 `pytest` 跑測試；沒有找到 CI workflow、lint、formatter 或 type checker 的專案強制檢查。
  README 寫的 `requirements.txt` 實際檔名是 `requirements`，安裝時使用後者；未順便修正無關文件問題。

GitHub 查詢於 **2026-11-22 18:36:28 -08:00** 完成。瀏覽工具開啟篩選頁失敗（Cache miss），
因此改用公開 REST API 的即時資料，不以網頁快取的數字作為唯一證據。
查詢由 `verification/collect_github.py` 執行，只送出 GET，會追蹤所有 `rel="next"` 分頁。

| 查詢／檢閱 | 結果 |
|---|---|
| [issues，state=all](https://api.github.com/repos/wenyenhsu/llm-powered-daily-intelligence-system/issues?state=all&per_page=100)，排除 PR | open 0、closed 0 |
| [pulls，state=all](https://api.github.com/repos/wenyenhsu/llm-powered-daily-intelligence-system/pulls?state=all&per_page=100) | open 0、closed 1 |
| 所有 issue／PR 標題與內文搜尋 | 正規式 `embed\|model\|metadata\|retriev\|reindex\|compatib`（實際以 regex alternation 執行）只找到 PR #1 |
| [PR #1](https://github.com/wenyenhsu/llm-powered-daily-intelligence-system/pull/1) 的 detail 與所有 changed files | 已 merged；merge SHA 與本次基準相同；新增 top-K、提示詞注入與測試，未檢查模型 |
| main commit API、clone 的 history／remote branches | main 仍為基準 SHA；相關 history 只有既有 retrieval／embedding 工作，未發現同項修正 |

檢閱過 `src/embedding_memory.py`、`src/config.py`、`src/run_pipeline.py`、
`tests/test_insight_retrieval.py`、其餘 `tests/` 及 `src/test_core.py`；
以 `rg` 查詢 `retrieve_top_insights`、`embed_text`、`OLLAMA_EMBED_MODEL` 及測試／政策關鍵字。
原版 index builder 會寫入 `model`，但 retrieval 直接呼叫 `embed_text(query[:4000])` 並開始計分。
`embed_text(text, model=OLLAMA_EMBED_MODEL)` 的預設值在函式定義時綁定，故只比對設定而省略實際呼叫的模型參數並不足夠。

原始證據：`verification/github-search.json` 保留每個 API URL、狀態與完整回應；
`verification/github-search.txt` 保留命令、摘要與 exit 0；`verification/investigation.txt` 保留本機搜尋。
結論限於此次查詢時間與可存取的資料，不代表未來不會出現類似貢獻，也沒有取得或聲稱任何 maintainer 回覆。

## 原版最小重現

正式案例腳本是 `verification/reproduce_model_mismatch.py`。它匯入並呼叫專案真正的
`src.embedding_memory.retrieve_top_insights()`，保留真正的 `load_index()`、`embed_text()` 及 cosine 計分。
僅將索引路徑指到臨時目錄，並 mock `requests.post`；沒有複製檢索實作。

輸入為索引模型 `model-A`，索引向量 `[1.0, 0.0]`，查詢文字 `query`。
以程序啟動前的環境變數設定查詢模型 `model-B`，mock HTTP 回傳同為二維的 `[1.0, 0.0]`。
這保證原版真正要送給 embedding backend 的模型也是 `model-B`，而非僅修改一個未使用的設定。

以下命令曾在 **尚未修改任何 production source 的基準版本**實際執行：

```sh
python3 verification/run_and_record.py verification/before-mismatch.txt \
  env OLLAMA_EMBED_MODEL=model-B .venv/bin/python verification/reproduce_model_mismatch.py
```

`run_and_record.py` 保存命令、工作目錄、洛杉磯時間、合併 stdout／stderr 及子程序真實退出碼，
並以該退出碼結束。`verification/baseline-source-unchanged.txt` 的 `git diff --exit-code -- src README.md`
為 exit 0，證明加入回歸測試時 production source 仍與基準一致。

| 觀察 | 期望 | 原版實際 | 修正後實際 |
|---|---|---|---|
| 模型驗證 | `ValueError`，列出兩模型與 `--reindex` | 無例外 | 符合 |
| 查詢 backend 呼叫 | 0 次 | 1 次，payload model=`model-B` | 0 次 |
| 檢索結果 | 不比較、不回傳匹配 | `same-dimension`，score=`1.0` | 無匹配結果，拋出例外 |
| 臨時索引原始 bytes | 不變 | 不變 | 不變 |
| 腳本退出碼 | 0 代表要求成立 | **1** | **0** |

原版紀錄見 `verification/before-mismatch.txt`，修正後相同輸入見 `verification/after-mismatch.txt`。
修正後例外的實際文字：

```text
Insight index embedding model 'model-A' does not match query embedding model 'model-B'. Rebuild with --reindex before retrieval.
```

## 修正與相容政策

1. 保留原有載入索引及提前回傳的順序。載入的 `items` 為空／缺少／None，或查詢經 strip 後為空，依舊回傳 `[]`。
2. 對真正進入比對的非空案例，擷取一次模組設定 `OLLAMA_EMBED_MODEL` 作為 `query_model`。
3. 非空索引若沒有 `model`，或其值為 None、空字串、全空白、非字串，拋出清楚的 `ValueError`，提示 `--reindex`。
   理由是模型身分未知時無法證明表示空間相容；自行補上目前模型名稱可能替舊向量標錯身分。
4. `index.model` 與 `query_model` 採精確字串比較。不同就列出兩個值並提示 `--reindex`，在 embedding 及 cosine 比較前停止。
5. 通過後明確呼叫 `embed_text(query[:4000], model=query_model)`，使檢查值與實際 backend payload 一致，避開預設參數綁定陷阱。

沒有變更排序、分數門檻、top-K、模型清單、索引格式或資料。新增錯誤路徑沒有 rebuild／write。
既有 `load_index()` 在索引檔不存在時會建索引的行為未修改；本次重現使用已存在的臨時索引，
未觸發該分支，也未觸碰使用者真正索引。README 的修復方式是先獨立執行 reindex，再重試 retrieval；
本次沒有代使用者執行。

## 測試與實際結果

先加入回歸測試，再修改 production code。最初測試草稿有一個未設定回傳值的 cosine mock，
導致額外 `TypeError`；原始輸出保存在 `verification/red-regressions-initial.txt`。
修正測試 mock 為數值回傳後，在仍未修改的 production code 上重跑，得到以下正式 red 結果。

| 檢查 | 修改前 | 修改後 | 紀錄檔（`verification/` 下） |
|---|---|---|---|
| 既有檢索檔 | 5 passed，exit 0 | 含新測試共 22 passed，exit 0 | `baseline-targeted.txt`、`after-targeted.txt` |
| 新回歸測試對原版（含既有測試加強） | 8 failed／14 passed，exit 1 | 同上 22 passed | `red-regressions.txt` |
| README 要求的完整 `pytest`（由 `python -m pytest` 執行） | 40 passed／5 failed，exit 1 | 57 passed／同 5 failed，exit 1 | `baseline-suite.txt`、`after-suite.txt` |
| 額外 `src/test_core.py`（不在預設 testpaths） | 17 passed，exit 0 | 17 passed，exit 0 | `baseline-core.txt`、`after-core.txt` |
| 完整測試的 failed node IDs 比較 | — | 相同 5 項，assert 通過，exit 0 | `failure-comparison.txt` |
| `pip check` | — | No broken requirements found，exit 0 | `pip-check.txt` |
| `git diff --check` | — | exit 0 | `diff-check.txt` |
| `git diff --exit-code -- state` | — | exit 0，tracked 索引未更動 | `data-unchanged.txt` |

新增加 17 個參數化測試案例：5 個排序／top-K／門檻組合、1 個同維異模型拒絕（並斷言 embed 與 cosine 均未呼叫）、
5 個缺少／無效 metadata、1 個保留真實 `embed_text()` 並驗證 HTTP payload 模型的預設參數陷阱、
5 個空輸入／索引案例。既有斷言全部保留，原排序 fixture 補上合理 metadata，另加明確模型參數的斷言。

全套既有失敗均來自 tests 預期不存在的 `--merge`／`args.merge`，沒有修掉、skip、xfail 或弱化：

- `tests/test_commands.py::test_full_pipeline_quick_start`
- `tests/test_commands.py::test_merge_apply`
- `tests/test_run_pipeline_args.py::test_default_args`
- `tests/test_run_pipeline_args.py::test_flag_args[argv5-merge]`
- `tests/test_run_pipeline_args.py::test_combined_args`

`pip check` 的 pip cache 不可寫警告不影響其 exit 0；Python 3.9 的 LibreSSL 警告與 collection errors
另存初始環境檔案，不混入 Python 3.11 的正式前後比較。

## 在目前修正上重跑

在專案根目錄使用 Python 3.11。現有 `.venv` 已可執行；若重建環境，使用：

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r verification/requirements-lock.txt
```

核心驗證命令（目前版本的預期退出碼依序為 0、0、1、0、0、0）：

```sh
env OLLAMA_EMBED_MODEL=model-B .venv/bin/python verification/reproduce_model_mismatch.py
.venv/bin/python -m pytest -q tests/test_insight_retrieval.py
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q src/test_core.py
.venv/bin/python -m pip check
git diff --check
```

原版重跑可使用以下**獨立目錄**範本，避免 checkout 蓋掉目前修改。這是供日後使用的範本；
本次原版數字來自修改前的實際執行，不是假稱已執行此範本：

```sh
project_dir="$PWD"
baseline_dir="$(mktemp -d)"
git archive facf02b041671491cde33cc212c6b16eee79fdac | tar -x -C "$baseline_dir"
mkdir "$baseline_dir/verification"
cp verification/reproduce_model_mismatch.py "$baseline_dir/verification/"
cd "$baseline_dir"
env OLLAMA_EMBED_MODEL=model-B "$project_dir/.venv/bin/python" verification/reproduce_model_mismatch.py
# 預期 exit 1：會回傳 score 1.0，HTTP mock 被呼叫一次。
```

## 限制、AI 揭露與本人待核對

- Mock 測試只能證明控制流程、相容性檢查、排序規則及模型傳遞，不能證明真實模型的檢索品質、準確率或效能提升。
- 只驗證索引宣告的模型名稱與查詢使用名稱相等；相同名稱底下的模型內容／tag 變動、錯誤 metadata、
  前處理差異等未納入指紋驗證，也不把模型字串相同視為完整來源證明。
- 設定沿用現有模組載入方式，沒有新增 `.env` 熱更新、模型別名解析或重構其他 embedding 消費者
  （例如 `match_insight`、topic memory、merging）。
- 本輪 AI 協助包含：讀碼與規範／GitHub 查詢、環境建立、mock 重現、修正與測試撰寫、實際執行命令、
  保存紀錄與本文件／報告草稿。上述檢查由 Codex 執行，不能改寫成使用者已親自操作。
- 本人應親自核對 diff、例外政策、測試紀錄與重跑結果，再決定是否採納；真實模型人工驗證如需進行，須另記資料與結果。
- 本人應核對期中複習原檔第 232–233 頁、課程 AI 使用／揭露規定與報告頁數。
  本輪課程說明根據使用者提供的原則，未獨立讀取該教材。
- 個人使用情境、實際遇到問題的時間與經驗、課程教材完整名稱／引用格式、本人獨立驗證日期與結果：**[待本人補充]**。

`verification/focused-fix.patch` 是 production code、README 與回歸測試的可檢閱 patch；
`verification/SHA256SUMS` 記錄交付時文件、程式與證據檔案的 SHA-256（不包含其自身）。
SHA-256 僅供後續核對檔案是否變更，並非外部公證或獨立第三方驗證。

## 本機既有副本同步補充

本文件以上紀錄為原始工作區的歷史驗證。之後已同步到使用者指定的 `/Users/godhanko/github/llm-powered-daily-intelligence-system`，保留原有四項未提交變更；本副本的基準、實際重跑結果及檔案完整性證據詳見 [sync-verification.md](sync-verification.md)。
