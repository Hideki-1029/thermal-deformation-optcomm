# 260816 ICSO フルペーパー コンパクト版 構成ノート

- 作成: 2026-08-16
- 対象: `papers/icso/main.typ`
- 目的: ICSO 2026 提出用フルペーパー（締切 2026-08-20）を、12–16 p のコンパクト版として書き切るための章立ての正本。
- 関係: 詳細版（ページ無制限・図 15 点）の構成は `[260802_update_main_typ_to_260721_slides.md](260802_update_main_typ_to_260721_slides.md)` に残し、修士論文の章の素案とする。本ノートはそこからの圧縮版。

---

## 0. 方針

- 目標ページ数: **12–16 p**（ICSO は 6 p 下限・上限なしだが、JANUS STOP 論文など 12 p 級が標準→ICSO 2022,2024のpaperを調査した結果、意外とばらつきがあり、最大で25pとかもあった。ただし、標準は10p代のためなるべくここに収める。よって今の目標は妥当）
- スケジュール: 8/16–17 の 2 日で第一稿を書き切る
- 論理構成（問題→LOS 定義→解析→観察→モデル→検証→PAT→残差更新→考察）は詳細版と同じ。**章を合体させて圧縮する**

### 削るもの（合意済み）

- 図の枚数: 15 点 → **8–10 点**
- 観察の冗長な記述（代表例で示し、列挙しない）
- 難しいケースの詳細（Black / half-power / LTAN18）は 1 段落＋数値のみ。図は載せない



### 削らないもの

- 解析条件表（再現性の根拠）
- case matrix 表（21 ケースの定義）
- limitations（主張の適用範囲の根拠）
- JANUS 差分表（新規性の根拠）

---



## 1. 章立て（各章の内容・短文）



### Abstract + Keywords

- 確定済み（2026-08-16 版）。FF 層の定量結果＋residual update の予備的結果まで入っている。
- **2026-08-16 注意: PAT の秒数は新スキャン幾何（ビーコン／粗FOV級、[`260816_coarse_acquisition_scan_geometry.md`](260816_coarse_acquisition_scan_geometry.md)）の値を使う。** 旧の密スキャン（124.6 s、156.9 s 等）は使わない。



### 1. Introduction

- 粗捕捉の初期指向誤差がリンク確立時間を左右する問題を提示。
- 熱変形 LOS を「予測可能な時変成分」として扱う立場、研究質問 3 点、貢献 3 点、適用範囲。
- 改稿済み。Figure 1（問題設定 schematic）を保持。



### 2. Related Work and Positioning

- 4 グループ（光通信 PAT／衛星バス熱変形／地球観測系 LOS 補正／JANUS）を短く整理。
- JANUS 2019 STOP + 2021 地上試験は新規性の根拠なので詳しめに残す。
- JANUS 差分表を保持。
- 改稿済み。



### 3. Problem Formulation and LOS Definition

- 補正対象＝STT 基準で見た LCT 外向き光軸の相対回転（far-field）。
- centerline tilt を PAT LOS に加えない理由を 1 段落で。
- scan-center 補正式と残差式（`θ_scan = θ_nom − θ_hat_th`、`e_scan = e_nonthermal + θ_true − θ_hat`）を定義。
- 図: LOS 定義の模式図 1 点（新規または概念図流用）。



### 4. Spacecraft Model and Thermo-Structural Analysis

- TD → Femap/Nastran → LOS 後処理の 3 段を 1 章で簡潔に（詳細版の 4 小節を圧縮）。
- 衛星モデル: 箱型バス、STT/LCT/PROP/PCDU 配置、代表モデルであることの明示。
- 解析条件: 軌道（LTAN06 800 km COLD 等）、サンプリング、材料・CTE、拘束条件は**表 1 点に集約**。
- 図: 衛星モデル＋機器配置 1 点。



### 5. Case Matrix and Observed Thermal-LOS Characteristics

- 21 ケースの定義（太陽面 × 発熱 × 被覆 × 軌道）を case matrix 表で。
- 観察は代表例で短く: 温度場と LOS が軌道周期で変化、太陽面で支配軸と符号が変わる、大きさは MY ~150–260 µrad／PX/MX ~0.6–0.9 mrad／PY ~1.2 mrad。
- 「軌道内時変 → ΔT、ケース間 DC → ケースバイアス」への橋渡しを最後の段落で。
- 図: 代表ケースの温度＋LOS 時系列 1 点。



### 6. Hierarchical ΔT Model and Cross-Case Validation

- Level 1（`θ_dom ≈ b_case + a_sun·ΔT`）と Level 2（`b_case ≈ b0 + c_prop I + c_pcdu I`）の式と階層模式図。
- モデル選択の根拠（局所温度特徴の追加が共線性・低 SNR で不安定化）は 1 段落。
- 同定手順（先頭 1 軌道で学習、中央値で共有化、LOO）を短く。
- 結果: 共有感度 28–31 µrad/°C、Level-2 係数表、LOO RMSE 3.8 µrad、最終 test RMSE 5.5 µrad。
- 限界（Black 床 13 µrad、HOT での DC ずれ）は数値のみ 1 段落。
- 図: a_emp 分布＋b_emp vs b_pred を 1 図に結合、代表時系列 1 点。



### 7. Coarse-Acquisition Simulation and Results

- **スキャン条件は新幾何（2026-08-16、[`260816_coarse_acquisition_scan_geometry.md`](260816_coarse_acquisition_scan_geometry.md)）**: ±1600 µrad、step 120 µrad、検出半径 150 µrad（ビーコン／粗FOV級、Shi ら 2023 参考）、dwell 0.1 s/point、被覆の穴なし。小さな表で。
- 秒は「この走査条件での proxy」と明記（Shi と同じ 0.2 s dwell なら約 2 倍）。
- 非熱誤差モデル（Sentinel-1 TLE vs POD の軌道誤差＋アライメント・姿勢・ドリフト）は簡潔に。周波数帯の解釈（熱と軌道が同帯域→事前 FF の意義）は残す。
- 結果表（17 ケース、4–6, 8–21）: 熱のみ（補正なし 12.1 s → 階層 bcase 0.10 s = 1 dwell = 真値上限と一致、成功率はともに 100%）、非熱込み（16.3 s / 98.3% → 4.75 s / 100%、約 71% 短縮）。
- ケース依存性は 1 段落: MY（熱 150–250 µrad）は検出半径にほぼ入り補正の本命ではない、PX/MX（~0.9 mrad）は補正なし ~9–12 s、**PY（1.2 mrad 級）は補正なし ~32–37 s（Shi の 30 s 要求と同オーダー）→ FF 後 ~1.5 s・成功率 100%**。「平均に加えて大きい太陽面で効く」と読めるようにする。
- 図: PAT フロー 1 点＋結果は表中心。



### 8. On-Orbit Residual Update

- 新設（詳細版ノートには無い章。abstract とタイトルの整合のため）。
- 身分の明確化: 熱モデル適応ではなく、捕捉後残差への運用補正。定数 δb と残差 Fourier（causal）を並べる。
- 「いきなり Fourier」との比較: PY では初周 365 s で実質失敗 vs FF→Fourier は初周 21.4 s。**階層 FF が初回を生かし、後段が周期床を削る**という役割分担が主張。
- 結果: case 13 で FF 単独 1.63 s → 残差 Fourier 0.78 s（causal、新スキャン幾何での再計算済み）。batch は解析上限として明記。
- 「いきなり Fourier」比較は**新幾何で再実行済み**（2026-08-16、`run_direct_fourier_comparison.py`、出力 `results/pat_acquisition/sunface_deltaT_bcase_los_model/pat_direct_vs_residual_fourier/`）。Level-2 は 17 ケース LOO。
  - case 13（MY）: FF 1.63 s / いきなり Fourier 1.39 s（初周 3.37 s）/ FF→Fourier 0.78 s（初周 1.58 s、周1+ 0.38 s）
  - case 16（PY）: FF 1.56 s / いきなり Fourier 13.16 s（**初周 39.5 s**、成功率 98.7%）/ FF→Fourier 0.76 s（初周 1.47 s、周1+ 0.40 s）
  - 主張: 熱が大きい PY ではいきなり Fourier の初周が 30 s 要求を超えて実質失敗。FF→Fourier は初回から FF 性能、2 周目以降は床 0.4 s。
- 割り引き（密サンプル 60 s、cyclic 軌道誤差、失敗点残差の混入）も正直に 1 段落。
- 図: case 13 の時系列または比較表 1 点。
- 参照ノート: `[260813_post_ff_residual_fourier.md](260813_post_ff_residual_fourier.md)`、`[260808_adaptive_two_layer_b_update.md](260808_adaptive_two_layer_b_update.md)`。



### 9. Discussion and Conclusion

- 研究質問 3 点への回答を箇条書き。
- JANUS との関係（原点通過 vs b_case、地上検証の有無）を短く。
- 共有感度は経験的結果であり一般化しない、モデル構造こそ移植可能という線。
- Limitations を主張と対応させて列挙（10 項目は圧縮して 5–6 項目）。
- 今後: HOT/COLD・被覆の Level-2 への明示的導入、residual update の全ケース評価、実験検証。

---



## 2. 図表の割り当て（計 図 8–9・表 5–6）

**作図方針（2026-08-16 合意）:** 直近のスライド `papers/seminar/20260721_optcommrg_takamoto_v3_issl.pptx` にある図は、スライドから切り抜いて PNG 化するなどして**積極的に流用**する。新規作図は最小限にする。

| 番号      | 内容                             | 章   | ソース候補 |
| ------- | ------------------------------ | --- | --- |
| Fig 1   | 問題設定 schematic（既存・Typst）       | §1  | main.typ 内の Typst 図 |
| Fig 2   | LOS 定義模式図                      | §3  | スライド流用（あれば）または概念図 `shared/figures/concept/` |
| Fig 3   | 衛星モデル＋機器配置                     | §4  | スライド切り抜き PNG |
| Table 1 | TD/Femap 解析条件                  | §4  | 新規（表） |
| Table 2 | case matrix（21 ケース）            | §5  | `cases/case_matrix.xlsx` から生成 |
| Fig 4   | 代表ケース温度＋LOS 時系列                | §5  | スライド or `results/femap_deformation/` |
| Fig 5   | 階層モデル模式図（既存・Typst）             | §6  | main.typ 内の Typst 図 |
| Fig 6   | a_emp 分布 + b_emp vs b_pred（結合） | §6  | スライド or `figure/p3_*` |
| Table 3 | 共有感度 + Level-2 係数              | §6  | 新規（表） |
| Fig 7   | PAT 評価フロー（既存・Typst）            | §7  | main.typ 内の Typst 図 |
| Table 4 | スキャン条件                         | §7  | 新規（表） |
| Table 5 | PAT 結果（熱のみ＋非熱込み）               | §7  | `results/icso/` から生成 |
| Fig 8   | residual update の結果（case 13）   | §8  | `results/.../pat_residual_fourier_smoke_causal/` |


---



## 3. 執筆順（2 日）

- Day 1 (8/16): §3–6（問題設定→モデル検証）
- Day 2 (8/17): §7–9（PAT→residual update→考察結論）＋図表配置＋数値照合＋コンパイル確認



## 4. 宿題（執筆とは別）

- 題名変更: ポータルには「アブスト・タイトルの変更は運営に連絡せよ」と明記あり。その対応で変更可能と確認済み。
  - 手順: 予稿がある程度固まりテーマに問題ないと判断した時点（8/17 日曜夜の予定）にメールを作成し、8/18 月曜に送信する（滝本さん対応）。
- 対応著者メールアドレス: ICSOS の IEEE 発行版論文（`docs/literature/ICSOS_IEEE_発行版_Defocus-Aware_Modeling_and_Control_Analysis_of_a_QD-Based_Optical_Tracking_System_Experimental_and_Simulated_Evaluation_Using_the_DOLCE_Terminal.pdf`）を参考にする。同論文では `takamoto@space.t.u-tokyo.ac.jp` を使用。


## 5. 高本によるレビュー

### 本outlineでの初版：main_260816.pdf を読んでの感想
- ABSTRACT
  - 全体の構成、内容はこれでよさそう（俺が伝えたい内容が含まれている）
  - 英語にしたときに改めて確認したいが、文章がちょっと長めかな？削るとしたら後半の結果の数値の部分の解説をもう少し抑えてもよさそう（=一部定性表現に変えて短縮？）
- 序論
  - 「特に粗捕捉段階では...」：粗捕捉と言ったときにカバー範囲が広く、精追尾のQD-FPM系までCCDによって追い込むことも粗捕捉ということがあるので、初期捕捉とかが表現としては適切？
  - 「本研究が着目するのは、低軌道 (Low Earth Orbit; LEO) 衛星の熱変形に起因する指向バイアスである」：ここの文、ないしその後にそれ以前に説明として存在していた「初期指向誤差」のwordを入れる方が分かりやすそう。つまり、熱ひずみによる指向バイアスが初期指向誤差の一部を占めることを説明したい。
    - あと、なぜこのSTT-LCT間の熱ひずみバイアスに注目したのか、理由をもう少し言いたい。メインはサイズと予測可能性だと思うけど。
    - 以前の発表でも、初期指向誤差に含まれるそれぞれの成分のサイズがざっくりどれくらいか（つまり熱ひずみによるLOS誤差は他の成分と比べてどれくらい大きいのか）はかなり突っ込まれたから、そこは丁寧に各成分のサイズを説明してもいいかも。
  - 「この相対姿勢変化は、粗捕捉開始時にはまだ光学フィードバックで補正されていないため、scan center のずれとして現れる」：scan centerが唐突。粗捕捉開始時の...とかつけるといいかも
  - 「従来のPAT検討では、初期指向誤差をまとめて確率的な不確かさとして扱うことが多い」：これはそうなの？不確かさとして扱った上で、スキャンやビーコン光の拡がり角の設計で不確かさを吸収するイメージだった。
  - 「本稿の中心的な立場は、観測された指向残差から熱変形成分だけを完全に分離することではなく、」：それはそうなんだけど、ここでそれをいきなり出すと、読者はなぜいきなり観測の残差から分離しようとする話しが出たのか疑問に思うかも
  - 「なお、熱LOSと軌道予測誤差は同じ軌道周期帯の周波数成分を持つため、観測後の単純な周波数分離で両者を切り分けることは困難である。だからこそ、温度と運用状態に基づく事前の feedforward 補正に意味がある。」：これも軌道予測誤差と分離する話しがいきなりで唐突かな。確か、初期指向誤差に含まれる様々な誤差の中で、最もサイズが大きいのが軌道予測誤差と熱ひずみ誤差？（：これは解析して出た値を根拠にするか、参考文献を引っ張るか）で、しかもその2つは周波数が近いから分離しづらいという文脈があった気がする（がその文脈がこの序論ではうまく説明できていない気がする）
  - 「。JANUS 光学ヘッドでは、構造の」：うーん。「JANUS光学ヘッド」という略称でうまく伝わるかな。アブストじゃないし、もう少し丁寧でもいいかも？
    - あーでも次の章で先行研究詳しくやるのか。ならいいか。
  - 「しかし、衛星バス上に離れて搭載されたSTTとLCTの相対LOSを対象として、その軌道内の時変成分とケース間のバイアスを分離して軽量に予測し、光通信粗捕捉の scan center 補正へ接続した枠組みは十分に整理されていない」：ここもう少し一般的な表現にして強くしちゃだめ？今の文だとかなりニッチなことをやっているように見える。例えば「衛星バス上で発生した熱ひずみ」
    - あ、あとこれ後の章の話しかもだが、なぜ今回光通信系ではなく衛星バス全体に注目しているかは、JANUSの先行研究を引用して示したい（JANUSでは、Zemaxも使って光学ヘッドと内部の光学系の両方に対して熱構造解析を行った結果、光学系でのひずみによるLOS変化よりも、全体の構造のひずみによるLOS変化の方がずっとサイズが大きい事を示している
  - 


