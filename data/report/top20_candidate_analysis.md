# TOP 20 Usher 候選基因分析（完整 6 層證據）

**Pipeline Version:** 0.1.0
**Generated:** 2026-02-16 (v4 — gene_symbol deduplication 修正後)
**Scoring Layers:** gnomAD constraint (0.20) + Expression (0.20) + Annotation (0.15) + Localization (0.15) + Animal Model (0.15) + Literature (0.15)
**Coverage:** gnomAD 91.5% | Expression 96.1% | Annotation 98.9% | Localization 66.1% | Animal Model 97.9% | Literature 100%
**Tier Statistics:** HIGH: 4 | MEDIUM: 8,051 | LOW: 10,188 | Total: 18,243 (from 19,555 unique genes)

---

## v4 修正：gene_symbol 去重

### 問題
`gene_universe` 中 1,539 個 gene_symbol 對應多個 Ensembl ID（共 3,033 個多餘 ID）。非 canonical ID 在部分 evidence table 中缺少數據，因此只有 3 層但分數被 `weighted_sum/available_weight` 膨脹。例如：

| Gene | Ensembl ID | Layers | Score | 原因 |
|------|-----------|--------|-------|------|
| CACNA1C | ENSG00000285479 (non-canonical) | 3/6 | **0.8830** | 缺 expression/animal → 分母小 |
| CACNA1C | ENSG00000151067 (canonical) | 5/6 | 0.6334 | 有完整數據 → 真實分數 |

### 修正
在 `compute_composite_scores()` 中，對每個 gene_symbol 保留 `evidence_count` 最多的 Ensembl ID（相同 evidence_count 取 composite_score 最高者）。去重後 22,604 → 19,555 genes。

---

## Top 20 候選基因總覽

| Rank | Gene | Composite | Layers | Tier | gnomAD | Expression | Annotation | Localization | Literature |
|------|------|-----------|--------|------|--------|------------|------------|--------------|------------|
| 1 | **PAFAH1B1** | **0.7414** | **6/6** | HIGH | 0.969 | 0.597 | 0.928 | 1.000 | 0.927 |
| 2 | **DYNC1H1** | **0.7344** | **6/6** | HIGH | 0.966 | 0.648 | 0.843 | 1.000 | 0.902 |
| 3 | **SMAD4** | **0.7227** | **6/6** | HIGH | 0.932 | 0.529 | 0.948 | 1.000 | 0.921 |
| 4 | **DLG4** | **0.7116** | **5/6** | HIGH | 0.980 | 0.674 | 0.905 | — | 0.924 |
| 5 | CRMP1 | 0.6888 | 6/6 | MED | 0.866 | 0.666 | 0.794 | 1.000 | 0.754 |
| 6 | FGFR1 | 0.6857 | 5/6 | MED | 0.917 | 0.615 | 0.917 | — | 0.926 |
| 7 | ATP1A3 | 0.6833 | 5/6 | MED | 0.940 | 0.680 | 0.851 | — | 0.860 |
| 8 | ATP2B2 | 0.6832 | 5/6 | MED | 0.955 | 0.688 | 0.843 | — | 0.838 |
| 9 | PKD1 | 0.6831 | 5/6 | MED | 0.836 | 0.685 | 0.913 | — | 0.930 |
| 10 | ARL3 | 0.6826 | 6/6 | MED | 0.800 | 0.545 | 0.835 | 1.000 | 0.923 |
| 11 | GRIA2 | 0.6810 | 5/6 | MED | 0.957 | 0.656 | 0.831 | — | 0.877 |
| 12 | SNCA | 0.6810 | 5/6 | MED | 0.817 | 0.667 | 0.949 | — | 0.932 |
| 13 | HDAC6 | 0.6801 | 5/6 | MED | — | 0.573 | 0.928 | 1.000 | 0.934 |
| 14 | VAMP2 | 0.6786 | 5/6 | MED | 0.930 | 0.669 | 0.875 | — | 0.838 |
| 15 | MAPRE3 | 0.6769 | 5/6 | MED | 0.948 | 0.662 | 0.807 | — | 0.883 |
| 16 | ATP1B1 | 0.6754 | 5/6 | MED | 0.923 | 0.662 | 0.893 | — | 0.744 |
| 17 | ANP32A | 0.6743 | 6/6 | MED | 0.947 | 0.618 | 0.765 | 1.000 | 0.644 |
| 18 | ATP1A1 | 0.6741 | 5/6 | MED | 0.937 | 0.662 | 0.897 | — | 0.792 |
| 19 | SCN2A | 0.6733 | 5/6 | MED | 0.938 | 0.670 | 0.814 | — | 0.859 |
| 20 | VEGFA | 0.6722 | 5/6 | MED | 0.951 | 0.473 | 0.968 | — | 0.942 |

> **觀察:** 去重後 top 20 **全部有 5-6 層 evidence**，expression 層不再缺失。前 4 名（PAFAH1B1、DYNC1H1、SMAD4、DLG4）全是 LoF-intolerant 基因且有 centrosome/sensory 相關定位或文獻。

---

## 逐基因詳細分析

### #1 — PAFAH1B1 / LIS1（Dynein 調控因子）⭐

| 指標 | 值 |
|------|------|
| Composite | 0.7414 |
| Evidence layers | **6/6 全層** |
| gnomAD | LOEUF=0.100 (norm=0.969) — **極度 LoF intolerant (top 1%)**, pLI=1.000 |
| Expression | GTEx cerebellum=131.0 TPM; enrichment=1.17; norm=0.597 |
| Localization | HPA: **Centrosome**; proximity=1.000 |
| Literature | 496 篇; cilia=4, sensory=3, direct_exp=4, cyto=424; tier=direct_experimental |

**解讀:** LIS1 是 cytoplasmic dynein 的關鍵調控因子，控制微管 minus-end transport。Dynein 負責 IFT（intraflagellar transport）逆行運輸，是纖毛維持的核心機制。LIS1 突變致 lissencephaly（無腦回畸形），極度 LoF intolerant。與 Usher 的連結：**dynein transport 對感覺纖毛（photoreceptor connecting cilium、stereocilia kinocilium）至關重要**。

---

### #2 — DYNC1H1（Cytoplasmic Dynein 重鏈）⭐

| 指標 | 值 |
|------|------|
| Composite | 0.7344 |
| Evidence layers | **6/6 全層** |
| gnomAD | LOEUF=0.117 (norm=0.966) — **極度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=129.1 TPM; enrichment=1.68; norm=0.648 |
| Localization | HPA: **Centrosome + Cytosol**; proximity=1.000 |
| Literature | 211 篇; cilia=10, sensory=9, direct_exp=6; tier=direct_experimental |

**解讀:** Dynein 重鏈——分子馬達的催化核心。驅動 IFT retrograde transport 和中心粒遷移。DYNC1H1 突變導致 cortical malformation 和 spinal muscular atrophy。**纖毛中 dynein 運輸缺陷是多種 ciliopathy 的核心病理，連結 photoreceptor disc renewal 和 hair cell 功能。** 10 篇纖毛 + 9 篇感覺文獻在 211 篇中占 9%。

---

### #3 — SMAD4（TGF-β/BMP 核心轉錄因子）⭐

| 指標 | 值 |
|------|------|
| Composite | 0.7227 |
| Evidence layers | **6/6 全層** |
| gnomAD | LOEUF=0.227 (norm=0.932) — **高度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=28.8 TPM; enrichment=1.10; norm=0.529 |
| Localization | HPA: Cytosol + Nucleoplasm + **Centrosome**; proximity=1.000 |
| Literature | 6,577 篇; cilia=6, sensory=78, polarity=49; tier=direct_experimental |

**解讀:** TGF-β/BMP 信號通路的核心介導者。BMP signaling 在耳蝸發育中調控 hair cell 分化和 stereocilia polarity。SMAD4 也參與 cilia-dependent Hedgehog signaling。Centrosome 定位 + 高度 constrained + 6/6 全層 evidence。

---

### #4 — DLG4 / PSD-95（突觸後密度蛋白）⭐

| 指標 | 值 |
|------|------|
| Composite | 0.7116 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.166 (norm=0.980) — **極度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=**224.5 TPM** (極高); enrichment=**2.24**; norm=0.674 |
| Literature | 2,000 篇; sensory=**57**, cyto=319, polarity=27; tier=direct_experimental |

**解讀:** DLG4/PSD-95 是感覺神經元突觸的核心支架蛋白。在 photoreceptor ribbon synapse 和 hair cell afferent synapse 中表達。極度 LoF intolerance + 極高 cerebellum 表達 + 大量感覺文獻。

---

### #5 — CRMP1（Collapsin Response Mediator 1）⭐

| 指標 | 值 |
|------|------|
| Composite | 0.6888 |
| Evidence layers | **6/6 全層** |
| gnomAD | LOEUF=0.440 (norm=0.866) — 中高度 constrained, pLI=1.000 |
| Expression | GTEx cerebellum=**95.3 TPM**; enrichment=**2.43** (Usher 組織明顯富集); norm=0.666 |
| Localization | HPA: **Centrosome + Cytosol**; proximity=1.000 |
| Literature | 178 篇; sensory=6, cyto=33; tier=hts_hit |

**解讀:** CRMP1 參與微管組裝和 axon guidance，在感覺神經元高度表達。Cerebellum enrichment 極高（2.43）。Centrosome 定位 + 全 6 層 evidence。Under-studied（僅 178 篇）。

---

### #6 — FGFR1（FGF Receptor 1）

| 指標 | 值 |
|------|------|
| Composite | 0.6857 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.285 (norm=0.917) — **高度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=121.6 TPM; enrichment=1.31; norm=0.615 |
| Literature | 6,129 篇; cilia=35, sensory=**132**, direct_exp=8; tier=direct_experimental |

**解讀:** FGF 信號在耳蝸發育中調控 otic vesicle patterning 和 hair cell 分化。132 篇感覺 + 35 篇纖毛文獻。

---

### #7 — ATP1A3（Na⁺/K⁺ ATPase α3）

| 指標 | 值 |
|------|------|
| Composite | 0.6833 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.214 (norm=0.940) — **高度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=**346.3 TPM** (極高); enrichment=**2.40**; norm=0.680 |
| Literature | 527 篇; sensory=**78**; tier=hts_hit |

**解讀:** 神經元 Na⁺/K⁺ pump。ATP1A3 突變致 alternating hemiplegia + rapid-onset dystonia-parkinsonism，部分患者伴有**聽力損失**。在耳蝸 stria vascularis 高表達，維持 endolymph 離子梯度（聽覺轉導必需）。

---

### #8 — ATP2B2（Plasma Membrane Ca²⁺ ATPase 2）⭐

| 指標 | 值 |
|------|------|
| Composite | 0.6832 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.190 (norm=0.955) — **極度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=**164.7 TPM**; enrichment=**2.92** (最高之一); norm=0.688 |
| Literature | 180 篇; sensory=**54**; tier=hts_hit |

**解讀:** ATP2B2 是 Ca²⁺ extrusion pump。**Atp2b2 突變 (deafwaddler) 小鼠完全失聰** — 在耳蝸毛細胞 stereocilia 頂端高度表達，負責 mechanotransduction 後 Ca²⁺ 排出。極度 constrained + 最高 Usher tissue enrichment 之一（2.92）。**直接連結 stereocilia Ca²⁺ homeostasis 與聽力。**

---

### #9 — PKD1 / Polycystin-1（已知 Ciliopathy 基因 — 陽性對照）

| 指標 | 值 |
|------|------|
| Composite | 0.6831 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.360 (norm=0.836), pLI=1.000 |
| Expression | GTEx cerebellum=**577.2 TPM** (極高); enrichment=**2.54**; norm=0.685 |
| Literature | 2,521 篇; cilia=**242**, sensory=19, direct_exp=**201**; tier=direct_experimental |

**解讀:** **已知 ciliopathy 基因** — PKD1 突變致 ADPKD。Polycystin-1 是 primary cilia 上的機械感受器。242 篇纖毛文獻。Pipeline 正確排名 top 10，驗證 scoring 系統有效。

---

### #10 — ARL3（ADP-Ribosylation Factor-like 3）⭐

| 指標 | 值 |
|------|------|
| Composite | 0.6826 |
| Evidence layers | **6/6 全層** |
| gnomAD | LOEUF=0.557 (norm=0.800), pLI=0.930 |
| Expression | GTEx cerebellum=51.7 TPM; enrichment=1.04; norm=0.545 |
| Localization | HPA: **Centrosome + Nucleoplasm**; proximity=1.000 |
| Literature | 169 篇; cilia=**88**, sensory=**49**, direct_exp=**45**; tier=direct_experimental |

**解讀:** ARL3 是**已確認的纖毛信號蛋白**，調控 ciliary protein trafficking（與 RP2/UNC119 組成 lipidated cargo release 複合物）。169 篇中 88 篇纖毛文獻（**52%**）和 49 篇感覺文獻（**29%**）— 在所有候選基因中纖毛相關比例最高。ARL3 突變在小鼠致 retinal degeneration。**真正的 Usher-adjacent ciliopathy 候選基因。**

---

### #11 — GRIA2（Glutamate Receptor, AMPA 2）

| 指標 | 值 |
|------|------|
| Composite | 0.6810 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.123 (norm=0.957) — **極度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=74.4 TPM; enrichment=**2.29**; norm=0.656 |
| Literature | 1,758 篇; sensory=**87**; tier=hts_hit |

**解讀:** AMPA receptor 核心亞單位。在 cochlear nucleus 和 auditory pathway 大量表達。Hair cell afferent synapse 使用 glutamatergic transmission。極度 LoF intolerant。

---

### #12 — SNCA（α-Synuclein）

| 指標 | 值 |
|------|------|
| Composite | 0.6810 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.691 (norm=0.817) |
| Expression | GTEx cerebellum=73.9 TPM; enrichment=**2.74**; norm=0.667 |
| Literature | 4,084 篇; sensory=28, cyto=734; tier=direct_experimental |

**解讀:** Parkinson disease 相關蛋白。SNCA 在 synaptic vesicle 循環和 cytoskeleton 動態有角色。Cerebellum 高表達。主要文獻集中在 neurodegeneration。

---

### #13 — HDAC6（Histone Deacetylase 6）⭐

| 指標 | 值 |
|------|------|
| Composite | 0.6801 |
| Evidence layers | 5/6 (缺 gnomAD) |
| gnomAD | 無數據（可能因位於 chrX） |
| Expression | GTEx cerebellum=92.0 TPM; enrichment=1.08; norm=0.573 |
| Localization | HPA: Cytosol + Nucleoplasm + **Centrosome**; proximity=1.000 |
| Literature | 2,915 篇; cilia=**119**, sensory=36, direct_exp=40, cyto=605; tier=direct_experimental |

**解讀:** HDAC6 是**已知的 ciliogenesis 調控因子**。它 deacetylates α-tubulin，調控 cilia disassembly。HDAC6 抑制劑（如 tubastatin A）可以**穩定纖毛**。119 篇纖毛文獻 + centrosome 定位。在 ciliopathy 治療研究中是重要靶點。

---

### #14 — VAMP2（Synaptobrevin-2）

| 指標 | 值 |
|------|------|
| Composite | 0.6786 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.345 (norm=0.930) — **高度 constrained**, pLI=0.997 |
| Expression | GTEx cerebellum=**500.5 TPM** (極高); enrichment=**1.96**; norm=0.669 |
| Literature | 1,286 篇; sensory=24, cyto=115; tier=hts_hit |

**解讀:** SNARE 複合物核心成員，驅動 synaptic vesicle exocytosis。在 hair cell ribbon synapse 和 photoreceptor synapse 中有關鍵功能。極高 cerebellum 表達（500 TPM）。

---

### #15 — MAPRE3 / EB3（Microtubule End-Binding Protein 3）

| 指標 | 值 |
|------|------|
| Composite | 0.6769 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.163 (norm=0.948) — **極度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=**214.6 TPM** (極高); enrichment=**1.87**; norm=0.662 |
| Literature | 81 篇 (under-studied); cilia=3, sensory=1, cyto=67, direct_exp=2; tier=direct_experimental |

**解讀:** EB3 追蹤生長中的微管 plus-end，參與 cilia formation 和 axon guidance。極度 LoF intolerant + 極高 cerebellum 表達。僅 81 篇文獻 — truly under-studied。微管動態是 ciliogenesis 的基礎。

---

### #16 — ATP1B1（Na⁺/K⁺ ATPase β1 亞單位）

| 指標 | 值 |
|------|------|
| Composite | 0.6754 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.195 (norm=0.923) — **高度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=**211.4 TPM**; enrichment=**1.90**; norm=0.662 |
| Literature | 233 篇; sensory=7; tier=hts_hit |

**解讀:** Na⁺/K⁺ ATPase 的 β1 亞單位，與 ATP1A3 (#7) 和 ATP1A1 (#18) 形成功能複合物。在 stria vascularis 維持 endolymph K⁺ 濃度。聽覺轉導依賴此離子梯度。

---

### #17 — ANP32A（Acidic Nuclear Phosphoprotein 32A）

| 指標 | 值 |
|------|------|
| Composite | 0.6743 |
| Evidence layers | **6/6 全層** |
| gnomAD | LOEUF=0.143 (norm=0.947) — **極度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=55.8 TPM; enrichment=1.57; norm=0.618 |
| Localization | HPA: Nucleoplasm + **Centrosome** + Cytosol; proximity=1.000 |
| Literature | 203 篇; cilia=0, sensory=1; tier=hts_hit |

**解讀:** Histone chaperone 和 phosphatase inhibitor。Centrosome 定位有趣但纖毛/感覺文獻極少。極度 LoF intolerant 表明功能重要，但與 Usher/ciliopathy 的連結不明確。

---

### #18 — ATP1A1（Na⁺/K⁺ ATPase α1）

| 指標 | 值 |
|------|------|
| Composite | 0.6741 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.188 (norm=0.937) — **高度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=**374.6 TPM** (極高); enrichment=**1.79**; norm=0.662 |
| Literature | 667 篇; sensory=20; tier=hts_hit |

**解讀:** Na⁺/K⁺ ATPase 的 ubiquitous α 亞單位。與 ATP1A3 (#7) 和 ATP1B1 (#16) 形成 Na⁺/K⁺ pump 系統。Stria vascularis endolymph homeostasis 核心。

---

### #19 — SCN2A（Voltage-Gated Sodium Channel α2）

| 指標 | 值 |
|------|------|
| Composite | 0.6733 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.161 (norm=0.938) — **極度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=65.2 TPM; enrichment=**2.97** (最高); norm=0.670 |
| Literature | 966 篇; sensory=14; tier=direct_experimental |

**解讀:** 神經元 Na⁺ channel。SCN2A 突變致 epileptic encephalopathy。Usher tissue enrichment 最高（2.97），暗示在感覺神經元中特異性高表達。

---

### #20 — VEGFA（Vascular Endothelial Growth Factor A）

| 指標 | 值 |
|------|------|
| Composite | 0.6722 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.615 (norm=0.951) |
| Expression | GTEx cerebellum=39.4 TPM; enrichment=0.80; norm=0.473 |
| Literature | 26,240 篇; cilia=55, sensory=**2,550**; tier=direct_experimental |

**解讀:** 血管生成核心因子。2,550 篇感覺文獻（因為眼科血管新生是 VEGF 研究主題之一）。排名偏高因 annotation (0.968) + literature (0.942) 極高。與 ciliopathy 的直接連結較弱。

---

## 優先級總結

### 最高優先 — 直接纖毛/感覺機制

| 基因 | Layers | 核心理由 |
|------|--------|---------|
| **ARL3** ⭐ | 6/6 | 已確認纖毛信號蛋白。52% 文獻為纖毛相關。Centrosome 定位。Ciliary cargo transport。 |
| **PAFAH1B1** ⭐ | 6/6 | Dynein transport 核心。極度 LoF intolerant (LOEUF=0.10)。Centrosome 定位。 |
| **DYNC1H1** ⭐ | 6/6 | Dynein 重鏈。極度 LoF intolerant (LOEUF=0.12)。Centrosome 定位。纖毛逆行運輸。 |
| **ATP2B2** ⭐ | 5/6 | Atp2b2 突變小鼠失聰。stereocilia Ca²⁺ pump。極度 constrained。Enrichment=2.92。 |
| **HDAC6** ⭐ | 5/6 | 已知 ciliogenesis 調控因子。119 篇纖毛文獻。Centrosome 定位。治療靶點。 |

### 高優先 — 強多層證據 + 感覺系統角色

| 基因 | Layers | 核心理由 |
|------|--------|---------|
| **DLG4** ⭐ | 5/6 | 感覺突觸核心支架。極度 LoF intolerant。cerebellum 225 TPM。 |
| **SMAD4** ⭐ | 6/6 | TGF-β/BMP 核心。Hair cell 分化和 Hedgehog signaling。Centrosome 定位。 |
| **CRMP1** ⭐ | 6/6 | Under-studied centrosome 蛋白。Usher tissue enrichment=2.43。微管組裝。 |
| **MAPRE3** | 5/6 | 微管 plus-end tracker。極度 LoF intolerant。Under-studied (81 篇)。 |
| **ATP1A3** | 5/6 | Na⁺/K⁺ pump。部分患者有聽力損失。Stria vascularis 表達。 |

### 中優先 — 間接但有潛力

| 基因 | Layers | 核心理由 |
|------|--------|---------|
| **FGFR1** | 5/6 | FGF 信號調控 hair cell 分化。132 篇感覺文獻。 |
| **GRIA2** | 5/6 | AMPA receptor。Hair cell glutamatergic transmission。 |
| **VAMP2** | 5/6 | SNARE 蛋白。Ribbon synapse exocytosis。cerebellum 500 TPM。 |
| **ATP1B1 / ATP1A1** | 5/6 | Na⁺/K⁺ pump 系統。Endolymph K⁺ homeostasis。 |

### 陽性對照

| 基因 | Rank | 已知疾病 |
|------|------|---------|
| **PKD1** | #9 | ADPKD (242 篇纖毛文獻) |

---

## 建議下一步

1. **ARL3**: 調查 ARL3 突變小鼠是否有聽力/視力表型；檢查 photoreceptor connecting cilium proteomics
2. **ATP2B2**: 查詢 Usher 患者 cohort 中 ATP2B2 variants；deafwaddler 模型是否有視網膜表型
3. **HDAC6**: 評估 HDAC6 抑制劑對 Usher ciliopathy 模型的治療潛力
4. **PAFAH1B1 / DYNC1H1**: 調查 lissencephaly 患者是否有亞臨床聽力/視力退化
5. **MAPRE3**: 極度 under-studied (81 篇) + 極度 LoF intolerant — 值得在 inner ear organoid 中驗證
6. 補齊 **CellxGene** 單細胞數據以提升 retina/inner ear 組織特異性判斷
