# Response to YHC's review of UsherPipe draft-v2 / 對 YHC 審閱意見的回覆

Thank you for the detailed and careful reading — the comments materially improved the manuscript, and one of them uncovered a real scoring bug. Below is a point-by-point response. Items are grouped as **(A) changes made to the manuscript**, **(B) answers to your questions**, and **(C) decisions to handle in this reply rather than in the paper**.

感謝你仔細審閱。這些意見實質改善了稿件，其中一項還揭露了一個真正的計分程式錯誤。以下逐點回覆，分為 **(A) 已修改稿件**、**(B) 問題回答**、**(C) 於回覆說明、暫不改稿** 三類。

---

## (A) Changes made to the manuscript / 已修改稿件

**A1. "orthogonal" → "complementary" (Abstract, Introduction)**
You were right that the six layers are positively correlated (well-studied genes score high on annotation + literature + localization together), so "orthogonal" (which implies statistical independence) overstated it. Changed to "complementary" throughout.
你指出六層證據其實彼此正相關（研究充分的基因在 annotation＋literature＋localization 常同時高分），"orthogonal"（隱含統計獨立）確實過度宣稱，已全面改為 "complementary"。

**A2. "independent" → "separately computed" (Architecture, Figure 1)**
Accepted your strikeout. The layers are computed separately but are not independent (see A4), so the wording is corrected in both the text and the Figure 1 caption. The same fix was applied to both README files and the code docstring.
接受你的刪改。各層是「分別計算」但並非「獨立」（見 A4），已於內文與圖 1 圖說修正，並同步修正兩份 README 與程式碼註解。

**A3. Reference [4] and the "10–15% undiagnosed" figure**
You were correct that ref [4] (Bonnet & El-Amraoui, 2012 review) does not support the "10–15%" figure. We replaced it with the primary cohort study by the same lead author — Bonnet C, et al. *Eur J Hum Genet.* 2016;24(12):1730–1738 — which reports causal **biallelic mutations in 93%** of European patients, and reworded the claim to "biallelic variants in ~93% of patients, leaving roughly one in ten without a confirmed molecular diagnosis." *(This citation/wording is our proposal — please confirm it reads correctly.)*
你指出 ref [4]（Bonnet & El-Amraoui 2012 回顧）並不支持 "10–15%"，正確。已改引同一主要作者的原始世代研究 Bonnet C, et al. *Eur J Hum Genet.* 2016;24(12):1730–1738（歐洲病患 **93% 可找到雙等位致病突變**），並將敘述改為「約 93% 病患可找到雙等位變異，約十分之一仍無確定分子診斷」。

**A4. MGI / IMPC are not independent — double-counting fixed (the important one)**
This was the key finding. You are correct: IMPC phenotype data is ingested into MGI as Mammalian Phenotype (MP) ontology annotations, so the two are not independent. The old code compounded this twice — it awarded IMPC a separate "+0.3 independent-confirmation" bonus on top of the MGI mouse score, **and** summed the MGI + ZFIN + IMPC phenotype counts (so overlapping MGI/IMPC terms were counted twice in the log-scaling). We rewrote the animal-model scoring to fold MGI and IMPC into a **single mouse channel**: distinct MP terms across MGI ∪ IMPC are counted **once** (set union, not sum), and only one confidence-weighted mouse bonus is awarded; genes whose only mouse evidence is from IMPC still receive mouse credit. The fix was implemented test-first, and the entire pipeline was re-scored.
這是最關鍵的發現，你說得對：IMPC 的表型資料會以 Mammalian Phenotype (MP) ontology 形式併入 MGI，兩者並非獨立。舊程式錯了兩次——它在 MGI 小鼠分數之外，另給 IMPC 一個「+0.3 獨立確認」加分，**且**將 MGI＋ZFIN＋IMPC 的表型數量相加（MGI/IMPC 重疊詞彙在 log 縮放中被算兩次）。我們已重寫 animal-model 計分，把 MGI 與 IMPC 併為**單一小鼠來源**：MGI ∪ IMPC 的相異 MP 詞彙只計**一次**（取聯集，非相加），只給一次信心加權的小鼠加分；僅有 IMPC 證據的基因仍算有小鼠表型。此修正以測試先行方式實作，並重新計分整條 pipeline。

*Effect of the re-score / 重新計分的影響:*
- HIGH tier 95 → **83** genes / HIGH 層 95 → **83**。
- Known-gene validation essentially unchanged (median percentile 90.2 → 90.4%; still 35/38 in the top quartile) — the fix did not weaken sensitivity. / 已知基因驗證幾乎不變（中位百分位 90.2 → 90.4%；仍 35/38 在前四分位）——修正未削弱敏感度。
- **Improved specificity:** the housekeeping gene YWHAZ, previously the one negative control retained in HIGH, drops out (its inflated animal-model score 0.222 → 0.101). **Zero housekeeping genes now remain in HIGH.** / **特異性改善：** 原本唯一留在 HIGH 的對照基因 YWHAZ 已被剔除（其被膨脹的分數 0.222 → 0.101），**現在 HIGH 層無任何 housekeeping 基因**。
- All 10 OMIM Usher genes are still retained by the cilia-signal gate. / 10 個 OMIM Usher 基因仍全數通過 cilia-signal gate。

**A5. Supplementary table of merged and excluded genes**
Added, as requested: Additional file 1 (Table S1) lists all 1,539 gene symbols that had multiple Ensembl IDs and the retained canonical ID (1,503 kept a MANE Select canonical ID); Additional file 2 (Table S2) lists the 423 excluded genes (355 with composite < 0.2; 68 with no evidence). Both are regenerated reproducibly by `scripts/supplementary_tables.py`.
已依建議新增：Additional file 1（Table S1）列出全部 1,539 個具多重 Ensembl ID 的基因符號及保留的標準 ID（1,503 個保留 MANE Select 標準 ID）；Additional file 2（Table S2）列出 423 個被排除基因（355 個 composite < 0.2；68 個無證據）。兩表由 `scripts/supplementary_tables.py` 可重現產生。

**A6. USH vs. ciliopathy framing (the "混亂" comment)**
Agreed the Background jumped from Usher syndrome to "ciliopathies" without a bridge. Added a sentence explaining that the known Usher genes encode ciliary/periciliary proteins, so Usher syndrome sits within the broader ciliopathy spectrum — which motivates the genome-wide, ciliopathy-aware scope and the 38-gene validation set (10 OMIM Usher + 28 ciliary).
同意 Background 由 Usher 直接跳到 "ciliopathies" 缺少橋接。已加一句說明：已知 Usher 基因編碼纖毛/周纖毛蛋白，故 Usher 屬於較廣的 ciliopathy 範疇——這也解釋了全基因體、涵蓋 ciliopathy 的範圍設定與 38 基因驗證集（10 OMIM Usher＋28 纖毛基因）。

**A7. "11,406 candidates — too many?"**
The number is correct but the emphasis was misleading. The 11,406 is the MEDIUM+HIGH *tiered ranking*, not a shortlist; the actionable deliverable is the **83-gene HIGH shortlist**. We reworded the Abstract to lead with the 83-gene shortlist and present 11,406 as context.
數字正確但重點誤導。11,406 是 MEDIUM＋HIGH 的**分層排名**，非候選清單；真正可實驗跟進的是 **83 個 HIGH 基因**。已改寫摘要，改以 83 基因清單為主、11,406 為背景脈絡。

**A8. Animal-model species composition (mouse/zebrafish; C. elegans / FlyBase)**
A good point given that this layer is the most influential. Rather than run a full species split now, we added it as future work, tied explicitly to the layer's demonstrated dominance in the sensitivity analysis (see B7 for why we did not re-analyse for this revision).
此意見很好，因為此層影響最大。此次未做完整物種拆分，而是加入未來工作，並明確連結到敏感度分析中該層的主導地位（未於本次改稿重跑分析的理由見 B7）。

---

## (B) Answers to your questions / 問題回答

**B1. Seed genes / similarity — your summary is correct.**
Yes — seed-gene tools take known genes as "seeds" and rank others by similarity (expression, function, pathway, GO, PPI, mouse phenotype). Your note captured it exactly. UsherPipe deliberately does *not* use seeds, which is one of its distinguishing features.
是的，seed-gene 工具以已知基因為「種子」，依相似度（表現量、功能、pathway、GO、PPI、小鼠表型）排序其他基因，你的理解完全正確。UsherPipe 刻意**不用**種子，這正是其特點之一。

**B2. NULL-aware vs zero imputation — your summary is correct.**
Exactly as you wrote: each layer has a weight (summing to 1.0); missing evidence is kept as NULL rather than imputed to 0, and the composite is a weighted average over available layers only, so under-studied genes are not systematically penalised.
完全如你所述：各層有權重（總和 1.0）；缺值保留為 NULL 而非補 0，composite 僅就有資料的層做加權平均，故 under-studied 基因不被系統性懲罰。

**B3. Why these weights (0.20 / 0.15)?**
The weights are a biologically motivated *a priori* configuration, not learned (learning them collapses the integration onto one or two layers — see Discussion). gnomAD and expression get 0.20 because loss-of-function constraint and retina/ciliated-tissue specificity are the strongest genome-wide priors for this disease; the remaining four layers get 0.15 each. gnomAD is interpreted as a broad gene-level functional-importance measure (Usher is predominantly recessive, so it is not a direct inheritance predictor — this is stated in the Methods). We report per-gene layer contributions so any user can re-weight.
權重是有生物學依據的**先驗**設定，非學習而來（學習會使整合塌縮到一兩層，見 Discussion）。gnomAD 與 expression 給 0.20，因為 LoF 約束與視網膜/纖毛組織特異性是此疾病最強的全基因體先驗；其餘四層各 0.15。gnomAD 被詮釋為廣義的基因層級功能重要性指標（Usher 多為隱性遺傳，故非直接的遺傳模式預測——Methods 已說明）。我們輸出每個基因的各層貢獻，使用者可自行調權。

**B4. The six MeSH queries and evidence-tier auto-classification.**
The literature layer runs six batched PubMed MeSH queries combining the disease/phenotype vocabulary (Usher syndrome, retinitis pigmentosa, hearing loss, ciliopathy, cilium, photoreceptor) with each gene. Evidence is tiered automatically from the returned records: "direct experimental" (knockout/mutation/functional study) ranks above association-only or text-mining hits, based on MeSH qualifiers and publication-type tags. We can add the exact query strings and the tiering rules to the Methods/Supplement if you think it is warranted.
Literature 層以六組批次 PubMed MeSH 查詢，將疾病/表型詞彙（Usher syndrome、retinitis pigmentosa、hearing loss、ciliopathy、cilium、photoreceptor）與各基因組合。證據分層依回傳紀錄自動判定：「direct experimental」（knockout/mutation/功能研究）高於僅關聯或 text-mining，依 MeSH qualifier 與文獻類型標籤判斷。若你認為需要，我們可將確切查詢字串與分層規則加入 Methods/Supplement。

**B5. How was the 75% threshold decided?**
It is the 75th percentile of the animal-model score computed **over genes with a non-zero score** (threshold = 0.128), not the full layer (a zero means "no recorded phenotype", so it is excluded from the reference set). It is a *post-hoc* specificity filter chosen after the negative-control analysis found housekeeping genes in HIGH: we compared several gate definitions (non-zero signal; 75th; 90th percentile) and adopted the 75th because it retains every known disease gene reaching the HIGH thresholds while excluding **every** housekeeping control. It relabels tiers only and does not change any composite score.
它是 animal-model 分數**在非零基因上**的第 75 百分位（門檻 = 0.128），非整層計算（0 代表「無紀錄表型」，故排除於參考集之外）。這是在負對照分析發現 housekeeping 基因進入 HIGH 後所設的**事後**特異性過濾：我們比較數種 gate 定義（非零訊號；75th；90th），採 75th 因其能保留所有達 HIGH 門檻的已知基因，同時排除**全部** housekeeping 對照。它只重貼分層標籤，不改動任何 composite 分數。

**B6. "Candidate gene" vs "disease gene".**
By "known disease gene" we mean an established causative gene (our positive controls: 10 OMIM Usher genes + 28 SYSCILIA ciliary genes). By "candidate gene" we mean a gene the pipeline prioritises with supporting multi-layer evidence but which is not yet established as causative. These follow standard field usage, so we kept them undefined in the text, but we are happy to add a one-line definition at first use if you prefer.
「known disease gene」指已確立的致病基因（我方正對照：10 個 OMIM Usher＋28 個 SYSCILIA 纖毛基因）；「candidate gene」指 pipeline 依多層證據優先排序、但尚未確立為致病的基因。此為領域慣用語，內文未特別定義；若你希望，我們樂於在首次出現處加一行定義。

**B7. Other gene lists (Blueprint Genetics 21-gene panel; expanded USH-like sets).**
A fair suggestion. For this methods paper we validate against 38 genes (OMIM + SYSCILIA) and benchmark head-to-head against mantis-ml, which we think is sufficient to demonstrate the method. Benchmarking against expanded commercial/syndromic panels is a natural extension; we would rather flag it than run additional positive-control sets now, unless you feel a reviewer would require it.
合理建議。就此方法學論文，我們以 38 基因（OMIM＋SYSCILIA）驗證，並與 mantis-ml 正面對比，應足以展示方法。與擴充商用/症候群套組對比是自然延伸；除非你認為審稿人會要求，否則我們傾向標註為延伸方向，而不在此時新增正對照集。

**B8. CellxGene has scRNA; UsherPipe covers only protein-coding genes.**
Correct — UsherPipe's universe is the ~19,554 protein-coding genes; the CellxGene Census single-cell photoreceptor data is used only to supply retina cell-type expression evidence *for those genes*, not to expand the universe.
正確——UsherPipe 的範圍是約 19,554 個蛋白質編碼基因；CellxGene Census 單細胞光受器資料僅用來為**這些基因**補充視網膜細胞層級的表現量證據，並非擴充基因範圍。

**B9. VANGL2 / Vangl2 stereociliary polarity.**
Thank you for the corroborating note — yes, *Vangl2* mutant mice show disrupted stereociliary-bundle polarity, consistent with the manuscript's rationale for VANGL2 as a top candidate.
感謝你補充的佐證——是的，*Vangl2* 突變小鼠的立體纖毛束極化受損，與稿件將 VANGL2 列為首要候選的依據一致。

---

## (C) Handled here rather than in the paper / 於回覆說明、暫不改稿

- **B6 (define candidate/disease-gene)** and **B7 (expanded panels)** are answered above; we did not add them to the manuscript because the terms are field-standard and the current validation is sufficient for a methods paper. Happy to revisit if you disagree. / **B6、B7** 已於上方回答；因屬領域慣用語、且現有驗證足夠，暫不改稿。若你有不同看法，我們樂意再議。
- Your comprehension notes (seed genes, NULL-aware, convergent multi-layer support, MGI phenotype categories) matched our intent and needed no change. / 你的理解註記（seed genes、NULL-aware、convergent multi-layer support、MGI 表型分類）與我方原意一致，無需修改。

---

*One note on reproducibility: the MGI/IMPC fix changes several reported numbers throughout Results, Discussion, figures, and the benchmark; all have been re-derived from the re-scored pipeline and the PDF rebuilt. A pre-fix database backup is retained.*
*可重現性說明：MGI/IMPC 修正改動了 Results、Discussion、圖表與 benchmark 中多項數字，皆已由重新計分後的 pipeline 重新導出、PDF 重建；並保留修正前的資料庫備份。*
