# Usher Cilia Candidate Gene Discovery Pipeline

> **[English version (README.en.md)](README.en.md)**

一套可重現的生物資訊分析管線，用於系統性篩選與 Usher 症候群及纖毛病變（ciliopathies）相關的候選基因。

本管線對人類約 22,600 個蛋白質編碼基因，透過六個獨立的證據層面進行評分與排序，最終產出分層候選基因清單，供後續實驗驗證參考。

---

## 目錄

- [研究背景](#研究背景)
- [管線總覽](#管線總覽)
- [安裝與環境設定](#安裝與環境設定)
- [執行管線](#執行管線)
- [六大證據層面詳解](#六大證據層面詳解)
  - [1. gnomAD 約束性分析](#1-gnomad-約束性分析)
  - [2. 基因功能註釋](#2-基因功能註釋)
  - [3. 組織表達特異性](#3-組織表達特異性)
  - [4. 亞細胞定位](#4-亞細胞定位)
  - [5. 動物模型表型](#5-動物模型表型)
  - [6. 文獻探勘](#6-文獻探勘)
- [綜合評分與分層](#綜合評分與分層)
- [驗證機制](#驗證機制)
- [產出檔案說明](#產出檔案說明)
- [設定檔調整](#設定檔調整)
- [已知限制](#已知限制)
- [引用資料庫](#引用資料庫)

---

## 研究背景

**Usher 症候群**是最常見的遺傳性聾盲症候群，患者同時出現感音神經性聽力損失與視網膜色素變性。目前已知的致病基因（如 MYO7A、USH2A、CDH23 等）約 10 個，但臨床上仍有部分患者無法找到已知基因的致病變異，暗示可能存在尚未被發現的致病或修飾基因。

Usher 蛋白在纖毛（cilia）與纖毛相關結構中扮演關鍵角色，特別是視網膜光受器細胞的連接纖毛（connecting cilium）及內耳毛細胞的靜纖毛（stereocilia）。因此，本管線以**纖毛生物學**為核心，整合多面向的基因體與功能體學資料，系統性地搜尋可能被忽略的候選基因。

### 核心設計理念

- **缺失資料 ≠ 零分**：若某基因在特定證據層無資料（NULL），不會被扣分，僅以有資料的層面計算加權平均。這避免了對研究不足基因的系統性懲罰。
- **多面向正交驗證**：六個證據層面分別從不同角度衡量基因與纖毛/Usher 的關聯性，降低單一資料來源偏差的影響。
- **可重現性**：所有資料版本、參數設定、分析步驟均有完整記錄。

---

## 管線總覽

```
┌─────────────────────────────────────────────────────┐
│  Step 1: 建立基因宇宙 (Gene Universe)                  │
│  透過 mygene API 取得 ~22,600 個人類蛋白質編碼基因          │
└────────────────────────┬────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────┐
│  Step 2: 六大證據層面 (並行可獨立執行)                     │
│                                                     │
│  ┌───────────┐ ┌───────────┐ ┌────────────────┐    │
│  │ gnomAD    │ │ 功能註釋   │ │ 組織表達特異性   │    │
│  │ 約束性    │ │           │ │                │    │
│  └───────────┘ └───────────┘ └────────────────┘    │
│  ┌───────────┐ ┌───────────┐ ┌────────────────┐    │
│  │ 亞細胞定位 │ │ 動物模型   │ │ 文獻探勘       │    │
│  │           │ │ 表型      │ │                │    │
│  └───────────┘ └───────────┘ └────────────────┘    │
└────────────────────────┬────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────┐
│  Step 3: 綜合加權評分 + 信心分層                         │
│  NULL-aware weighted average → HIGH/MEDIUM/LOW       │
└────────────────────────┬────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────┐
│  Step 4: 驗證 + 報告產出                                │
│  已知 Usher/cilia 基因排名驗證 → TSV + Parquet + 圖表   │
└─────────────────────────────────────────────────────┘
```

---

## 安裝與環境設定

### 系統需求

- Python 3.11 以上
- 約 5 GB 磁碟空間（用於快取下載的資料庫檔案）
- 網路連線（首次執行需下載外部資料）

### 安裝步驟

打開終端機（Terminal），進入專案資料夾後執行：

```bash
# 1. 建立虛擬環境（建議）
python -m venv .venv
source .venv/bin/activate    # macOS / Linux
# .venv\Scripts\activate     # Windows

# 2. 安裝管線
pip install -e ".[dev]"
```

安裝完成後，可以用以下指令確認是否成功：

```bash
usher-pipeline info
```

如果看到版本號與設定摘要，表示安裝成功。

### NCBI API Key（文獻探勘層需要）

文獻探勘層使用 NCBI PubMed E-utilities API。此 API 需要提供電子郵件，並建議申請 API Key 以提高查詢速度（3 次/秒 → 10 次/秒）。

申請方式：前往 https://www.ncbi.nlm.nih.gov/account/ 註冊 NCBI 帳號，在帳號設定中產生 API Key。

---

## 執行管線

以下是完整的執行流程。每一步都是獨立的指令，按順序執行即可。

> **提示**：每個指令執行完畢後會顯示摘要統計。如果中途失敗，修正問題後重新執行同一步即可（所有步驟皆為冪等操作，重複執行不會產生重複資料）。

### Step 1：建立基因宇宙

```bash
usher-pipeline setup
```

這一步會：
- 透過 mygene API 查詢所有人類蛋白質編碼基因（約 22,600 個）
- 建立 Ensembl Gene ID ↔ HGNC Symbol ↔ UniProt Accession 的對應關係
- 結果儲存至本地 DuckDB 資料庫（`data/pipeline.duckdb`）

### Step 2：執行六大證據層面

六個層面可以按任意順序執行，彼此之間互相獨立。但請**逐一執行**，不要同時開兩個（DuckDB 僅支援單一寫入者）。

```bash
# 2a. gnomAD 約束性指標
usher-pipeline evidence gnomad

# 2b. 基因功能註釋
usher-pipeline evidence annotation

# 2c. 組織表達特異性
usher-pipeline evidence expression

# 2d. 亞細胞定位
usher-pipeline evidence localization

# 2e. 動物模型表型
usher-pipeline evidence animal-models

# 2f. 文獻探勘（需要 email，建議提供 API key）
usher-pipeline evidence literature --email your@email.com --api-key YOUR_KEY
```

> **注意**：文獻探勘層需要查詢 22,600 個基因的 PubMed 記錄，速度較慢（約 8 基因/分鐘），完整執行可能需要較長時間。此層支援中斷後續跑（checkpoint-restart），如果中途斷線，重新執行同一指令即可從上次進度繼續。

### Step 3：綜合評分

```bash
usher-pipeline score
```

此步驟會：
- 以 LEFT JOIN 合併六個證據層的分數
- 計算 NULL-aware 加權綜合分數
- 對已知 Usher/纖毛基因進行排名驗證（正控制）
- 將基因分為 HIGH / MEDIUM / LOW 三個信心層級

### Step 4：產出報告

```bash
usher-pipeline report
```

產出檔案會放在 `data/report/` 目錄，包含：
- `candidates.tsv` — 候選基因清單（可用 Excel 開啟）
- `candidates.parquet` — 同上，但為高效能二進位格式（適合 R / Python 後續分析）
- `score_distribution.png` — 分數分佈圖
- `evidence_coverage.png` — 各證據層覆蓋率圖
- `tier_distribution.png` — 信心層級分佈圓餅圖
- `reproducibility.md` — 可重現性報告（含所有參數與資料版本）

### 選用：驗證報告

```bash
usher-pipeline validate
```

驗證已知 Usher 基因與 SYSCILIA 纖毛基因是否排名在前 25%，確認評分系統的有效性。

---

## 六大證據層面詳解

### 1. gnomAD 約束性分析

**生物學問題**：此基因是否在人類族群中顯示強烈的功能喪失（Loss-of-Function）選擇約束？

**資料來源**：gnomAD v4.1 約束性指標

**科學依據**：
如果一個基因對正常生理功能是必要的（例如感覺功能），那麼在人類族群中應該很少觀察到該基因的功能喪失型變異（LoF variants），因為帶有這些變異的個體會有降低的適應性。gnomAD 資料庫透過比較「觀察到的 LoF 變異數量」與「預期的 LoF 變異數量」，計算出約束性指標。

**關鍵指標**：
- **LOEUF**（Loss-of-function Observed/Expected Upper bound Fraction）：越低代表約束越強
- **pLI**（Probability of LoF Intolerance）：越高代表越不容忍 LoF 變異

**評分方式**：
將 LOEUF 值反轉並正規化至 0–1 範圍：

```
loeuf_normalized = (LOEUF_max − LOEUF) / (LOEUF_max − LOEUF_min)
```

分數越高 = 約束性越強 = 該基因對正常功能越重要。

**品質控管**：要求平均定序深度 ≥30x 且 CDS 涵蓋率 ≥90%，低於此閾值的基因標記為 `incomplete_coverage`。

---

### 2. 基因功能註釋

**生物學問題**：此基因的功能註釋完整程度如何？

**資料來源**：
- Gene Ontology（GO）— 生物過程、分子功能、細胞組分
- UniProt — 蛋白質註釋品質分數（0–5）
- KEGG / Reactome — 代謝與訊號傳遞路徑

**科學依據**：
功能註釋的完整程度反映了一個基因被研究的深度。注意：此層面與「新穎性」呈**負相關**——註釋越少的基因可能代表尚未被發現的生物學。因此在綜合評分中，此層僅佔 15% 權重，讓缺乏註釋但有其他證據支持的新穎候選基因仍能獲得高排名。

**評分方式**：

```
annotation_score = 0.5 × GO 組分 + 0.3 × UniProt 組分 + 0.2 × Pathway 組分

其中：
  GO 組分 = log₂(GO term 數量 + 1) / log₂(最大 GO term 數量 + 1)
  UniProt 組分 = UniProt 分數 / 5.0
  Pathway 組分 = 若有任何 pathway 註釋則為 1，否則為 0
```

---

### 3. 組織表達特異性

**生物學問題**：此基因是否特異性地表達在 Usher 症候群相關的組織（視網膜、內耳）？

**資料來源**：
- **HPA**（Human Protein Atlas）v23 — 組織層級 RNA 表達量（TPM）
- **GTEx** v8 — 54 個人體組織的大量 RNA 定序資料
- **CellxGene** — 單細胞 RNA 定序（光受器細胞、毛細胞群體）

**科學依據**：
Usher 症候群影響視網膜光受器細胞與耳蝸毛細胞。若一個基因在這些組織中高度富集表達，暗示其在這些組織具有特化功能，是值得關注的候選基因。

**關鍵指標**：

1. **Tau 組織特異性指數**（τ）：衡量一個基因在各組織間的表達均勻程度
   - τ = 0：遍在表達（housekeeping gene）
   - τ = 1：高度組織特異性
   - 公式：`τ = Σ(1 − xᵢ/x_max) / (n − 1)`

2. **Usher 組織富集度**：目標組織（視網膜、小腦、光受器、毛細胞）的平均表達量，除以所有組織的整體平均表達量。比值 > 1 代表在目標組織富集。

**評分方式**：

```
expression_score = 0.4 × 富集度百分位數 + 0.3 × τ 特異性 + 0.3 × 目標組織最大表達百分位數
```

使用百分位數正規化，避免絕對 TPM 值因定序深度差異而產生偏差。

---

### 4. 亞細胞定位

**生物學問題**：此蛋白質是否定位在纖毛、中心體或基體等與 Usher 病理機轉相關的亞細胞結構？

**資料來源**：
- **HPA 亞細胞定位資料** — 免疫螢光顯微鏡
- **纖毛蛋白質體學** — 已發表的纖毛質譜資料集（CiliaCarta 等）
- **中心體蛋白質體學** — 已發表的中心體質譜資料集

**科學依據**：
已知的 Usher 蛋白（MYO7A、USH1C、CDH23 等）都是纖毛或纖毛周邊蛋白。蛋白質定位在纖毛/基體/中心體，是參與纖毛病變途徑的**強力機制性證據**。

**評分方式**：

| 定位區域 | 基礎分數 |
|---------|---------|
| 纖毛、中心體、基體、轉換區、靜纖毛 | 1.0 |
| 細胞骨架、微管、細胞連接 | 0.5 |
| 僅出現在蛋白質體學資料集 | 0.3 |
| 有定位資料但與纖毛無關 | 0.0 |
| 無定位資料 | NULL |

**證據權重**：
- 實驗證據（HPA Enhanced/Supported 可靠度、蛋白質體學）：× 1.0
- 計算預測（HPA Approved/Uncertain 可靠度）：× 0.6

```
localization_score = 纖毛接近度基礎分數 × 證據類型權重
```

---

### 5. 動物模型表型

**生物學問題**：在小鼠或斑馬魚中，此基因的直系同源物（ortholog）被破壞時，是否會產生感覺或纖毛相關的表型？

**資料來源**：
- **HCOP**（HUGO Gene Nomenclature Committee Ortholog Predictions）— 人-鼠/人-魚直系同源物對應
- **MGI**（Mouse Genome Informatics）— 小鼠基因剔除表型（MP ontology）
- **ZFIN**（Zebrafish Information Network）— 斑馬魚突變表型
- **IMPC**（International Mouse Phenotyping Consortium）— 系統性基因剔除篩選

**科學依據**：
跨物種的感覺表型保守性提供了**功能驗證**。小鼠的聽力/平衡缺陷及斑馬魚的側線系統缺陷，都能重現人類 Usher 症候群的病理特徵。

**表型關鍵字篩選**：
- 小鼠：hearing、vision、retina、photoreceptor、cochlea、stereocilia、cilia、vestibular、balance
- 斑馬魚：hearing、ear、otic、otolith、lateral line、hair cell、retina、vision、eye

**評分方式**：

```
animal_model_score =
    0.4 × 小鼠分數 × 小鼠信心度 +
    0.3 × 斑馬魚分數 × 斑馬魚信心度 +
    0.3 × IMPC 額外加分

信心度權重：HIGH = 1.0, MEDIUM = 0.7, LOW = 0.4
表型數量縮放：log₂(感覺表型數量 + 1) / log₂(最大數量 + 1)
```

使用對數縮放防止註釋數量過多的基因主導排名（報酬遞減效應）。

---

### 6. 文獻探勘

**生物學問題**：此基因在科學文獻中是否被提及與纖毛或感覺功能相關？文獻證據的品質如何？

**資料來源**：NCBI PubMed（透過 E-utilities API）

**科學依據**：
文獻證據反映了累積的科學知識，但存在**研究偏差**（study bias）——明星基因（如 TP53、BRCA1）擁有大量文獻，但這不代表它們與纖毛相關。本層的正規化策略特別針對這個問題進行校正。

**證據品質分級**：

| 等級 | 說明 | 權重 |
|------|------|------|
| direct_experimental | 基因剔除/突變 + 纖毛/感覺語境 | 1.0 |
| functional_mention | 纖毛/感覺語境 + ≥3 篇文獻 | 0.6 |
| hts_hit | 高通量篩選命中 + 纖毛/感覺語境 | 0.3 |
| incidental | 有文獻但無纖毛/感覺語境 | 0.1 |
| none | 無文獻 | 0.0 |

**研究偏差校正**：

```
raw_score = (語境分數 × 品質權重) / log₂(PubMed 總文獻數 + 1)
literature_score = percentile_rank(raw_score)
```

除以 `log₂(總文獻數)` 的關鍵意義：一個基因若在 50 篇文獻中有 5 篇提及纖毛，會比在 100,000 篇文獻中有 5 篇提及纖毛得到更高的分數。這鼓勵發現被忽略但有線索的基因。

---

## 綜合評分與分層

### 加權綜合分數

六個證據層以可調整的權重合併為單一綜合分數：

| 證據層 | 預設權重 | 生物學意義 |
|--------|---------|-----------|
| gnomAD 約束性 | 20% | 基因的功能必要性 |
| 組織表達 | 20% | 在目標組織的特異性表達 |
| 功能註釋 | 15% | 已知的功能特徵 |
| 亞細胞定位 | 15% | 纖毛結構的接近程度 |
| 動物模型 | 15% | 跨物種的功能驗證 |
| 文獻探勘 | 15% | 文獻中的纖毛/感覺關聯 |

**NULL-aware 加權平均**：

```
composite_score = Σ(scoreᵢ × weightᵢ) / Σ(weightᵢ)
                  ─── 僅計算非 NULL 的層面 ───
```

例如：某基因只有 gnomAD（0.8）、表達（0.6）和定位（0.9）三層有資料：

```
composite_score = (0.8×0.20 + 0.6×0.20 + 0.9×0.15) / (0.20 + 0.20 + 0.15)
               = 0.415 / 0.55
               = 0.755
```

### 信心分層

| 層級 | 條件 | 意義 |
|------|------|------|
| **HIGH** | 綜合分數 ≥ 0.7 且 ≥ 3 層有資料 | 高優先候選基因，建議進入實驗驗證 |
| **MEDIUM** | 綜合分數 ≥ 0.4 且 ≥ 2 層有資料 | 中等證據，值得進一步文獻調查 |
| **LOW** | 綜合分數 ≥ 0.2 | 證據薄弱，需要更多資料 |
| EXCLUDED | 低於以上條件 | 排除，不列入候選清單 |

### 品質旗標

| 旗標 | 條件 | 說明 |
|------|------|------|
| sufficient_evidence | ≥ 4 層有分數 | 資料涵蓋充分 |
| moderate_evidence | ≥ 2 層有分數 | 部分涵蓋 |
| sparse_evidence | ≥ 1 層有分數 | 資料稀疏 |
| no_evidence | 0 層有分數 | 完全無資料 |

---

## 驗證機制

管線內建正控制驗證，確認評分系統的有效性：

### 正控制基因集

1. **OMIM Usher 基因**（10 個）：MYO7A、USH1C、CDH23、PCDH15、USH1G、CIB2、USH2A、ADGRV1、WHRN、CLRN1
2. **SYSCILIA SCGS v2 核心纖毛基因**（28 個）：IFT88、IFT140、BBS1、CEP290、RPGR 等

### 驗證標準

- 已知基因的中位百分位排名應 ≥ 75%（前四分之一）
- 前 10% 候選基因應包含 > 70% 的已知基因（Recall@10%）

如果驗證未通過，表示權重設定或資料品質可能有問題，需要檢視並調整。

---

## 產出檔案說明

所有結果儲存在 `data/report/` 目錄：

| 檔案 | 說明 | 適用對象 |
|------|------|---------|
| `candidates.tsv` | 候選基因清單（Tab 分隔） | 用 Excel 或文字編輯器開啟 |
| `candidates.parquet` | 同上，高效能二進位格式 | R（`arrow::read_parquet`）或 Python（`polars.read_parquet`） |
| `score_distribution.png` | 分數分佈直方圖 | 快速了解整體分佈 |
| `evidence_coverage.png` | 各證據層覆蓋率圖 | 了解哪些層資料最完整 |
| `tier_distribution.png` | HIGH/MEDIUM/LOW 比例圓餅圖 | 快速概覽 |
| `reproducibility.md` | 完整的參數、資料版本與軟體環境記錄 | 論文方法學 / 重現分析 |

### candidates.tsv 欄位說明

**核心欄位**：
- `gene_id` — Ensembl 基因 ID（如 ENSG00000154229）
- `gene_symbol` — HGNC 基因符號（如 MYO7A）
- `composite_score` — 綜合分數（0–1）
- `confidence_tier` — 信心層級（HIGH / MEDIUM / LOW）
- `evidence_count` — 有非 NULL 分數的證據層數量（0–6）

**各層分數**（0–1，NULL 表示無資料）：
- `gnomad_score` — 約束性分數
- `expression_score` — 表達特異性分數
- `annotation_score` — 功能註釋分數
- `localization_score` — 亞細胞定位分數
- `animal_model_score` — 動物模型表型分數
- `literature_score` — 文獻證據分數

**輔助欄位**：
- `supporting_layers` — 有分數的層面清單（如 `gnomad,expression,localization`）
- `evidence_gaps` — 缺少資料的層面清單
- `quality_flag` — 品質旗標

---

## 設定檔調整

管線設定檔位於 `config/default.yaml`：

```yaml
# 資料版本
versions:
  ensembl_release: 113
  gnomad_version: v4.1
  gtex_version: v8
  hpa_version: "23.0"

# 評分權重（可依研究需求調整，總和必須為 1.0）
scoring:
  gnomad: 0.20
  expression: 0.20
  annotation: 0.15
  localization: 0.15
  animal_model: 0.15
  literature: 0.15

# API 設定
api:
  rate_limit_per_second: 5
  max_retries: 5
  timeout_seconds: 30
```

若要調整權重（例如更重視組織表達），修改 `scoring` 區塊後重新執行 `usher-pipeline score` 與 `usher-pipeline report` 即可。

---

## 已知限制

| 限制 | 說明 | 影響 |
|------|------|------|
| GTEx v8 無視網膜組織 | GTEx v8 不包含 "Eye - Retina" 組織 | 視網膜表達資料僅來自 HPA |
| HPA 基因符號比對落差 | HPA 使用 gene symbol，管線以 gene ID 為主鍵 | 部分基因的 HPA 表達資料可能遺失 |
| gnomAD 轉錄本層級 ID | gnomAD 使用轉錄本 ID，非基因層級 | 部分基因 JOIN 時可能產生 NaN |
| 文獻探勘速度 | NCBI API 限制，~8 基因/分鐘 | 完整執行需要較長時間；可使用 API key 加速 |
| 單一寫入限制 | DuckDB 不支援多行程同時寫入 | 請勿同時執行兩個管線步驟 |
| 內耳資料稀缺 | 人類耳蝸組織的大量轉錄體資料有限 | 以小腦（含纖毛）及 CellxGene 毛細胞資料作為替代 |

---

## 引用資料庫

本管線整合以下公開資料庫與工具：

- **gnomAD** v4.1 — Karczewski et al. (2020) *Nature* 581:434-443
- **Human Protein Atlas** v23 — Uhlén et al. (2015) *Science* 347:1260419
- **GTEx** v8 — GTEx Consortium (2020) *Science* 369:1318-1330
- **CellxGene** — Chan Zuckerberg Initiative single-cell atlas
- **Gene Ontology** — Gene Ontology Consortium (2021) *Nucleic Acids Res* 49:D325-D334
- **UniProt** — UniProt Consortium (2023) *Nucleic Acids Res* 51:D523-D531
- **MGI** — Mouse Genome Informatics, The Jackson Laboratory
- **ZFIN** — Zebrafish Information Network
- **IMPC** — International Mouse Phenotyping Consortium
- **SYSCILIA SCGS v2** — van Dam et al. (2021) *Mol Biol Cell* 32:br6
- **mygene.info** — Xin et al. (2016) *Genome Biol* 17:91
- **NCBI E-utilities** — PubMed literature search API

---

## 授權

MIT License
