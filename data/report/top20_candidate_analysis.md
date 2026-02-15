# TOP 20 Usher 候選基因分析（完整 6 層證據）

**Pipeline Version:** 0.1.0
**Generated:** 2026-02-16 (v3 — gnomAD gene_symbol fallback 修正後)
**Scoring Layers:** gnomAD constraint (0.20) + Expression (0.20) + Annotation (0.15) + Localization (0.15) + Animal Model (0.15) + Literature (0.15)
**Coverage:** gnomAD 93.8% | Expression 99.3% | Annotation 99.3% | Localization 99.3% | Animal Model 99.3% | Literature 99.3%
**Tier Statistics:** HIGH: 82 | MEDIUM: 9,626 | LOW: 11,469 | Total: 21,177 (18,328 unique gene_symbols)

---

## 方法論注意事項

### 計分公式
```
composite_score = weighted_sum / available_weight
```
其中 `available_weight` 只計算有數據（非 NULL）的 evidence layer 權重。

### 已知偏差
只有 3 層數據的基因（如 gnomAD + annotation + literature），若每層分數都高，`composite_score` 會被膨脹（因為分母 `available_weight` 只有 0.50 而非 1.00）。因此本報告**同時呈現兩個排名**：
1. **≥3 層 raw composite** — 數學上最高分，但可能包含 3 層膨脹的基因
2. **≥4 層 balanced composite** — 更可靠的多證據支持排名

---

## Part A: Raw Top 20（≥3 Evidence Layers）

| Rank | Gene | Composite | Layers | gnomAD | Annotation | Literature | Expression | Localization |
|------|------|-----------|--------|--------|------------|------------|------------|--------------|
| 1 | CACNA1C | 0.8830 | 3/6 | 0.929 | 0.862 | 0.843 | — | — |
| 2 | TNF | 0.8676 | 3/6 | 0.718 | 0.992 | 0.943 | — | — |
| 3 | ZAP70 | 0.8214 | 3/6 | 0.740 | 0.861 | 0.890 | — | — |
| 4 | COL11A2 | 0.8025 | 3/6 | 0.771 | 0.802 | 0.845 | — | — |
| 5 | C4B | 0.7987 | 3/6 | 0.809 | 0.816 | 0.768 | — | — |
| 6 | SLC2A4 | 0.7856 | 3/6 | 0.625 | 0.879 | 0.905 | — | — |
| 7 | NDE1 | 0.7812 | 3/6 | 0.653 | 0.835 | 0.898 | — | — |
| 8 | CRHR1 | 0.7762 | 3/6 | 0.686 | 0.830 | 0.844 | — | — |
| 9 | **DLG5** | **0.7681** | **4/6** | 0.858 | 0.841 | 0.843 | — | 0.500 |
| 10 | LTA | 0.7643 | 3/6 | 0.631 | 0.822 | 0.884 | — | — |
| 11 | OTOA | 0.7588 | 3/6 | 0.743 | 0.713 | 0.826 | — | — |
| 12 | **LRP6** | **0.7577** | **4/6** | 0.882 | 0.872 | 0.901 | 0.428 | — |
| 13 | MICA | 0.7567 | 3/6 | 0.621 | 0.807 | 0.888 | — | — |
| 14 | MUC2 | 0.7567 | 3/6 | 0.637 | 0.747 | 0.925 | — | — |
| 15 | CNTNAP2 | 0.7512 | 3/6 | 0.652 | 0.848 | 0.787 | — | — |
| 16 | GREM1 | 0.7492 | 3/6 | 0.583 | 0.870 | 0.851 | — | — |
| 17 | C2 | 0.7455 | 3/6 | 0.556 | 0.804 | 0.939 | — | — |
| 18 | STRA6 | 0.7453 | 3/6 | 0.654 | 0.833 | 0.779 | — | — |
| 19 | PIWIL1 | 0.7447 | 3/6 | 0.640 | 0.831 | 0.798 | — | — |
| 20 | TBCD | 0.7437 | 3/6 | 0.638 | 0.811 | 0.818 | — | — |

> **觀察:** 20 基因中有 18 個只有 3 層（gnomAD + annotation + literature），缺少 expression、localization、animal model。分數膨脹效應明顯。生物意義上需以 Part B 為主要參考。

### Raw Top 20 中值得注意的基因

- **NDE1** (#7): 雖然只有 3 層，但 NDE1 是 dynein 調控因子，12 篇纖毛文獻，5 篇直接實驗。與 PAFAH1B1/LIS1 功能相關（共同調控 cortical neuronal migration via dynein）。LOEUF=0.851 中度 constrained。
- **OTOA** (#11): Otoancorin，45 篇感覺系統文獻，在耳蝸 tectorial membrane attachment 有已知功能。與聽力損失高度相關。
- **STRA6** (#18): 視黃醇受體，29 篇感覺文獻。STRA6 突變致 Matthew-Wood syndrome（眼睛發育異常），與視網膜功能直接相關。
- **TBCD** (#20): Tubulin folding cofactor D，參與微管動態。Cerebellum 38.2 TPM，有纖毛功能潛力。

---

## Part B: Balanced Top 20（≥4 Evidence Layers）— 主要分析

| Rank | Gene | Composite | Layers | gnomAD | Expr | Annot | Local | Animal | Lit |
|------|------|-----------|--------|--------|------|-------|-------|--------|-----|
| 1 | DLG5 | 0.7681 | 4/6 | 0.858 | — | 0.841 | 0.500 | — | 0.843 |
| 2 | LRP6 | 0.7577 | 4/6 | 0.882 | 0.428 | 0.872 | — | — | 0.901 |
| 3 | **PAFAH1B1** | **0.7414** | **6/6** | 0.969 | 0.597 | 0.832 | 1.000 | 0.000 | 0.927 |
| 4 | CHRNA7 | 0.7394 | 4/6 | 0.477 | 0.436 | 0.866 | — | — | 0.895 |
| 5 | **DYNC1H1** | **0.7344** | **6/6** | 0.960 | 0.648 | 0.834 | 1.000 | 0.000 | 0.902 |
| 6 | **SMAD4** | **0.7227** | **6/6** | 0.904 | 0.529 | 0.897 | 1.000 | 0.000 | 0.921 |
| 7 | DLG4 | 0.7116 | 5/6 | 0.935 | 0.674 | 0.857 | — | 0.000 | 0.924 |
| 8 | CETN2 | 0.7006 | 4/6 | — | 0.396 | 0.828 | 1.000 | — | 0.888 |
| 9 | DLL1 | 0.6914 | 4/6 | 0.899 | 0.280 | 0.865 | 0.000 | — | 0.875 |
| 10 | **CRMP1** | **0.6888** | **6/6** | 0.795 | 0.666 | 0.767 | 1.000 | 0.000 | 0.754 |
| 11 | FGFR1 | 0.6857 | 5/6 | 0.874 | 0.615 | 0.888 | — | 0.000 | 0.926 |
| 12 | ATP1A3 | 0.6833 | 5/6 | 0.911 | 0.680 | 0.816 | — | 0.000 | 0.860 |
| 13 | **ATP2B2** | **0.6832** | **5/6** | 0.923 | 0.688 | 0.826 | — | 0.000 | 0.838 |
| 14 | PKD1 | 0.6831 | 5/6 | 0.836 | 0.685 | 0.876 | — | 0.000 | 0.930 |
| 15 | **ARL3** | **0.6826** | **6/6** | 0.736 | 0.545 | 0.804 | 1.000 | 0.000 | 0.923 |
| 16 | GRIA2 | 0.6810 | 5/6 | 0.957 | 0.656 | 0.853 | — | 0.000 | 0.877 |
| 17 | SNCA | 0.6810 | 5/6 | 0.667 | 0.667 | 0.857 | — | 0.000 | 0.932 |
| 18 | HDAC6 | 0.6801 | 5/6 | — | 0.573 | 0.887 | 1.000 | 0.000 | 0.934 |
| 19 | VAMP2 | 0.6786 | 5/6 | 0.844 | 0.669 | 0.864 | — | 0.000 | 0.838 |
| 20 | TRIM71 | 0.6771 | 4/6 | 0.880 | 0.113 | 0.867 | 0.300 | — | 0.632 |

---

## 逐基因詳細分析（Part B 排序）

### #1 — DLG5（Discs Large 5）

| 指標 | 值 |
|------|------|
| Composite | 0.7681 |
| Evidence layers | 4/6 (gnomAD + annotation + localization + literature) |
| gnomAD | LOEUF=0.333 (norm=0.858) — **高度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=15.1 TPM, testis=18.6 TPM; enrichment=0.70 (未計入 scoring) |
| Localization | HPA: **Cell Junctions**; proximity=0.500 |
| Literature | 168 篇; cilia=3, sensory=2, polarity=**17**, direct_exp=2; tier=direct_experimental |

**解讀:** DLG5 是 Scribble 極性複合物相關蛋白，調控 apicobasal polarity 和 cell junction 形成。Planar cell polarity (PCP) 信號是耳蝸毛細胞 stereocilia bundle 正確排列的關鍵。DLG5 突變小鼠有 neural tube defect。Cell junction 定位暗示其在感覺上皮 tight junction 維持中的角色。

---

### #2 — LRP6（Wnt Co-receptor）

| 指標 | 值 |
|------|------|
| Composite | 0.7577 |
| Evidence layers | 4/6 (gnomAD + expression + annotation + literature) |
| gnomAD | LOEUF=0.270 (norm=0.882) — **高度 constrained**, pLI=1.000 |
| Expression | GTEx cerebellum=11.1 TPM, testis=7.8 TPM; enrichment=0.90; norm=0.428 |
| Localization | 無 HPA 定位數據 |
| Literature | 1,557 篇; cilia=13, sensory=35, polarity=**44**, direct_exp=3; tier=direct_experimental |

**解讀:** LRP6 是 canonical Wnt 信號的共受體。**Wnt/PCP 信號通路對耳蝸毛細胞的平面細胞極性（stereocilia bundle 朝向）至關重要。** Wnt 信號也參與 ciliogenesis 調控。44 篇 polarity 文獻中有部分涉及 cochlear convergent extension。高度 constrained + 纖毛/感覺文獻使其成為值得深入研究的候選。

---

### #3 — PAFAH1B1 / LIS1（Dynein 調控因子）⭐

| 指標 | 值 |
|------|------|
| Composite | 0.7414 |
| Evidence layers | **6/6 全層** |
| gnomAD | LOEUF=0.100 (norm=0.969) — **極度 LoF intolerant (top 1%)**, pLI=1.000 |
| Expression | GTEx cerebellum=131.0 TPM; enrichment=1.17; norm=0.597 |
| Localization | HPA: **Centrosome**; proximity=1.000 |
| Animal Model | Mouse: Pafah1b1, Zebrafish: pafah1b1b (phenotype score=0) |
| Literature | 496 篇; cilia=4, sensory=3, direct_exp=4, cyto=424; tier=direct_experimental |

**解讀:** LIS1 是 cytoplasmic dynein 的關鍵調控因子，控制微管 minus-end transport。Dynein 負責 IFT（intraflagellar transport）逆行運輸，是纖毛維持的核心機制。LIS1 突變致 lissencephaly（無腦回畸形），極度 LoF intolerant 表明該基因不可或缺。與 Usher 的連結在於 **dynein transport 對感覺纖毛（photoreceptor connecting cilium、stereocilia kinocilium）至關重要**。6/6 全層 evidence 中 centrosome 定位尤為關鍵。

---

### #4 — CHRNA7（菸鹼型乙醯膽鹼受體 α7）

| 指標 | 值 |
|------|------|
| Composite | 0.7394 |
| Evidence layers | 4/6 (gnomAD + expression + annotation + literature) |
| gnomAD | LOEUF=1.064 (norm=0.477) — 不 constrained |
| Expression | GTEx cerebellum=0.09 TPM (低); enrichment=1.27; norm=0.436 |
| Localization | 無 HPA 定位數據 |
| Literature | 2,051 篇; cilia=8, sensory=21, hts=21; tier=direct_experimental |

**解讀:** CHRNA7 在 cochlear efferent 突觸和聽覺通路中有角色。分數偏高主要因 annotation (0.866) + literature (0.895) 都高。gnomAD 不 constrained 降低了其作為 essential gene 的可能性。缺少 localization 數據。優先級中等。

---

### #5 — DYNC1H1（Cytoplasmic Dynein 重鏈）⭐

| 指標 | 值 |
|------|------|
| Composite | 0.7344 |
| Evidence layers | **6/6 全層** |
| gnomAD | LOEUF=0.117 (norm=0.960) — **極度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=129.1 TPM; enrichment=1.68; norm=0.648 |
| Localization | HPA: **Centrosome + Cytosol**; proximity=1.000 |
| Animal Model | Mouse: Dync1h1, Zebrafish: dync1h1 (phenotype score=0) |
| Literature | 211 篇; cilia=10, sensory=9, direct_exp=6; tier=direct_experimental |

**解讀:** Dynein 重鏈——分子馬達的催化核心。驅動 IFT retrograde transport 和中心粒遷移。DYNC1H1 突變導致 cortical malformation 和 spinal muscular atrophy。**纖毛中 dynein 運輸缺陷是多種 ciliopathy 的核心病理，連結 photoreceptor disc renewal 和 hair cell 功能。** 10 篇纖毛文獻 + 9 篇感覺文獻在總 211 篇中比例很高（9%）。

---

### #6 — SMAD4（TGF-β/BMP 核心轉錄因子）⭐

| 指標 | 值 |
|------|------|
| Composite | 0.7227 |
| Evidence layers | **6/6 全層** |
| gnomAD | LOEUF=0.227 (norm=0.904) — **高度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=28.8 TPM; enrichment=1.10; norm=0.529 |
| Localization | HPA: Cytosol + Nucleoplasm + **Centrosome**; proximity=1.000 |
| Animal Model | Mouse: Smad4, Zebrafish: smad4a (phenotype score=0) |
| Literature | 6,577 篇; cilia=6, sensory=78, polarity=49; tier=direct_experimental |

**解讀:** TGF-β/BMP 信號通路的核心介導者。BMP signaling 在耳蝸發育中調控 hair cell 分化和 stereocilia polarity。SMAD4 也參與 cilia-dependent Hedgehog signaling。Centrosome 定位 + 高度 constrained + 6/6 全層 evidence 支持其在纖毛功能中的角色。

---

### #7 — DLG4 / PSD-95（突觸後密度蛋白）⭐

| 指標 | 值 |
|------|------|
| Composite | 0.7116 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.166 (norm=0.935) — **極度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=**224.5 TPM** (極高); enrichment=**2.24**; norm=0.674 |
| Localization | 無 HPA 定位數據 |
| Animal Model | Mouse: Dlg4, Zebrafish: dlg4a (phenotype score=0) |
| Literature | 2,000 篇; sensory=**57**, cyto=319, polarity=27; tier=direct_experimental |

**解讀:** DLG4/PSD-95 是感覺神經元突觸的核心支架蛋白。在 photoreceptor ribbon synapse 和 hair cell afferent synapse 中表達。其極度 LoF intolerance + 極高的 cerebellum 表達 + 大量感覺文獻，使其成為感覺突觸傳遞缺陷角度的重要候選。

---

### #8 — CETN2（Centrin-2）

| 指標 | 值 |
|------|------|
| Composite | 0.7006 |
| Evidence layers | 4/6 (expression + annotation + localization + literature，缺 gnomAD) |
| gnomAD | 無數據（gnomAD v4.1 中此基因缺失） |
| Expression | GTEx cerebellum=27.2 TPM, testis=40.5 TPM; enrichment=0.56; norm=0.396 |
| Localization | HPA: **Centrosome** + Cytosol + Nucleoplasm; proximity=1.000 |
| Literature | 110 篇 (under-studied); cilia=**17**, sensory=8, direct_exp=**11**; tier=direct_experimental |

**解讀:** Centrin-2 是中心粒複製必需的 Ca²⁺-binding protein。在 connecting cilium 和 photoreceptor basal body 有表達。同家族 **CETN3 已與 ciliopathy 有關連**。110 篇中 17 篇纖毛文獻（15.5%）— truly under-studied 且纖毛比例極高。

---

### #9 — DLL1（Delta-like 1, Notch Ligand）

| 指標 | 值 |
|------|------|
| Composite | 0.6914 |
| Evidence layers | 4/6 (gnomAD + annotation + localization + literature) |
| gnomAD | LOEUF=0.236 (norm=0.899) — **高度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=4.6 TPM; enrichment=0.43; norm=0.280 (未進入 scoring) |
| Localization | HPA: Plasma membrane; proximity=0.000 |
| Literature | 751 篇; cilia=8, sensory=26, polarity=8, direct_exp=4; tier=direct_experimental |

**解讀:** Notch signaling 在 inner ear hair cell 命運決定中是關鍵通路。DLL1 作為 Notch ligand，調控 lateral inhibition（決定 hair cell vs supporting cell）。高度 constrained + 26 篇感覺文獻。Notch-cilia 互動近年有報導。

---

### #10 — CRMP1（Collapsin Response Mediator 1）⭐

| 指標 | 值 |
|------|------|
| Composite | 0.6888 |
| Evidence layers | **6/6 全層** |
| gnomAD | LOEUF=0.440 (norm=0.795) — 中高度 constrained, pLI=1.000 |
| Expression | GTEx cerebellum=**95.3 TPM** (高); enrichment=**2.43** (Usher 組織明顯富集); norm=0.666 |
| Localization | HPA: **Centrosome + Cytosol**; proximity=1.000 |
| Animal Model | Mouse: Crmp1, Zebrafish: crmp1 (phenotype score=0) |
| Literature | 178 篇; sensory=6, cyto=33; tier=hts_hit |

**解讀:** CRMP1 參與微管組裝和 axon guidance，在感覺神經元高度表達。Cerebellum enrichment 極高（2.43）。雖然纖毛文獻不多，但其在微管動態和感覺神經元發育中的角色，加上 centrosome 定位和全 6 層 evidence，使其成為有潛力的 under-studied 候選。

---

### #11 — FGFR1（FGF Receptor 1）

| 指標 | 值 |
|------|------|
| Composite | 0.6857 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.285 (norm=0.874) — **高度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=121.6 TPM; enrichment=1.31; norm=0.615 |
| Literature | 6,129 篇; cilia=35, sensory=**132**, direct_exp=8; tier=direct_experimental |

**解讀:** FGF 信號在耳蝸發育中調控 otic vesicle patterning 和 hair cell 分化。FGFR1 也參與 ciliogenesis 調控。132 篇感覺文獻 + 35 篇纖毛文獻是非纖毛基因中很高的數字。

---

### #12 — ATP1A3（Na⁺/K⁺ ATPase α3）

| 指標 | 值 |
|------|------|
| Composite | 0.6833 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.214 (norm=0.911) — **高度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=**346.3 TPM** (極高); enrichment=**2.40**; norm=0.680 |
| Literature | 527 篇; sensory=**78**; tier=hts_hit |

**解讀:** 神經元 Na⁺/K⁺ pump。ATP1A3 突變致 alternating hemiplegia of childhood 和 rapid-onset dystonia-parkinsonism，部分患者伴有**聽力損失**。在耳蝸 stria vascularis 高表達，維持 endolymph 離子梯度（聽覺轉導必需）。

---

### #13 — ATP2B2（Plasma Membrane Ca²⁺ ATPase 2）⭐

| 指標 | 值 |
|------|------|
| Composite | 0.6832 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.190 (norm=0.923) — **極度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=**164.7 TPM**; enrichment=**2.92** (最高之一); norm=0.688 |
| Literature | 180 篇; sensory=**54**; tier=hts_hit |

**解讀:** ATP2B2 是 Ca²⁺ extrusion pump。**Atp2b2 突變 (deafwaddler) 小鼠完全失聰** — 在耳蝸毛細胞 stereocilia 頂端高度表達，負責 mechanotransduction 後的 Ca²⁺ 排出。極度 constrained + 最高 Usher tissue enrichment 之一（2.92）。**如果此基因確認參與 Usher 通路，將直接連結 stereocilia Ca²⁺ homeostasis 與視聽退化。**

---

### #14 — PKD1 / Polycystin-1（已知 Ciliopathy 基因 — 陽性對照）

| 指標 | 值 |
|------|------|
| Composite | 0.6831 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.360 (norm=0.836), pLI=1.000 |
| Expression | GTEx cerebellum=**577.2 TPM** (極高); enrichment=**2.54**; norm=0.685 |
| Literature | 2,521 篇; cilia=**242**, sensory=19, direct_exp=**201**; tier=direct_experimental |

**解讀:** **已知 ciliopathy 基因** — PKD1 突變致 autosomal dominant polycystic kidney disease。Polycystin-1 是 primary cilia 上的機械感受器。242 篇纖毛文獻、201 篇直接實驗。Pipeline 正確排名高位，作為**陽性對照**驗證 scoring 系統有效。

---

### #15 — ARL3（ADP-Ribosylation Factor-like 3）⭐ NEW

| 指標 | 值 |
|------|------|
| Composite | 0.6826 |
| Evidence layers | **6/6 全層** |
| gnomAD | LOEUF=0.557 (norm=0.736), pLI=0.930 |
| Expression | GTEx cerebellum=51.7 TPM; enrichment=1.04; norm=0.545 |
| Localization | HPA: **Centrosome + Nucleoplasm**; proximity=1.000 |
| Animal Model | Mouse: Arl3, Zebrafish: arl3l1 (phenotype score=0) |
| Literature | 169 篇; cilia=**88**, sensory=**49**, direct_exp=**45**; tier=direct_experimental |

**解讀:** ARL3 是 **已確認的纖毛信號蛋白**，調控 ciliary protein trafficking（與 RP2/UNC119 組成 lipidated cargo release 複合物）。169 篇中 88 篇纖毛文獻（**52%**）和 49 篇感覺文獻（**29%**）— 在所有候選基因中纖毛相關比例最高。ARL3 突變在小鼠致 retinal degeneration 和 ciliopathy。**此基因可能是真正的 Usher-adjacent ciliopathy 候選基因，值得最高優先研究。**

---

### #16 — GRIA2（Glutamate Receptor, AMPA 2）

| 指標 | 值 |
|------|------|
| Composite | 0.6810 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.123 (norm=0.957) — **極度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=74.4 TPM; enrichment=**2.29**; norm=0.656 |
| Literature | 1,758 篇; sensory=**87**; tier=hts_hit |

**解讀:** GRIA2 是 AMPA receptor 核心亞單位。在 cochlear nucleus 和 auditory pathway 大量表達。Hair cell afferent synapse 使用 glutamatergic transmission。極度 LoF intolerant。

---

### #17 — SNCA（α-Synuclein）

| 指標 | 值 |
|------|------|
| Composite | 0.6810 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.691 (norm=0.667) |
| Expression | GTEx cerebellum=73.9 TPM; enrichment=**2.74**; norm=0.667 |
| Literature | 4,084 篇; sensory=28, cyto=734, HTS=157; tier=direct_experimental |

**解讀:** Parkinson disease 相關蛋白。SNCA 在 synaptic vesicle 循環和 cytoskeleton 動態有角色。近年發現 synuclein 與 cilia 有交互作用。Cerebellum 高表達，但主要文獻集中在 neurodegeneration 而非 ciliopathy。

---

### #18 — HDAC6（Histone Deacetylase 6）⭐ NEW

| 指標 | 值 |
|------|------|
| Composite | 0.6801 |
| Evidence layers | 5/6 (缺 gnomAD) |
| gnomAD | 無數據 |
| Expression | GTEx cerebellum=92.0 TPM; enrichment=1.08; norm=0.573 |
| Localization | HPA: Cytosol + Nucleoplasm + **Centrosome**; proximity=1.000 |
| Literature | 2,915 篇; cilia=**119**, sensory=36, direct_exp=40, cyto=**605**; tier=direct_experimental |

**解讀:** HDAC6 是**已知的 ciliogenesis 調控因子**。它 deacetylates α-tubulin，調控 cilia disassembly。HDAC6 抑制劑（如 tubastatin A）可以**穩定纖毛**。119 篇纖毛文獻 + centrosome 定位。在 ciliopathy 治療研究中是重要靶點。其缺少 gnomAD 數據可能因位於 chrX 而非常染色體。

---

### #19 — VAMP2（Synaptobrevin-2）

| 指標 | 值 |
|------|------|
| Composite | 0.6786 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.345 (norm=0.844) — **高度 constrained**, pLI=0.997 |
| Expression | GTEx cerebellum=**500.5 TPM** (極高); enrichment=**1.96**; norm=0.669 |
| Literature | 1,286 篇; sensory=24, cyto=115, polarity=13; tier=hts_hit |

**解讀:** Synaptobrevin-2 是 SNARE 複合物核心成員，驅動 synaptic vesicle exocytosis。在 hair cell ribbon synapse 和 photoreceptor synapse 中有關鍵功能。極高的 cerebellum 表達（500 TPM）。

---

### #20 — TRIM71（Tripartite Motif Containing 71）

| 指標 | 值 |
|------|------|
| Composite | 0.6771 |
| Evidence layers | 4/6 (gnomAD + annotation + localization + literature) |
| gnomAD | LOEUF=0.275 (norm=0.880) — **高度 LoF intolerant**, pLI=1.000 |
| Expression | GTEx cerebellum=0.08 TPM (極低); enrichment=0.03; norm=0.113 |
| Localization | HPA: Actin filaments + Focal adhesion sites + Plasma membrane; proximity=0.300 |
| Literature | 100 篇; cilia=1, sensory=5; tier=hts_hit |

**解讀:** TRIM71 是 RNA-binding protein，參與 miRNA 通路和幹細胞分化。高度 constrained 但表達極低且纖毛/感覺文獻很少。排名偏高可能因 annotation score 驅動。優先級較低。

---

## 優先級總結

### 最高優先 — 直接纖毛/感覺證據

| 基因 | Layers | 核心理由 |
|------|--------|---------|
| **ARL3** ⭐ | 6/6 | 已確認纖毛信號蛋白。52% 文獻為纖毛相關。Centrosome 定位。調控 ciliary cargo transport。 |
| **PAFAH1B1** (LIS1) ⭐ | 6/6 | Dynein transport 核心。極度 LoF intolerant (LOEUF=0.10)。Centrosome 定位。IFT 核心。 |
| **DYNC1H1** ⭐ | 6/6 | Dynein 重鏈。極度 LoF intolerant (LOEUF=0.12)。Centrosome 定位。纖毛逆行運輸。 |
| **ATP2B2** ⭐ | 5/6 | Atp2b2 突變小鼠失聰。stereocilia Ca²⁺ pump。極度 constrained (LOEUF=0.19)。Enrichment=2.92。 |
| **HDAC6** ⭐ | 5/6 | 已知 ciliogenesis 調控因子。119 篇纖毛文獻。Centrosome 定位。 |

### 高優先 — 強多層證據

| 基因 | Layers | 核心理由 |
|------|--------|---------|
| **DLG4** (PSD-95) | 5/6 | 感覺突觸核心支架。極度 LoF intolerant (LOEUF=0.17)。cerebellum 225 TPM。 |
| **SMAD4** | 6/6 | TGF-β/BMP 核心。Hair cell 分化和 Hedgehog signaling。Centrosome 定位。 |
| **CRMP1** | 6/6 | Under-studied centrosome 蛋白。Usher tissue enrichment=2.43。6/6 全層。 |
| **LRP6** | 4/6 | Wnt/PCP co-receptor。高度 constrained。Polarity 是 stereocilia bundle 排列關鍵。 |
| **DLG5** | 4/6 | Cell junction + polarity。PCP 信號對毛細胞至關重要。 |
| **CETN2** | 4/6 | 纖毛/感覺文獻比例 15.5%。Centrosome 定位。同家族 CETN3 已有 ciliopathy 報導。 |

### 中優先 — 間接但有潛力

| 基因 | Layers | 核心理由 |
|------|--------|---------|
| **ATP1A3** | 5/6 | Na⁺/K⁺ pump。部分患者有聽力損失。Stria vascularis 表達。 |
| **FGFR1** | 5/6 | FGF 信號調控 hair cell 分化。132 篇感覺文獻。 |
| **DLL1** | 4/6 | Notch ligand。Inner ear lateral inhibition 關鍵。 |
| **GRIA2** | 5/6 | AMPA receptor。Hair cell glutamatergic transmission。 |
| **VAMP2** | 5/6 | SNARE 蛋白。Ribbon synapse exocytosis。cerebellum 500 TPM。 |

### 陽性對照（驗證 pipeline 有效）

| 基因 | 已知疾病 | Rank (≥4 layers) |
|------|---------|-----------------|
| **PKD1** | Autosomal dominant polycystic kidney disease | #14 |
| **SDCCAG8** | Nephronophthisis-related ciliopathy, Bardet-Biedl | #18 (score=0.6753) |

---

## 與上一版比較（v2 → v3）

| 變更 | 影響 |
|------|------|
| gnomAD coverage 78.5% → 93.8% | +3,471 genes 獲得 gnomAD constraint 數據 |
| gene_symbol fallback 修正 | 許多有 NCBI numeric ID 的基因現在有 Ensembl mapping |
| HIGH tier 18 → 82 | 更多基因達到 score ≥ 0.7 + evidence ≥ 3 |
| **新進 top 20** | ARL3、HDAC6 首次進入——兩者都是已確認的纖毛相關蛋白 |
| 3-layer inflation 更明顯 | gnomAD 廣泛覆蓋後，gnomAD+annot+lit 三層組合更常見 |

---

## 建議下一步

1. **ARL3**: 調查 ARL3 突變小鼠是否有聽力/視力表型；檢查 ARL3 在 photoreceptor connecting cilium 的 proteomics 數據
2. **ATP2B2**: 查詢 Usher 患者 cohort 中的 ATP2B2 variants；小鼠 deafwaddler 模型的視網膜表型
3. **HDAC6**: 評估 HDAC6 inhibitor 對 Usher 相關 ciliopathy 模型的治療潛力
4. **PAFAH1B1 / DYNC1H1**: 調查 lissencephaly 患者是否有亞臨床聽力/視力退化
5. **計分改進**: 考慮對 3-layer-only 基因施加 penalty（如要求至少 1 個非 annotation/literature 層），以減少膨脹效應
6. 補齊 **CellxGene** 單細胞數據（photoreceptor + hair cell 表達），可大幅提升 retina/inner ear 特異性判斷
