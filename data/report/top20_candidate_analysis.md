# TOP 20 Usher 候選基因分析（完整 6 層證據）

**Pipeline Version:** 0.1.0
**Generated:** 2026-02-16 (v5 — gene_symbol deduplication 修正後最終版)
**Scoring Layers:** gnomAD constraint (0.20) + Expression (0.20) + Annotation (0.15) + Localization (0.15) + Animal Model (0.15) + Literature (0.15)
**Coverage:** gnomAD 91.5% | Expression 96.1% | Annotation 98.9% | Localization 66.1% | Animal Model 97.9% | Literature 100%
**Tier Statistics:** HIGH: 4 | MEDIUM: 8,051 | LOW: 10,188 | Total: 18,243 (from 19,555 unique genes)
**Validation:** PASSED — CDH23 98.3rd percentile, median known gene 83.3%

---

## 方法論

### 計分公式
```
composite_score = weighted_sum / available_weight
```
其中 `available_weight` 只計算有數據（非 NULL）的 evidence layer 權重。

### v4 修正：gene_symbol 去重
`gene_universe` 中 1,539 個 gene_symbol 對應多個 Ensembl ID（共 3,033 個多餘 ID）。非 canonical ID 在部分 evidence table 中缺少數據，導致分數被 `weighted_sum/available_weight` 膨脹。例如：

| Gene | Ensembl ID | Layers | Score | 原因 |
|------|-----------|--------|-------|------|
| CACNA1C | ENSG00000285479 (non-canonical) | 3/6 | **0.8830** | 缺 expression/animal → 分母小 |
| CACNA1C | ENSG00000151067 (canonical) | 5/6 | 0.6334 | 有完整數據 → 真實分數 |

修正：在 `compute_composite_scores()` 中，對每個 gene_symbol 保留 `evidence_count` 最多的 Ensembl ID（相同 evidence_count 取 composite_score 最高者）。去重後 22,604 → 19,555 genes。

---

## Top 20 候選基因總覽

| # | Gene | Score | Layers | Tier | gnomAD | Expr | Annot | Local | Lit |
|---|------|-------|--------|------|--------|------|-------|-------|-----|
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

> **去重後 top 20 全部有 5-6 層 evidence，expression 層不再缺失。** 前 4 名（PAFAH1B1、DYNC1H1、SMAD4、DLG4）全是 LoF-intolerant 基因且有 centrosome/sensory 相關定位或文獻。

---

## 逐基因詳細分析

### #1 — PAFAH1B1 / LIS1（Dynein 調控因子）

**6/6 全層 | LOEUF=0.100 | pLI=1.000 | Centrosome**

| 指標 | 值 |
|------|------|
| gnomAD | LOEUF=0.100 (norm=0.969) — **極度 LoF intolerant (top 1%)** |
| Expression | GTEx cerebellum=131.0 TPM; enrichment=1.17; norm=0.597 |
| Localization | HPA: **Centrosome**; proximity=1.000 |
| Literature | 496 篇; cilia=4, sensory=3, direct_exp=4, cyto=**424**; tier=direct_experimental |

LIS1 是 cytoplasmic dynein 的關鍵調控因子，控制微管 minus-end transport。Dynein 負責 IFT（intraflagellar transport）逆行運輸——纖毛維持的核心機制。LIS1 突變致 lissencephaly（無腦回畸形）。與 Usher 的連結：**dynein transport 對感覺纖毛（photoreceptor connecting cilium、stereocilia kinocilium）至關重要**。6/6 全層 + 極度 constrained + centrosome 定位，是最強候選之一。

---

### #2 — DYNC1H1（Cytoplasmic Dynein 重鏈）

**6/6 全層 | LOEUF=0.117 | pLI=1.000 | Centrosome + Cytosol**

| 指標 | 值 |
|------|------|
| gnomAD | LOEUF=0.117 (norm=0.966) — **極度 LoF intolerant** |
| Expression | GTEx cerebellum=129.1 TPM; enrichment=1.68; norm=0.648 |
| Localization | HPA: **Centrosome + Cytosol**; proximity=1.000 |
| Literature | 211 篇; cilia=**10**, sensory=**9**, direct_exp=6; tier=direct_experimental |

Dynein 重鏈——分子馬達的催化核心，驅動 IFT retrograde transport 和中心粒遷移。DYNC1H1 突變致 cortical malformation 和 spinal muscular atrophy。**纖毛中 dynein 運輸缺陷是多種 ciliopathy 的核心病理**，連結 photoreceptor disc renewal 和 hair cell 功能。纖毛+感覺文獻占比 9%（19/211），在非纖毛基因中比例很高。

---

### #3 — SMAD4（TGF-β/BMP 核心轉錄因子）

**6/6 全層 | LOEUF=0.227 | pLI=1.000 | Centrosome**

| 指標 | 值 |
|------|------|
| gnomAD | LOEUF=0.227 (norm=0.932) — **高度 LoF intolerant** |
| Expression | GTEx cerebellum=28.8 TPM; enrichment=1.10; norm=0.529 |
| Localization | HPA: Cytosol + Nucleoplasm + **Centrosome**; proximity=1.000 |
| Literature | 6,577 篇; cilia=6, sensory=**78**, polarity=**49**; tier=direct_experimental |

TGF-β/BMP 信號通路的核心介導者。BMP signaling 在耳蝸發育中調控 hair cell 分化和 stereocilia polarity。SMAD4 也參與 cilia-dependent **Hedgehog signaling**。Centrosome 定位 + 高度 constrained + 78 篇感覺 + 49 篇 polarity 文獻。

---

### #4 — DLG4 / PSD-95（突觸後密度蛋白）

**5/6（缺 localization）| LOEUF=0.166 | pLI=1.000**

| 指標 | 值 |
|------|------|
| gnomAD | LOEUF=0.166 (norm=**0.980**) — **極度 LoF intolerant**, gnomAD norm top 20 最高 |
| Expression | GTEx cerebellum=**224.5 TPM** (極高); enrichment=**2.24**; norm=0.674 |
| Literature | 2,000 篇; sensory=**57**, cyto=319, polarity=27; tier=direct_experimental |

DLG4/PSD-95 是感覺神經元突觸的核心支架蛋白。在 photoreceptor ribbon synapse 和 hair cell afferent synapse 中表達。極度 LoF intolerance + 極高 cerebellum 表達 + 大量感覺文獻。

---

### #5 — CRMP1（Collapsin Response Mediator 1）

**6/6 全層 | LOEUF=0.440 | pLI=1.000 | Centrosome**

| 指標 | 值 |
|------|------|
| gnomAD | LOEUF=0.440 (norm=0.866) — 中高度 constrained |
| Expression | GTEx cerebellum=**95.3 TPM**; enrichment=**2.43** (Usher 組織富集); norm=0.666 |
| Localization | HPA: **Centrosome + Cytosol**; proximity=1.000 |
| Literature | 178 篇 (under-studied); sensory=6, cyto=33; tier=hts_hit |

微管組裝和 axon guidance 蛋白。Cerebellum enrichment 在 top 20 中排名前列（2.43）。僅 178 篇文獻 — truly under-studied。微管動態 + centrosome 定位 + 全 6 層 evidence。

---

### #6 — FGFR1（FGF Receptor 1）

**5/6（缺 localization）| LOEUF=0.285 | pLI=1.000**

| 指標 | 值 |
|------|------|
| gnomAD | LOEUF=0.285 (norm=0.917) — **高度 LoF intolerant** |
| Expression | GTEx cerebellum=121.6 TPM; enrichment=1.31; norm=0.615 |
| Literature | 6,129 篇; cilia=**35**, sensory=**132**, direct_exp=8; tier=direct_experimental |

FGF 信號在耳蝸發育中調控 otic vesicle patterning 和 hair cell 分化。FGFR1 也參與 ciliogenesis 調控。132 篇感覺 + 35 篇纖毛文獻，在非纖毛基因中數字很高。

---

### #7 — ATP1A3（Na+/K+ ATPase α3）

**5/6（缺 localization）| LOEUF=0.214 | pLI=1.000**

| 指標 | 值 |
|------|------|
| gnomAD | LOEUF=0.214 (norm=0.940) — **高度 LoF intolerant** |
| Expression | GTEx cerebellum=**346.3 TPM** (極高); enrichment=**2.40**; norm=0.680 |
| Literature | 527 篇; sensory=**78**; tier=hts_hit |

神經元 Na+/K+ pump。ATP1A3 突變致 alternating hemiplegia + rapid-onset dystonia-parkinsonism，**部分患者伴有聽力損失**。在耳蝸 stria vascularis 高表達，維持 endolymph 離子梯度——聽覺轉導必需。

---

### #8 — ATP2B2（Plasma Membrane Ca2+ ATPase 2）

**5/6（缺 localization）| LOEUF=0.190 | pLI=1.000**

| 指標 | 值 |
|------|------|
| gnomAD | LOEUF=0.190 (norm=0.955) — **極度 LoF intolerant** |
| Expression | GTEx cerebellum=**164.7 TPM**; enrichment=**2.92** (top 20 最高); norm=0.688 |
| Literature | 180 篇; sensory=**54**; tier=hts_hit |

Ca2+ extrusion pump。**Atp2b2 突變（deafwaddler）小鼠完全失聰。** 在耳蝸毛細胞 stereocilia 頂端高度表達，負責 mechanotransduction 後 Ca2+ 排出。極度 constrained + Usher tissue enrichment 最高（2.92）。**直接連結 stereocilia Ca2+ homeostasis 與聽力退化。**

---

### #9 — PKD1 / Polycystin-1（已知 Ciliopathy — 陽性對照）

**5/6（缺 localization）| LOEUF=0.360 | pLI=1.000**

| 指標 | 值 |
|------|------|
| gnomAD | LOEUF=0.360 (norm=0.836) |
| Expression | GTEx cerebellum=**577.2 TPM** (top 20 最高); enrichment=**2.54**; norm=0.685 |
| Literature | 2,521 篇; cilia=**242**, direct_exp=**201**; tier=direct_experimental |

**已知 ciliopathy 基因。** PKD1 突變致 autosomal dominant polycystic kidney disease。Polycystin-1 是 primary cilia 上的機械感受器。Pipeline 正確排在 #9，**驗證 scoring 系統有效**。

---

### #10 — ARL3（ADP-Ribosylation Factor-like 3）

**6/6 全層 | LOEUF=0.557 | pLI=0.930 | Centrosome**

| 指標 | 值 |
|------|------|
| gnomAD | LOEUF=0.557 (norm=0.800) |
| Expression | GTEx cerebellum=51.7 TPM; enrichment=1.04; norm=0.545 |
| Localization | HPA: **Centrosome + Nucleoplasm**; proximity=1.000 |
| Literature | 169 篇; cilia=**88 (52%)**, sensory=**49 (29%)**, direct_exp=**45**; tier=direct_experimental |

**已確認的纖毛信號蛋白。** ARL3 調控 ciliary protein trafficking，與 RP2/UNC119 組成 lipidated cargo release 複合物。169 篇中 88 篇纖毛文獻（**52%**）— 所有候選基因中纖毛相關比例最高。ARL3 突變在小鼠致 retinal degeneration。**真正的 Usher-adjacent ciliopathy 候選。**

---

### #11 — GRIA2（Glutamate Receptor, AMPA 2）

**5/6（缺 localization）| LOEUF=0.123 | pLI=1.000**

| 指標 | 值 |
|------|------|
| gnomAD | LOEUF=0.123 (norm=0.957) — **極度 LoF intolerant** |
| Expression | GTEx cerebellum=74.4 TPM; enrichment=**2.29**; norm=0.656 |
| Literature | 1,758 篇; sensory=**87**; tier=hts_hit |

AMPA receptor 核心亞單位。在 cochlear nucleus 和 auditory pathway 大量表達。Hair cell afferent synapse 使用 glutamatergic transmission。極度 LoF intolerant（LOEUF=0.123）。

---

### #12 — SNCA（α-Synuclein）

**5/6（缺 localization）| LOEUF=0.691**

| 指標 | 值 |
|------|------|
| gnomAD | LOEUF=0.691 (norm=0.817) |
| Expression | GTEx cerebellum=73.9 TPM; enrichment=**2.74**; norm=0.667 |
| Literature | 4,084 篇; sensory=28, cyto=**734**; tier=direct_experimental |

Parkinson disease 相關蛋白。在 synaptic vesicle 循環和 cytoskeleton 動態有角色。Cerebellum 高表達。主要文獻集中在 neurodegeneration 而非 ciliopathy。

---

### #13 — HDAC6（Histone Deacetylase 6）

**5/6（缺 gnomAD）| Centrosome**

| 指標 | 值 |
|------|------|
| gnomAD | 無數據（可能因位於 chrX） |
| Expression | GTEx cerebellum=92.0 TPM; enrichment=1.08; norm=0.573 |
| Localization | HPA: Cytosol + Nucleoplasm + **Centrosome**; proximity=1.000 |
| Literature | 2,915 篇; cilia=**119**, sensory=36, direct_exp=40, cyto=**605**; tier=direct_experimental |

**已知的 ciliogenesis 調控因子。** HDAC6 deacetylates α-tubulin，調控 cilia disassembly。HDAC6 抑制劑（tubastatin A）可以**穩定纖毛**。119 篇纖毛文獻 + centrosome 定位。在 ciliopathy **治療研究**中是重要靶點。

---

### #14 — VAMP2 / Synaptobrevin-2

**5/6（缺 localization）| LOEUF=0.345 | pLI=0.997**

| 指標 | 值 |
|------|------|
| gnomAD | LOEUF=0.345 (norm=0.930) — **高度 constrained** |
| Expression | GTEx cerebellum=**500.5 TPM** (極高); enrichment=**1.96**; norm=0.669 |
| Literature | 1,286 篇; sensory=24, cyto=115; tier=hts_hit |

SNARE 複合物核心成員，驅動 synaptic vesicle exocytosis。在 hair cell ribbon synapse 和 photoreceptor synapse 中有關鍵功能。Cerebellum 500 TPM 是 top 20 中第二高（僅次 PKD1 的 577）。

---

### #15 — MAPRE3 / EB3（Microtubule End-Binding Protein 3）

**5/6（缺 localization）| LOEUF=0.163 | pLI=1.000**

| 指標 | 值 |
|------|------|
| gnomAD | LOEUF=0.163 (norm=0.948) — **極度 LoF intolerant** |
| Expression | GTEx cerebellum=**214.6 TPM** (極高); enrichment=**1.87**; norm=0.662 |
| Literature | 81 篇 (under-studied); cilia=3, cyto=67, direct_exp=2; tier=direct_experimental |

EB3 追蹤生長中的微管 plus-end，參與 cilia formation 和 axon guidance。**極度 LoF intolerant + 極高 cerebellum 表達 + 僅 81 篇文獻 — truly under-studied。** 微管動態是 ciliogenesis 的基礎。

---

### #16 — ATP1B1（Na+/K+ ATPase β1 亞單位）

**5/6（缺 localization）| LOEUF=0.195 | pLI=1.000**

| 指標 | 值 |
|------|------|
| gnomAD | LOEUF=0.195 (norm=0.923) — **高度 LoF intolerant** |
| Expression | GTEx cerebellum=**211.4 TPM**; enrichment=**1.90**; norm=0.662 |
| Literature | 233 篇; sensory=7; tier=hts_hit |

Na+/K+ ATPase 的 β1 亞單位，與 ATP1A3 (#7) 和 ATP1A1 (#18) 形成功能複合物。在 stria vascularis 維持 endolymph K+ 濃度。聽覺轉導依賴此離子梯度。

---

### #17 — ANP32A（Acidic Nuclear Phosphoprotein 32A）

**6/6 全層 | LOEUF=0.143 | pLI=1.000 | Centrosome**

| 指標 | 值 |
|------|------|
| gnomAD | LOEUF=0.143 (norm=0.947) — **極度 LoF intolerant** |
| Expression | GTEx cerebellum=55.8 TPM; enrichment=1.57; norm=0.618 |
| Localization | HPA: Nucleoplasm + **Centrosome** + Cytosol; proximity=1.000 |
| Literature | 203 篇; cilia=0, sensory=1; tier=hts_hit |

Histone chaperone 和 phosphatase inhibitor。極度 LoF intolerant + Centrosome 定位。但纖毛/感覺文獻極少（cilia=0），與 Usher/ciliopathy 的直接連結不明確。6/6 全層但排名不高是因為個別層分數相對低。

---

### #18 — ATP1A1（Na+/K+ ATPase α1）

**5/6（缺 localization）| LOEUF=0.188 | pLI=1.000**

| 指標 | 值 |
|------|------|
| gnomAD | LOEUF=0.188 (norm=0.937) — **高度 LoF intolerant** |
| Expression | GTEx cerebellum=**374.6 TPM** (極高); enrichment=**1.79**; norm=0.662 |
| Literature | 667 篇; sensory=20; tier=hts_hit |

Na+/K+ ATPase 的 ubiquitous α 亞單位。與 ATP1A3 (#7) 和 ATP1B1 (#16) 共同組成 Na+/K+ pump 系統。三個亞單位都在 top 20，顯示 **stria vascularis endolymph homeostasis 是一個 convergent signal**。

---

### #19 — SCN2A（Voltage-Gated Sodium Channel α2）

**5/6（缺 localization）| LOEUF=0.161 | pLI=1.000**

| 指標 | 值 |
|------|------|
| gnomAD | LOEUF=0.161 (norm=0.938) — **極度 LoF intolerant** |
| Expression | GTEx cerebellum=65.2 TPM; enrichment=**2.97** (**top 20 最高**); norm=0.670 |
| Literature | 966 篇; sensory=14; tier=direct_experimental |

神經元 Na+ channel。SCN2A 突變致 epileptic encephalopathy。Usher tissue enrichment 在 top 20 中最高（2.97），暗示在感覺神經元中特異性極高。極度 LoF intolerant。

---

### #20 — VEGFA（Vascular Endothelial Growth Factor A）

**5/6（缺 localization）| LOEUF=0.615**

| 指標 | 值 |
|------|------|
| gnomAD | LOEUF=0.615 (norm=0.951) |
| Expression | GTEx cerebellum=39.4 TPM; enrichment=0.80; norm=0.473 |
| Literature | 26,240 篇; cilia=55, sensory=**2,550**; tier=direct_experimental |

血管生成核心因子。2,550 篇感覺文獻主要來自眼科血管新生研究（AMD/DR 是 VEGF 研究主題）。Annotation (0.968) + literature (0.942) 極高推動排名。與 ciliopathy 的直接連結較弱。

---

## 優先級總結

### Tier 1 — 直接纖毛/感覺機制

| 基因 | Layers | LOEUF | 核心理由 |
|------|--------|-------|---------|
| **ARL3** | 6/6 | 0.557 | 已確認纖毛信號蛋白。52% 文獻為纖毛相關。Ciliary cargo transport。小鼠 retinal degeneration。 |
| **PAFAH1B1** | 6/6 | 0.100 | Dynein transport 核心。極度 LoF intolerant。Centrosome 定位。IFT 核心機制。 |
| **DYNC1H1** | 6/6 | 0.117 | Dynein 重鏈。極度 LoF intolerant。Centrosome 定位。纖毛逆行運輸。 |
| **ATP2B2** | 5/6 | 0.190 | deafwaddler 小鼠失聰。stereocilia Ca2+ pump。極度 constrained。Enrichment=2.92。 |
| **HDAC6** | 5/6 | — | 已知 ciliogenesis 調控因子。119 篇纖毛文獻。Centrosome 定位。治療靶點。 |

### Tier 2 — 強多層證據 + 感覺系統角色

| 基因 | Layers | LOEUF | 核心理由 |
|------|--------|-------|---------|
| **DLG4** | 5/6 | 0.166 | 感覺突觸支架。gnomAD norm 0.980（最高）。cerebellum 225 TPM。 |
| **SMAD4** | 6/6 | 0.227 | TGF-β/BMP 核心。Hair cell 分化 + Hedgehog signaling。Centrosome。 |
| **CRMP1** | 6/6 | 0.440 | Under-studied (178 篇)。Centrosome。Usher enrichment=2.43。微管組裝。 |
| **MAPRE3** | 5/6 | 0.163 | 微管 plus-end tracker。Under-studied (81 篇)。極度 LoF intolerant。cerebellum 215 TPM。 |
| **ATP1A3** | 5/6 | 0.214 | Na+/K+ pump。部分患者有聽力損失。cerebellum 346 TPM。 |

### Tier 3 — 間接但有趣的 convergent signals

| 基因 | 核心理由 |
|------|---------|
| **ATP1A3 + ATP1B1 + ATP1A1** | Na+/K+ pump 三亞單位全在 top 20 → stria vascularis endolymph 是 convergent signal |
| **FGFR1** | FGF 信號 hair cell 分化。132 篇感覺文獻。 |
| **VAMP2** | Ribbon synapse SNARE。cerebellum 500 TPM。 |
| **SCN2A** | Usher tissue enrichment 2.97（最高）。epilepsy gene 可能有亞臨床聽力表型。 |

### 陽性對照

**PKD1** 排 #9（2,521 篇文獻，242 篇纖毛），驗證 scoring 系統正確識別已知 ciliopathy 基因。

---

## 關鍵觀察

1. **Dynein 系統突出**：PAFAH1B1 (#1) + DYNC1H1 (#2) 分占前兩名，暗示 IFT retrograde transport 是 pipeline 識別的最強 ciliopathy 信號
2. **Na+/K+ pump 系統收斂**：ATP1A3 (#7) + ATP1B1 (#16) + ATP1A1 (#18) 三個亞單位同時出現，指向 stria vascularis endolymph homeostasis 作為聽力退化的獨立機制
3. **ARL3 是最佳新候選**：已確認纖毛蛋白但尚未與 Usher 連結，52% 文獻纖毛相關，有 retinal degeneration 小鼠表型
4. **MAPRE3 是最 under-studied 的高分基因**：僅 81 篇文獻，極度 LoF intolerant，cerebellum 215 TPM

---

## 建議下一步

1. **ARL3**: 調查 ARL3 突變小鼠是否有聽力/視力表型；檢查 photoreceptor connecting cilium proteomics
2. **ATP2B2**: 查詢 Usher 患者 cohort 中 ATP2B2 variants；deafwaddler 模型是否有視網膜表型
3. **HDAC6**: 評估 HDAC6 抑制劑對 Usher ciliopathy 模型的治療潛力
4. **PAFAH1B1 / DYNC1H1**: 調查 lissencephaly 患者是否有亞臨床聽力/視力退化
5. **MAPRE3**: 極度 under-studied (81 篇) + 極度 LoF intolerant — 值得在 inner ear organoid 中驗證
6. 補齊 **CellxGene** 單細胞數據以提升 retina/inner ear 組織特異性判斷
