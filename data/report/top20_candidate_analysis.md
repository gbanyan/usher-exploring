# TOP 20 Usher 候選基因分析（修正後 6 層證據）

**Pipeline Version:** 0.1.0
**Generated:** 2026-05-20（4 個 pipeline bug 修正後重跑：CellxGene 層、Tau specificity、MGI/ZFIN 解析、HCOP URL）
**Scoring Layers:** gnomAD constraint (0.20) + Expression (0.20) + Annotation (0.15) + Localization (0.15) + Animal Model (0.15) + Literature (0.15)
**Coverage:** gnomAD 91% | Expression 98% | Annotation 99% | Localization 66% | Animal Model 98% | Literature 99%
**Tier Statistics:** HIGH 95 | MEDIUM 11,335 | LOW 7,702 | Total 19,132 candidates（from 19,554 scored genes，HIGH 層已套用 cilia-signal gate）
**Validation:** 陽性對照 median 90.2%、35/38 在前四分位；最高 CDH23 99.8th percentile

> 本表所列為 layer normalized score（0–1，pipeline 實際使用值），非原始 LOEUF/TPM。`composite_score = weighted_sum / available_weight`，分母僅計非 NULL 層權重。

---

## 方法論

每個 gene_symbol 保留 evidence_count 最多的 Ensembl ID（相同則取 composite 最高者）；22,604 → 19,554 genes。本次重跑修正了四個錯誤：(1) CellxGene 單細胞層先前在 Python 3.13 環境下靜默失效，現補齊光受器表達（約 19,500 基因）；(2) Tau specificity 先前因要求全部 10 個組織欄非空而恆為 NULL，現改為以各基因可得組織計算；(3) MGI/ZFIN 表型解析器先前因檔案無表頭而回傳空集，動物模型層先前僅含 IMPC，現含 MGI+ZFIN+IMPC（具感覺表型基因 945 → 5,477）；(4) HCOP ortholog URL 已從 EBI FTP 遷移至 Google Cloud Storage。

候選基因以「sufficient evidence（≥4 層）」篩選，與 manuscript 的 Top candidate 一致。

---

## Top 20 候選基因總覽（≥4 層證據）

| # | Gene | Score | Layers | gnomAD | Expr | Annot | Local | Animal | Lit |
|---|------|-------|--------|--------|------|-------|-------|--------|-----|
| 1 | **VANGL2** | **0.850** | 5/6 | 0.802 | 0.813 | 0.814 | — | **0.909** | 0.940 |
| 2 | **ATP1B1** | **0.833** | 5/6 | 0.923 | 0.929 | 0.893 | — | 0.476 | 0.881 |
| 3 | **DYNC1H1** | **0.826** | 6/6 | 0.966 | 0.903 | 0.845 | 1.000 | 0.169 | 0.998 |
| 4 | VEGFA | 0.819 | 5/6 | 0.951 | 0.746 | 0.955 | — | 0.425 | 0.996 |
| 5 | CCT5 | 0.811 | 5/6 | 0.913 | 0.682 | 0.816 | — | 0.674 | 0.977 |
| 6 | ATP1A1 | 0.806 | 5/6 | 0.937 | 0.923 | 0.889 | — | 0.224 | 0.973 |
| 7 | DYNC1LI1 | 0.800 | 6/6 | 0.836 | 0.721 | 0.822 | 1.000 | 0.444 | 0.990 |
| 8 | PAFAH1B1 | 0.798 | 6/6 | 0.969 | 0.811 | 0.913 | 1.000 | 0.048 | 0.988 |
| 9 | ATP2B2 | 0.786 | 5/6 | 0.955 | 0.986 | 0.848 | — | 0.063 | 0.955 |
| 10 | AHI1 | 0.785 | 6/6 | 0.569 | 0.846 | 0.801 | 1.000 | 0.555 | 0.989 |
| 11 | PKD1 | 0.784 | 5/6 | 0.836 | 0.975 | 0.906 | — | 0.123 | 1.000 |
| 12 | HDAC6 | 0.773 | 5/6 | — | 0.781 | 0.927 | 1.000 | 0.158 | 0.996 |
| 13 | ODF2 | 0.771 | 6/6 | 0.806 | 0.660 | 0.792 | 1.000 | 0.398 | 0.994 |
| 14 | NEUROD1 | 0.769 | 5/6 | 0.669 | 0.992 | 0.871 | — | 0.434 | 0.838 |
| 15 | YWHAZ | 0.766 | 5/6 | 0.970 | 0.781 | 0.851 | — | 0.222 | 0.933 |
| 16 | ARHGEF2 | 0.766 | 5/6 | 0.897 | 0.849 | 0.851 | — | 0.176 | 0.985 |
| 17 | TCP1 | 0.766 | 5/6 | 0.947 | 0.709 | 0.831 | — | 0.312 | 0.987 |
| 18 | ANP32A | 0.765 | 6/6 | 0.947 | 0.866 | 0.768 | 1.000 | 0.000 | 0.914 |
| 19 | MAPK8 | 0.761 | 5/6 | 0.812 | 0.790 | 0.868 | — | 0.333 | 0.978 |
| 20 | BMP4 | 0.760 | 5/6 | 0.888 | 0.637 | 0.956 | — | 0.503 | 0.812 |

> 修正後動物模型層（MGI+ZFIN+IMPC）使多個感覺表型基因上升：VANGL2 因 *Vangl2* 突變小鼠的內耳/神經管表型躍居首位。Localization 層覆蓋率僅 66%，多數 5/6 層基因即缺此層。

---

## 逐基因摘要

### #1 — VANGL2（Planar Cell Polarity 核心蛋白）
平面細胞極性（PCP）核心成員，調控耳蝸毛細胞 stereocilia bundle 的協調定向。*Vangl2* looptail (Lp) 突變小鼠出現內耳毛細胞極性異常與神經管缺陷——animal model 層 0.909 為 top 20 最高。缺 localization 數據（NULL），是 NULL-aware 設計避免被 zero imputation 懲罰的代表案例。

### #2 — ATP1B1（Na⁺/K⁺-ATPase β1 亞單位）
與 ATP1A1（#6）組成 Na⁺/K⁺ pump，在 stria vascularis 維持 endolymph K⁺ 梯度——聽覺轉導必需。各層分數均衡偏高。

### #3 — DYNC1H1（Cytoplasmic Dynein 重鏈）
分子馬達催化核心，驅動 IFT retrograde transport 與中心粒遷移。Centrosome/纖毛定位 1.0、文獻 0.998、極高 constraint 0.966。修正後動物模型層 0.169（先前因解析錯誤為 0.0）——多數 *Dync1h1* 表型登錄於神經發育而非感覺類詞彙。

### #4 — VEGFA（血管內皮生長因子 A）
血管生成核心因子；annotation 與 literature 極高（眼科血管新生研究龐大）。與 ciliopathy 直接連結較弱，高分主要由非特異層驅動。

### #5 — CCT5（CCT/TRiC Chaperonin 亞單位 ε）
TRiC/CCT 摺疊複合體成員。TRiC/CCT-BBS chaperonin 已知參與 BBSome 組裝（見 manuscript 參考 [30] Usher interactome）；與 #17 TCP1 共同出現提示 chaperonin 路徑訊號。

### #6 — ATP1A1（Na⁺/K⁺-ATPase α1）
Na⁺/K⁺ pump 的 ubiquitous α 亞單位，與 ATP1B1（#2）功能成對，stria vascularis 離子恆定。

### #7 — DYNC1LI1（Dynein Light Intermediate Chain 1）
細胞質 dynein 複合體成員，參與 IFT 逆行運輸；6/6 全層、centrosome 定位 1.0。與 DYNC1H1、PAFAH1B1 同屬 dynein 系統收斂訊號。

### #8 — PAFAH1B1 / LIS1（Dynein 調控因子）
cytoplasmic dynein 關鍵調控因子，IFT 與中心粒定位必需 [24]；centrosome 定位 1.0、極高 constraint 0.969。感覺動物模型分數低（0.048），因 *Lis1* 小鼠表型登錄於神經發育詞彙。

### #9 — ATP2B2（Plasma Membrane Ca²⁺-ATPase 2）
*deafwaddler* 小鼠（*Atp2b2* 自發突變）完全失聰並具前庭功能異常 [27]，表型擬似 USH type 1；在毛細胞 stereocilia 頂端排出 Ca²⁺。expression 層 0.986 極高。

### #10 — AHI1（Jouberin，已知 Joubert 症候群基因）
已知纖毛病基因（Joubert 症候群），具視網膜表現。排名第 10 為陽性對照式回收——顯示修正後 6 層計分能識別真實纖毛生物學。

### #11 — PKD1 / Polycystin-1（已知 Ciliopathy — 陽性對照）
ADPKD 致病基因，polycystin-1 為 primary cilia 機械感受器。文獻層 1.000。陽性對照。

### #12 — HDAC6（Histone Deacetylase 6）
去乙醯化 α-tubulin、調控纖毛 disassembly；HDAC6 抑制劑可穩定纖毛，是 ciliopathy 治療研究靶點。gnomAD 層 NULL（chrX 相關）。localization 1.0。

### #13 — ODF2 / Cenexin（Outer Dense Fiber 2）
基底體/纖毛附屬結構蛋白（distal/subdistal appendage），ciliogenesis 必需。6/6 全層、localization 1.0。

### #14 — NEUROD1（bHLH 轉錄因子）
內耳與視網膜神經元分化的 bHLH 轉錄因子；*Neurod1* 小鼠有耳蝸與前庭神經元缺陷。expression 層 0.992 極高。

### #15 — YWHAZ（14-3-3ζ）— 注意：同時為陰性對照
14-3-3ζ；本基因同時是 13 個 housekeeping 陰性對照之一，卻排名第 15 且 `has_cilia_signal = true`（animal 0.222）。此例正說明 manuscript 所述的特異性限制——constraint/annotation/literature 等非特異層可將泛表達基因推高。解讀候選時須檢視各層分數。

### #16 — ARHGEF2（Rho/Rac Guanine Exchange Factor 2）
微管相關 Rho GEF，調控細胞骨架與細胞分裂；與纖毛/中心體細胞骨架調控有間接連結。

### #17 — TCP1（CCT/TRiC Chaperonin 亞單位 α）
TRiC/CCT 摺疊複合體亞單位，與 #5 CCT5 同屬 chaperonin——TRiC/CCT-BBS 與 BBSome 組裝相關，構成 convergent 路徑訊號。

### #18 — ANP32A（Acidic Nuclear Phosphoprotein 32A）
Histone chaperone / phosphatase inhibitor；6/6 全層、centrosome 定位，但纖毛/感覺文獻極少（animal 0.000），與 Usher 的直接連結不明確。

### #19 — MAPK8 / JNK1（c-Jun N-terminal Kinase 1）
壓力活化 MAP kinase；參與 PCP 路徑下游訊號與細胞凋亡，與內耳發育有間接連結。

### #20 — BMP4（Bone Morphogenetic Protein 4）
BMP 訊號配體，調控內耳半規管與毛細胞分化；animal model 層 0.503、annotation 0.956。

---

## 優先級總結

### Tier 1 — 直接纖毛/感覺機制
| 基因 | Layers | 核心理由 |
|------|--------|---------|
| **VANGL2** | 5/6 | PCP 核心；looptail 小鼠內耳毛細胞極性缺陷；animal 層 top 20 最高 |
| **DYNC1H1 / DYNC1LI1 / PAFAH1B1** | 6/6 | Dynein–IFT 系統收斂；centrosome 定位 1.0；極高 constraint |
| **ATP2B2** | 5/6 | deafwaddler 小鼠失聰；stereocilia Ca²⁺ pump |
| **ODF2** | 6/6 | 基底體 appendage 蛋白；ciliogenesis 必需 |
| **HDAC6** | 5/6 | 纖毛 disassembly 調控；ciliopathy 治療靶點 |

### Tier 2 — 強多層證據 + 感覺系統角色
| 基因 | 核心理由 |
|------|---------|
| **ATP1B1 + ATP1A1** | Na⁺/K⁺ pump；stria vascularis endolymph 恆定 |
| **CCT5 + TCP1** | TRiC/CCT chaperonin；與 BBSome 組裝相關（convergent） |
| **NEUROD1 / BMP4** | 內耳毛細胞與神經元分化轉錄/訊號因子 |

### 陽性對照回收
**AHI1**（#10，Joubert）與 **PKD1**（#11，ADPKD）為已知纖毛病基因，排名前列，驗證修正後計分系統的有效性。

### 特異性警示
**YWHAZ**（#15）同時是 housekeeping 陰性對照——說明非特異層（constraint/annotation/literature）可將泛表達基因推入高分。候選須結合 `has_cilia_signal` 旗標與逐層分數判讀。

---

## 關鍵觀察

1. **Dynein–IFT 系統收斂**：DYNC1H1、DYNC1LI1、PAFAH1B1 三個 dynein 複合體成員同入 top 8，為 pipeline 最強的 ciliopathy 訊號。
2. **Na⁺/K⁺ pump 收斂**：ATP1B1 與 ATP1A1 同入 top 6，指向 stria vascularis endolymph 恆定作為聽力退化機制。
3. **TRiC/CCT chaperonin 新訊號**：CCT5 與 TCP1 同入 top 20——TRiC/CCT-BBS chaperonin 與 BBSome 組裝相關，值得追查。
4. **修正後動物模型層改變排名**：MGI/ZFIN 表型修正使 VANGL2 躍居首位；具感覺表型基因由 945 增至 5,477。
5. **特異性仍為限制**：YWHAZ（housekeeping）排第 15，與 manuscript 陰性對照分析一致。

---

## 建議下一步

1. **VANGL2**：檢視 PCP 路徑與 Usher 蛋白網絡的交集；查詢 Usher 患者 cohort 中 VANGL2 變異。
2. **ATP2B2**：查詢 Usher cohort 中 ATP2B2 變異；deafwaddler 模型是否有視網膜表型。
3. **Dynein 系統（DYNC1H1/DYNC1LI1/PAFAH1B1）**：調查 lissencephaly/SMA 患者是否有亞臨床聽力/視力退化。
4. **CCT5/TCP1**：檢驗 TRiC/CCT 與 BBSome 組裝在感覺纖毛中的角色。
5. 補齊 **CellxGene 內耳毛細胞** 單細胞數據（Census 目前尚無）以提升 cochlear 組織特異性。
