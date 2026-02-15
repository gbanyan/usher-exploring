# TOP 20 Usher 候選基因分析（完整 6 層證據）

**Pipeline Version:** 0.1.0
**Generated:** 2026-02-16
**Scoring Layers:** gnomAD constraint (0.20) + Expression (0.20) + Annotation (0.15) + Localization (0.15) + Animal Model (0.15) + Literature (0.15)
**Coverage:** gnomAD 78.5% | Expression 87.4% | Annotation 98.8% | Localization 63.7% | Animal Model 84.7% | Literature 100%

---

## 篩選條件

- Composite score ≥ 0.68（加權平均，NULL-preserving）
- Evidence layers ≥ 3/6
- 以 gene_symbol 去重（取最高分 Ensembl ID）
- 排序：composite_score DESC

---

## #1 — DRD4（多巴胺受體 D4）

| 指標 | 值 |
|------|------|
| Composite | 0.7617 |
| Evidence layers | 3/6 (annotation + localization + literature) |
| gnomAD | LOEUF=1.952 (norm=0.023, 不 constrained) |
| Expression | GTEx cerebellum=7.0 TPM, testis=6.3 TPM, enrichment=1.09 |
| Localization | HPA: Plasma membrane + **Centrosome**; hits: centrosome |
| Literature | 2,021 篇; sensory=33, HTS=20, cyto=87; tier=hts_hit |

**解讀:** DRD4 在 centrosome 有定位，大量感覺系統文獻，但作為 GPCR 與 Usher 連結較間接。gnomAD 不 constrained，3/6 層排名偏高可能因 `weighted_sum/available_weight` 膨脹。優先級中等。

---

## #2 — PAFAH1B1 / LIS1（Dynein 調控因子）⭐

| 指標 | 值 |
|------|------|
| Composite | 0.7414 |
| Evidence layers | **6/6 全層** |
| gnomAD | LOEUF=0.100 (norm=0.969) — **極度 LoF intolerant (top 1%)** |
| Expression | GTEx cerebellum=131.0 TPM, testis=125.6 TPM; enrichment=1.17 |
| Localization | HPA: **Centrosome**; hits: centrosome |
| Literature | 496 篇; cilia=4, sensory=3, direct_exp=4, cyto=**424**; tier=direct_experimental |

**解讀:** LIS1 是 cytoplasmic dynein 的關鍵調控因子，控制微管 minus-end transport。Dynein 負責 IFT（intraflagellar transport）逆行運輸，是纖毛維持的核心機制。LIS1 突變致 lissencephaly（無腦回畸形），極度 LoF intolerant 表明該基因不可或缺。與 Usher 的連結在於 **dynein transport 對感覺纖毛（photoreceptor connecting cilium、stereocilia kinocilium）至關重要**。

---

## #3 — DYNC1H1（Cytoplasmic Dynein 重鏈）⭐

| 指標 | 值 |
|------|------|
| Composite | 0.7344 |
| Evidence layers | **6/6 全層** |
| gnomAD | LOEUF=0.106 (norm=0.966) — **極度 LoF intolerant** |
| Expression | GTEx cerebellum=129.1 TPM, testis=44.4 TPM; enrichment=1.68 |
| Localization | HPA: **Centrosome + Cytosol**; hits: centrosome |
| Literature | 211 篇; cilia=10, sensory=9, direct_exp=6, cyto=110; tier=direct_experimental |

**解讀:** Dynein 重鏈——分子馬達的催化核心。驅動 IFT retrograde transport 和中心粒遷移。DYNC1H1 突變導致 cortical malformation 和 spinal muscular atrophy。**纖毛中 dynein 運輸缺陷是多種 ciliopathy 的核心病理，連結 photoreceptor disc renewal 和 hair cell 功能。**

---

## #4 — DLG5（Discs Large 5）

| 指標 | 值 |
|------|------|
| Composite | 0.7283 |
| Evidence layers | 3/6 (annotation + localization + literature) |
| gnomAD | LOEUF=0.318 (norm=0.858, constrained) |
| Expression | GTEx cerebellum=15.1 TPM, testis=18.6 TPM; enrichment=0.70 |
| Localization | HPA: **Cell Junctions** |
| Literature | 168 篇; cilia=3, sensory=2, polarity=17, direct_exp=2; tier=direct_experimental |

**解讀:** DLG5 是 Scribble 極性複合物相關蛋白，調控 apicobasal polarity 和 cell junction 形成。Planar cell polarity (PCP) 信號是耳蝸毛細胞 stereocilia bundle 正確排列的關鍵。DLG5 突變小鼠有 neural tube defect。

---

## #5 — SMAD4（TGF-β/BMP 核心轉錄因子）⭐

| 指標 | 值 |
|------|------|
| Composite | 0.7227 |
| Evidence layers | **6/6 全層** |
| gnomAD | LOEUF=0.172 (norm=0.932) — **高度 LoF intolerant** |
| Expression | GTEx cerebellum=28.8 TPM, testis=17.4 TPM; enrichment=1.10 |
| Localization | HPA: Cytosol + Nucleoplasm + **Centrosome**; hits: centrosome |
| Literature | 6,577 篇; cilia=6, sensory=78, HTS=162, polarity=49; tier=direct_experimental |

**解讀:** TGF-β/BMP 信號通路的核心介導者。BMP signaling 在耳蝸發育中調控 hair cell 分化和 stereocilia polarity。SMAD4 也參與 cilia-dependent Hedgehog signaling。Centrosome 定位 + 高度 constrained 支持其在纖毛功能中的角色。

---

## #6 — CHRNA7（菸鹼型乙醯膽鹼受體 α7）

| 指標 | 值 |
|------|------|
| Composite | 0.7187 |
| Evidence layers | 3/6 (expression + annotation + literature) |
| gnomAD | LOEUF=0.448 (norm=0.791, 中度 constrained) |
| Expression | HPA cerebellum=2; GTEx cerebellum=0.1 TPM; enrichment=1.27 |
| Localization | 無 HPA 定位數據 |
| Literature | 2,051 篇; cilia=8, sensory=21, HTS=21; tier=direct_experimental |

**解讀:** CHRNA7 在 cochlear efferent 突觸和聽覺通路中有角色。與聽力損失相關的 cholinergic signaling 已有報導。缺少 localization 數據限制了進一步判斷。

---

## #7 — DLG4 / PSD-95（突觸後密度蛋白）⭐

| 指標 | 值 |
|------|------|
| Composite | 0.7116 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.079 (norm=0.980) — **極度 LoF intolerant (top 0.5%)** |
| Expression | GTEx cerebellum=**224.5 TPM** (極高); enrichment=**2.24** |
| Localization | 無 HPA 定位數據 |
| Literature | 2,000 篇; sensory=**57**, cyto=319, polarity=27; tier=direct_experimental |

**解讀:** DLG4/PSD-95 是感覺神經元突觸的核心支架蛋白。在 photoreceptor ribbon synapse 和 hair cell afferent synapse 中表達。其極度 LoF intolerance + 最高的 cerebellum 表達之一 + 大量感覺文獻，使其成為感覺突觸傳遞缺陷角度的重要候選。

---

## #8 — LTB（Lymphotoxin Beta）

| 指標 | 值 |
|------|------|
| Composite | 0.7109 |
| Evidence layers | 3/6 (annotation + localization + literature) |
| gnomAD | LOEUF=1.781 (norm=0.111, 不 constrained) |
| Localization | HPA: Centrosome; hits: centrosome |
| Literature | 2,648 篇; cilia=6, sensory=8; tier=hts_hit |

**解讀:** 免疫信號分子，centrosome 定位可能是細胞分裂期間的暫時性定位而非纖毛功能相關。gnomAD 不 constrained。與 Usher 連結較弱，優先級低。

---

## #9 — LRP6（Wnt Co-receptor）

| 指標 | 值 |
|------|------|
| Composite | 0.7080 |
| Evidence layers | 3/6 (expression + annotation + literature) |
| gnomAD | LOEUF=0.270 (norm=0.882) — **高度 constrained** |
| Expression | GTEx cerebellum=11.1 TPM, testis=7.8 TPM; enrichment=0.90 |
| Localization | 無 HPA 定位數據 |
| Literature | 1,557 篇; cilia=13, sensory=35, direct_exp=3, polarity=**44**; tier=direct_experimental |

**解讀:** LRP6 是 canonical Wnt 信號的共受體。**Wnt/PCP 信號通路對耳蝸毛細胞的平面細胞極性（stereocilia bundle 朝向）至關重要。** Wnt 信號也參與 ciliogenesis 調控。高度 constrained + 纖毛/感覺文獻 + polarity 文獻使其成為值得深入研究的候選。

---

## #10 — GBA1（Glucocerebrosidase）

| 指標 | 值 |
|------|------|
| Composite | 0.7059 |
| Evidence layers | 3/6 (expression + annotation + literature) |
| gnomAD | 無數據 |
| Expression | GTEx cerebellum=9.6 TPM, testis=9.2 TPM; enrichment=0.89 |
| Localization | 無 HPA 定位數據 |
| Literature | 890 篇; cilia=12, sensory=7, direct_exp=11; tier=direct_experimental |

**解讀:** 溶酶體酶，GBA1 突變致 Gaucher disease。近年發現 lysosome-cilia 交互作用：autophagy 調控 ciliogenesis，溶酶體功能障礙影響纖毛 homeostasis。12 篇纖毛文獻在非纖毛基因中較多。

---

## #11 — CETN2（Centrin-2）

| 指標 | 值 |
|------|------|
| Composite | 0.7006 |
| Evidence layers | 4/6 (expression + annotation + localization + literature) |
| gnomAD | 無數據 |
| Expression | GTEx cerebellum=27.2 TPM, testis=40.5 TPM; enrichment=0.56 |
| Localization | HPA: **Centrosome** + Cytosol + Nucleoplasm; hits: **centrosome_proteomics**, centrosome |
| Literature | 110 篇 (under-studied); cilia=**17**, sensory=8, direct_exp=**11**; tier=direct_experimental |

**解讀:** Centrin-2 是中心粒複製必需的 Ca²⁺-binding protein。在 connecting cilium 和 photoreceptor basal body 有表達。同家族 **CETN3 已與 ciliopathy 有關連**。相對低發表量意味著 truly under-studied，但纖毛/感覺證據比例極高（17/110 = 15.5%）。

---

## #12 — SDCCAG8（已知 Ciliopathy 基因 — 陽性對照）

| 指標 | 值 |
|------|------|
| Composite | 0.6965 |
| Evidence layers | 4/6 (expression + annotation + localization + literature) |
| gnomAD | LOEUF=0.810 (norm=0.606, 中度 constrained) |
| Expression | GTEx cerebellum=7.1 TPM, testis=7.3 TPM; enrichment=0.75 |
| Localization | HPA: **Centrosome**; hits: centrosome |
| Literature | 71 篇; cilia=15, sensory=9, direct_exp=**13**; tier=direct_experimental |

**解讀:** **已知 ciliopathy 基因** — SDCCAG8 突變致 nephronophthisis-related ciliopathy 和 Bardet-Biedl 相關表型。Pipeline 正確將其排為 top tier，作為**陽性對照**驗證 scoring 系統有效。

---

## #13 — CRMP1（Collapsin Response Mediator 1）⭐

| 指標 | 值 |
|------|------|
| Composite | 0.6869 |
| Evidence layers | **6/6 全層** |
| gnomAD | LOEUF=0.301 (norm=0.866) — **高度 constrained** |
| Expression | GTEx cerebellum=**95.3 TPM** (高); enrichment=**2.43** (Usher 組織明顯富集) |
| Localization | HPA: **Centrosome + Cytosol**; hits: centrosome |
| Literature | 178 篇; sensory=6, cyto=33; tier=hts_hit |

**解讀:** CRMP1 參與微管組裝和 axon guidance，在感覺神經元高度表達。Cerebellum enrichment 極高。雖然纖毛文獻不多，但其在微管動態和感覺神經元發育中的角色，加上 centrosome 定位和高 constraint，使其成為有潛力的新候選。

---

## #14 — ATP1A3（Na⁺/K⁺ ATPase α3）

| 指標 | 值 |
|------|------|
| Composite | 0.6833 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.156 (norm=0.940) — **高度 LoF intolerant** |
| Expression | GTEx cerebellum=**346.3 TPM** (極高); enrichment=**2.40** |
| Localization | 無 HPA 定位數據 |
| Literature | 527 篇; sensory=**78**; tier=hts_hit |

**解讀:** 神經元 Na⁺/K⁺ pump。ATP1A3 突變致 alternating hemiplegia of childhood 和 rapid-onset dystonia-parkinsonism，部分患者伴有**聽力損失**。在耳蝸 stria vascularis 高表達，維持 endolymph 離子梯度（聽覺轉導必需）。

---

## #15 — ATP2B2（Plasma Membrane Ca²⁺ ATPase 2）⭐

| 指標 | 值 |
|------|------|
| Composite | 0.6832 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.128 (norm=0.955) — **極度 LoF intolerant** |
| Expression | GTEx cerebellum=**164.7 TPM**; enrichment=**2.92** (Usher 組織極度富集) |
| Localization | 無 HPA 定位數據 |
| Literature | 180 篇; sensory=**54**; tier=hts_hit |

**解讀:** ATP2B2 是 Ca²⁺ extrusion pump。**Atp2b2 突變 (deafwaddler) 小鼠完全失聰** — 在耳蝸毛細胞 stereocilia 頂端高度表達，負責 mechanotransduction 後的 Ca²⁺ 排出。極度 constrained + 最高 Usher tissue enrichment 之一。**如果此基因確認參與 Usher 通路，將直接連結 stereocilia Ca²⁺ homeostasis 與視聽退化。**

---

## #16 — PKD1 / Polycystin-1（已知 Ciliopathy 基因 — 陽性對照）

| 指標 | 值 |
|------|------|
| Composite | 0.6831 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.360 (norm=0.836) |
| Expression | GTEx cerebellum=**577.2 TPM** (極高); enrichment=**2.54** |
| Localization | 無 HPA 定位數據 |
| Literature | 2,521 篇; cilia=**242**, sensory=19, direct_exp=**201**; tier=direct_experimental |

**解讀:** **已知 ciliopathy 基因** — PKD1 突變致 autosomal dominant polycystic kidney disease。Polycystin-1 是 primary cilia 上的機械感受器。242 篇纖毛文獻、201 篇直接實驗。Pipeline 正確排名，作為**陽性對照**。

---

## #17 — FGFR1（FGF Receptor 1）

| 指標 | 值 |
|------|------|
| Composite | 0.6826 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.202 (norm=0.917) — **高度 LoF intolerant** |
| Expression | GTEx cerebellum=121.6 TPM, testis=31.3 TPM; enrichment=1.31 |
| Localization | 無 HPA 定位數據 |
| Literature | 6,129 篇; cilia=35, sensory=**132**, direct_exp=8; tier=direct_experimental |

**解讀:** FGF 信號在耳蝸發育中調控 otic vesicle patterning 和 hair cell 分化。FGFR1 也參與 ciliogenesis 調控。高度 constrained + 豐富的感覺/纖毛文獻。

---

## #18 — KIFC1（Kinesin-14 Motor）

| 指標 | 值 |
|------|------|
| Composite | 0.6815 |
| Evidence layers | 4/6 (expression + annotation + localization + literature) |
| gnomAD | LOEUF=0.706 (norm=0.660, 中度 constrained) |
| Expression | enrichment=**3.00** (最高) |
| Localization | HPA: **Centrosome**; hits: centrosome |
| Literature | 243 篇; cilia=7, cyto=**144**, direct_exp=2; tier=direct_experimental |

**解讀:** Minus-end directed kinesin motor，參與 centrosome clustering 和 spindle formation。Centrosome 定位 + 極高 Usher tissue enrichment 值得進一步研究。

---

## #19 — GRIA2（Glutamate Receptor, Ionotropic AMPA 2）

| 指標 | 值 |
|------|------|
| Composite | 0.6810 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.123 (norm=0.957) — **極度 LoF intolerant** |
| Expression | GTEx cerebellum=74.4 TPM; enrichment=**2.29** |
| Localization | 無 HPA 定位數據 |
| Literature | 1,758 篇; sensory=**87**; tier=hts_hit |

**解讀:** GRIA2 是 AMPA receptor 核心亞單位。在 cochlear nucleus 和 auditory pathway 大量表達。Hair cell afferent synapse 使用 glutamatergic transmission。GRIA2 突變致 neurodevelopmental disorder。

---

## #20 — SNCA（α-Synuclein）

| 指標 | 值 |
|------|------|
| Composite | 0.6810 |
| Evidence layers | 5/6 (缺 localization) |
| gnomAD | LOEUF=0.397 (norm=0.817) |
| Expression | GTEx cerebellum=73.9 TPM; enrichment=**2.74** |
| Localization | 無 HPA 定位數據 |
| Literature | 4,084 篇; sensory=28, cyto=**734**, HTS=157; tier=direct_experimental |

**解讀:** Parkinson disease 相關蛋白。SNCA 在 synaptic vesicle 循環和 cytoskeleton 動態有角色。近年發現 synuclein 與 cilia 有交互作用。Cerebellum 高表達，但主要文獻集中在 neurodegeneration 而非 ciliopathy。

---

## 優先級總結

### 最高優先

| 基因 | 理由 |
|------|------|
| **PAFAH1B1** (LIS1) | Dynein transport 核心。6/6 全層。極度 LoF intolerant (LOEUF=0.10)。IFT 是 ciliopathy 核心機制。 |
| **DYNC1H1** | Dynein 重鏈。6/6 全層。極度 LoF intolerant (LOEUF=0.11)。直接驅動纖毛逆行運輸。 |
| **ATP2B2** | Atp2b2 突變小鼠失聰。stereocilia Ca²⁺ pump。極度 constrained (LOEUF=0.13)。Usher tissue enrichment=2.92。 |

### 高優先

| 基因 | 理由 |
|------|------|
| **DLG4** (PSD-95) | 感覺突觸核心支架。極度 LoF intolerant (LOEUF=0.08)。cerebellum 224 TPM。 |
| **LRP6** | Wnt/PCP co-receptor。高度 constrained。Polarity 是 stereocilia bundle 排列關鍵。 |
| **CRMP1** | Under-studied centrosome 蛋白。6/6 全層。Usher tissue enrichment=2.43。 |
| **CETN2** | 纖毛/感覺文獻比例 15.5% (17/110)。centrosome proteomics hit。同家族 CETN3 已有 ciliopathy 報導。 |
| **SMAD4** | TGF-β/BMP 核心。6/6 全層。調控 hair cell 分化和 Hedgehog signaling。 |

### 陽性對照（驗證 pipeline 有效）

| 基因 | 已知疾病 |
|------|---------|
| **SDCCAG8** | Nephronophthisis-related ciliopathy, Bardet-Biedl |
| **PKD1** | Autosomal dominant polycystic kidney disease |

### 建議下一步

1. **ATP2B2**: 查詢是否有 Usher 患者 cohort 中的 ATP2B2 variants；小鼠 deafwaddler 模型已有視網膜表型報導嗎？
2. **PAFAH1B1 / DYNC1H1**: 調查 lissencephaly 患者是否有亞臨床聽力/視力退化
3. **CETN2**: 在 photoreceptor connecting cilium proteomics 數據中驗證表達
4. **LRP6**: 調查 Wnt/PCP 通路其他成員在本 pipeline 中的排名
5. 補齊 **CellxGene** 單細胞數據（photoreceptor + hair cell 表達），可大幅提升 retina/inner ear 特異性判斷
