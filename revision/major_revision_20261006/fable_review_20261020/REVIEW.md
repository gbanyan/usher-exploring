# UsherPipe 修訂包獨立審查（inputs/ 2026‑10‑20 凍結版）

審查範圍：`manuscript.md`、`supplementary_methods.md`、`response_to_reviewers.md`、`cover_letter.md`，逐條對照原始審稿文字。只檢查四份檔案之間的一致性與回應切題度；未重跑任何數據，未核對 PDF 頁碼。

## 一、總評

修訂稿對全部 25 項意見都有實質回應，沒有真正未回答的要求。需要補強的只有三處小缺口：

- R1‑major‑10 的回覆沒有回答審稿人明確提出的「請說明為何保留小腦作代理組織」，只是替它貼了標籤。
- R3‑3 的回覆只交叉引用 R1‑major‑5，沒有向 Reviewer 3 直接陳述權重理由。
- 稿件 Background 兩處仍留有「disease‑specific tissue‑weighted / tissue weighting」字樣，與 R1‑major‑10 回覆中「已改為 retina/proxy expression」的承諾相抵觸。

其餘改善空間都在文字層面：稿件各段末尾反覆出現的免責句（同一限制在 Methods、Results、Limitations 各說一次以上），以及回覆中少數迂迴句。科學限制已經揭露到位，不需再加新的警語；應做的是把同一限制集中說一次。修正上述項目後即可上傳。

## 二、適切性矩陣

評等：✔ 充分；✔− 充分，建議微調文字；△ 已回應但缺一句直接答覆。

| 編號 | 審稿要求核心 | 回覆切題 | 稿件落實 | 評等 |
|---|---|---|---|---|
| Editor | 結果準確、結論不過度、限制充分 | 是 | Abstract/Conclusions/Limitations 一致 | ✔ |
| Reviewer 2 | 圖檔無法存取 | 是；嵌入圖與圖檔，入口檢查待辦已揭露 | 圖例完整 | ✔ |
| R1‑M1 | 定義預測任務；Usher/SYSCILIA 分開報告 | 是，明確選「sensory/ciliary hypotheses in the Usher context」 | Abstract、Table 3、Fig 4/5、Conclusions 皆分開；mantis‑ml 段仍合併（已說明） | ✔− |
| R1‑M2 | HIGH 校準與評估不獨立 | 是；承認、改稱 heuristic、temporal split 結果弱 | Abstract 已分 raw score 與 gated HIGH | ✔ |
| R1‑M3 | 直接呈現 control 最終層級、流失原因、閾值敏感度 | 是，2/7/0/0 與 1/27/0/0，Table 3 逐基因 | 落實於 Results | ✔ |
| R1‑M4 | 配對陰性對照 | 是，111 對凍結配對；110/111 已在 raw 門檻失敗 | Results + S5 | ✔− |
| R1‑M5 | 權重啟發式；簡單基線；top‑K 持續率 | 是，等權/單層/留一層/8‑17‑41 | Methods + Sensitivity | ✔ |
| R1‑M6 | 稀疏證據偏好 | 是，HIGH 全為 5–6 層；ρ=0.24 | Results | ✔− |
| R1‑M7 | 層間相關；整合是否優於最強單層；層內合併細節 | 大致是；「是否優於最強單層」未在本條直接答 | Methods 各層細節已補；S4 有結論 | ✔− |
| R1‑M8 | mantis‑ml 基準弱；temporal 驗證；簡單基線 | 是，且完整揭露 0/41、0/45、人工複核 | Results/Table 4/S6 | ✔− |
| R1‑M9 | 版本、時間戳、鎖定環境、指令、校驗和 | 是；容器一項未提及 | Methods/S7 | ✔− |
| R1‑M10 | 解釋小腦代理；表現層貢獻；移除代理影響 | 貢獻與敏感度有答；「為何選小腦」未答 | 稿件 61、82 行殘留舊措辭 | △ |
| R1‑m1 | 定義 seed‑free | 是 | Methods 138 行定義 | ✔ |
| R1‑m2 | confidence → priority tier | 是 | 全稿一致 | ✔ |
| R1‑m3 | canonical identifier 用語 | 是 | Gene universe、Additional file 1 | ✔ |
| R1‑m4 | 主文呈現 tier 分布 | 是 | Results | ✔ |
| R1‑m5 | 背景抽樣與 seed | 是 | Fig 5 圖例、S7 | ✔ |
| R1‑m6 | DOI 典藏 | 直接說明未做 | Data availability | ✔ |
| R1‑m7 | 縮短背景 | 是，列出變更並引用新文字；與稿件一致 | Background 已精簡 | ✔ |
| R3‑1 | 補參考文獻 | 是，[8–11] | Background | ✔ |
| R3‑2 | seed‑free 與事後校準 | 是 | 同 R1‑M2 | ✔ |
| R3‑3 | 權重理由；排序敏感度影響 | 理由只交叉引用 | Methods 130 行有理由 | △ |
| R3‑4 | 新基因預測的獨立證據 | 是，直接承認未建立 | Results/Limitations | ✔ |
| R3‑5 | 排除毛細胞資料的影響 | 是 | Limitations 375 行 | ✔ |
| R3‑6 | 一般重要性 vs 疾病特異性 | 是 | Negative controls、comparators | ✔− |

## 三、優先處理事項

### P1：上傳前必改

1. **R1‑major‑10 未回答「為何選小腦」**。審稿人原文：「the authors should explain this choice more clearly」。回覆只寫 “Cerebellum is an adult neural proxy, not auditory evidence”，稿件 `inputs/manuscript.md:114` 與 S3.1 也只標示性質，未給理由。四份檔案都找不到選擇依據，請作者補一句實際原因（替換文字見第四節，含待填欄位）。

2. **稿件殘留「disease‑specific tissue weighting」**。`inputs/manuscript.md:61`（“a disease‑specific tissue‑weighted Usher score”）與 `inputs/manuscript.md:82`（“disease‑specific tissue weighting”）隱含 UsherPipe 具備此特性，與 R1‑major‑10 回覆「已替換為 retina/proxy expression terminology」矛盾。改法見第四節。

3. **R3‑3 應直接陳述權重理由**。Reviewer 3 要求 “additional justification for the final predefined weights”，回覆寫 “We explain the limited design rationale for 0.20/0.20/…” 卻沒說理由是什麼，且 “limited design rationale” 自貶又含糊。Methods `inputs/manuscript.md:130` 已有理由（constraint/expression 各加五個百分點），回覆應複述一句。替換文字見第四節。

### P2：文字品質（建議改）

4. **稿件各段末尾反覆的免責句**。同一「不代表因果／不是獨立驗證」的限制在以下位置各出現一次以上，形成清單式警語：
   - Methods 各證據層段尾：`manuscript.md:116`、`:120`、`:122`、`:136`（最後一句）。
   - Results「Top candidate genes」：`:229`、`:231`、`:233` 每個基因各附一句否定。
   - 「Negative controls」：`:261`、`:263`、`:265` 三次說 gate 不證明一般特異性。
   - 「Comparison with mantis‑ml」：`:337`、`:339`、`:341`、`:343` 四次說不是基準。
   
   Limitations（`:367–379`）已是集中陳述處，應保留。建議把各段尾的否定句刪除，每節留一句總結；證據層段落可用第四節的一句合併語取代。這不刪任何科學限制，只把它說一次。

5. **稿件正文出現修訂流程用語**。`manuscript.md:92`（“The revision preserves the submitted scores…”）、`:164`（“The revision package supplies…”）、`:273`（“prompted by independent AI‑assisted methodological review”）是給編輯看的流程敘述，不是期刊正文。改為 “This study preserves…”、“We supply…”、“A post‑outcome diagnostic retained every frozen pair…”。

6. **R1‑major‑8 第三段開頭迂迴**。“Concerns about PDIA6, VWA8 and PLCG1 require interpretation across reports” 沒說是什麼 concern。改為直接句（第四節）。其餘內容正確，且與 S6.6 的 2/2/3 下限、「仍在審查、未排除」一致。

7. **R1‑major‑7 缺一句直接答覆**。審稿人問整合模型是否「provides information beyond the strongest individual components」。答案已在 R1‑major‑8 與 S4（“has not been shown to outperform the strongest layer”），本條應補一句（第四節）。

8. **R1‑major‑9 容器一項未提**。審稿人列為 “ideally”，屬可選，但回覆完全未提。補半句即可（第四節）。

### P3：可選微調

9. 回覆用語：R1‑major‑6 “actually have” 改 “have”；R1‑minor‑1 “explicitly permits known‑gene annotations” 改 “acknowledges that known‑gene annotations enter the score”；R1‑major‑4 倒數第二句的四項並列警語可縮為 “S5 discusses the remaining limitations of two‑covariate matching and shared curation.”
10. R1‑major‑1 第二段關於 temporal cohort 的內容與 R1‑major‑8 重複，可縮為一句交叉引用。26/28 SYSCILIA 重疊在 R1‑major‑2、R1‑major‑7、R1‑minor‑1 三處重述，後兩處可只引用。
11. Abstract Results（`manuscript.md:21`）數字密度高，“provisionally literature‑screened” 讀者難解。可刪「Paired control advantage fell to…」與「only 41 default top‑100 genes…」兩句（數字仍在 Results），並把 “provisionally literature‑screened” 改為 “literature‑screened”。可選。
12. 內部術語：S3.1 “Phase 2 expression audit”、S4 “Phase 2”、S5 “phase3_roster / phase4_spec.md”、回覆 R1‑major‑4 的 Changes/evidence 檔名，審稿人無法對應；建議以 Additional file 11 的描述取代。稿件 `:279`、`:333`、`:357` 的 “artifact” 改 “output” 或 “analysis”。「Old‑versus‑new impact audit」（`:331–333`）是內部 QC，不回應任何審稿意見，可移入補充。
13. Figure 7 圖例首尾兩次說 top‑100 Spearman 是 conditional，刪一次。

## 四、替換文字（英文）

**R1‑major‑10 回覆，第一段**（第二段保留）：

> We have replaced “Usher‑specific tissue weighting” with “retina/proxy expression layer” throughout, including Table 1. Cerebellum was retained because [AUTHORS: state the actual reason; none of the current files gives it]. It is an adult neural proxy, not auditory evidence. No cochlear hair‑cell measurements enter production scoring, so genes with auditory‑restricted or developmentally restricted expression can be disadvantaged when other evidence is also limited. The fetal GSE135913 views are exploratory annotations within the already selected HIGH tier and do not close this gap.

**稿件 `manuscript.md:61`**：

> Neither published description includes a retina/proxy expression layer or a gnomAD constraint layer.

**稿件 `manuscript.md:82`**：

> …and phenotype matching is not treated as a retina/proxy expression layer.

**稿件 `manuscript.md:114`，在 “Cerebellum is an adult neural proxy” 前加一句**：

> Cerebellum was retained as [reason]; it is an adult neural proxy, not cochlear evidence.

**R3‑3 回覆（整段替換）**：

> The weights are heuristic. Constraint and expression receive 0.20 each for general functional relevance and sensory‑tissue plausibility; the four remaining layers receive 0.15 each (Methods, “NULL‑aware composite scoring”). We do not claim that this configuration is optimal. Equal‑weight, single‑layer and leave‑one‑layer‑out baselines, together with top‑25/50/100 persistence, show that high whole‑ranking correlation (0.9598–0.9994) coexists with substantial shortlist movement: only 41 of the default top‑100 genes persist across all 25 modest configurations. Animal‑only scoring recovers more Usher controls (4/9 at top 100) and literature‑only scoring more SYSCILIA controls (21/28) than the default. Logistic‑regression weighting changes the ranking substantially (ρ = 0.646) and was not adopted because it fits and evaluates on the same controls and risks over‑specialization. Candidate prioritization is therefore weight‑dependent; per‑gene layer contributions are reported so that users can re‑rank under alternative weights. See R1‑major‑5 and Results “Sensitivity analysis”, S2 and S4.

**R1‑major‑8 回覆，第三段前兩句**：

> Human review raised family‑evidence concerns for PDIA6, VWA8 and PLCG1. The initial PDIA6 report described one family; the earlier VWA8 report concerned a developmental disorder in one family, whereas the temporal target was a later retinal association; PLCG1 had a single‑family immune‑disorder report and a later auditory/ocular multisystem report with four families.

**R1‑major‑7 回覆，段末加一句**：

> On the internal controls, the integrated score has not been shown to outperform the strongest single layer: animal‑only recovers more Usher controls and literature‑only more SYSCILIA controls at top 100 (R1‑major‑8; S4).

**R1‑major‑9 回覆，第一段末加半句**：

> No container image is provided; the tested dependency lock and replay commands serve as the equivalent reproducible setup.

**稿件 Methods「Evidence layers」節末合併語**（取代 `:116`、`:120`、`:122` 段尾否定句與 `:136` 最後一句）：

> All six layer scores quantify the availability and strength of measured or curated evidence, not gene–disease causality. Annotation and literature scores reflect research depth, and animal‑model and literature evidence can draw on the same disease‑curation sources; these dependences are examined in Results.

## 五、已核對、未漂移的科學事實

- Raw scoring 無訓練標籤或相似性種子；HIGH gate 受 controls 影響，全稿一致稱 heuristic priority tier。
- Temporal：截止 2020‑12‑31；45 例 = 41 coding + 4 noncoding；兩版 top100/HIGH 均 0/41、0/45；Abstract、Results、Table 4、回覆、cover letter 數字一致。
- 人工複核涵蓋全部 45 例；PDIA6/VWA8/PLCG1 累積目標家系下限 2/2/3，仍在審查，未排除、未核准；S6.6、回覆、Limitations 一致。
- CRLS1/CTNND1/DHRSX/RNU 作為「廣義感覺目標」示例；GO 為事後描述、無 FDR 顯著。
- 工作表未附、DOI 未鑄、mantis‑ml 未重跑、期刊入口圖檔檢查待辦，均已揭露。
- R1‑minor‑7 回覆所述變更與引用句（`manuscript.md:41`）與稿件相符。
- 參考文獻 [1]–[66] 依序出現；comparator、persistence、correlation 等數值在 Abstract、Results、S4/S5 與各回覆間一致。
