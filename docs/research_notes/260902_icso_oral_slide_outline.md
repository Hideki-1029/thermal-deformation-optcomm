# ICSO 2026 口頭発表　本編13枚の構成ノート

- 作成: 2026-09-02
- 改訂: 2026-09-12（先行研究の位置づけを本編前半に追加し、表示情報を整理）
- 発表: ICSO 2026, Paper 293, oral, session *PAT and Receiver Technologies*
- 日時: 2026-10-15（セッション枠 16:20–17:40、持ち時間 **15分発表 + 5分質疑**）
- 画面: 16:9、英語、MS PowerPoint または PDF。テンプレは光RG `20260721_optcommrg_takamoto_v3_issl.pptx` の ISSL 形式を流用
- 数値・主張の正本: 提出稿 `papers/icso/main_en.typ` / `papers/icso/260820_final_submittion/293_Takamoto.pdf`
- 光RG 54枚は骨格と型だけ流用し、中身は本ノートから新規作成する。v3 の日本語本文・旧PAT秒・Adaptive主主張は使わない
- 関連: [`260721_rg_slide_retrospective_and_paper_narrative.md`](260721_rg_slide_retrospective_and_paper_narrative.md)、[`260816_icso_compact_paper_outline.md`](260816_icso_compact_paper_outline.md)、[`papers/icso/official_author_instructions_ja.md`](../../papers/icso/official_author_instructions_ja.md)

---

## 0. 固定した方針

- 本編 **13枚**（タイトル含む）。話すのはこれだけ。裏は質疑用で、時間内には進まない
- 1枚1メッセージ。タイトルはその場で図と数字が支える結論形（英語）
- 聴衆は PAT／受信機。STOP の操作説明より、初期指向誤差と捕捉時間
- 主結果は階層 sun-face ΔT モデルによる **捕捉前 feedforward**。残差 Fourier は予備なので本編に入れない
- 関連研究の専用スライド／全文献表は本編に置かない。ただし Slide 2 の下部で、**既存の光通信PAT／既存の温度ベースLOS補正／本研究**の位置づけを30秒で明示する。詳細表は裏 B8
- 数字は提出稿。光RGの 124.6 s / 156.9 s、走査 40/25 µrad、単位 °C は使わない
- Constant-bias only は未計算。取れ次第、裏 B7 か本編11の横に足す。構成は空けておく

時間配分の目安（台本上 **13分30秒**。遷移・図示・言い直しを含めて14分以内をリハーサル目標とし、残りをバッファにする）:

| 枚 | 役割 | 目安 |
|---|---|---|
| 1 | 題 | 15 s |
| 2–3 | 問題・位置づけ・LOS定義 | 2 min 15 s |
| 4–5 | 解析と観察 | 2 min |
| 6–8 | モデルと予測精度 | 3 min 45 s |
| 9–11 | PAT | 3 min 30 s |
| 12–13 | 限界と結論 | 1 min 45 s |

---

## 1. 本編13枚

各枚は次の欄で書く。

- **Title**: スライド上の英語タイトル案
- **On slide**: 図・式・数字（少なく）
- **Say**: 口頭で足すこと。スライドに全文を書かない
- **Do not**: この枚に載せないもの
- **Source**: 提出稿の対応箇所

---

### Slide 1 — Title

- **Title**: Hierarchical Prediction and Feedforward Correction of Time-Varying Thermal Line-of-Sight Bias for Coarse Acquisition in Satellite Optical Communications
- **On slide**: 提出稿と同じ題（改行位置も論文に合わせる）。著者、所属、Paper 293、ICSO 2026。Adaptive は題に入れない
- **Say**: 名前と所属だけ。中身は2枚目から
- **Do not**: 日本語副題、光RGの日付、Adaptive を並列した旧題
- **Source**: `main_en.typ` 題名

---

### Slide 2 — Problem

- **Title**: Thermal LOS bias can dominate the coarse-acquisition scan before optical feedback is available
- **On slide**: 上部80%は光RG v3 の問題図を英語化して流用してよい（Uncertainty region → 熱LOS → 予測を scan center から引く）。熱LOSのオーダー **150 µrad to >1 mrad**。他誤差の目安を小さく横に置く:
  - 軌道予測（TLE）: 数百 µrad
  - STT 姿勢・較正済みアライメント: 数十 µrad
  - 熱: 太陽面と発熱次第で上記以上になり得る
- 下部20%に、文献名の羅列ではなく次の3行の **positioning strip** を置く。小さな2列（Thermal LOS prediction / Acquisition evaluation）でもよい:
  - Optical communication / PAT: thermal error is mainly absorbed or reduced; acquisition is evaluated
  - EO / JANUS thermal correction: temperature-based LOS correction is demonstrated; acquisition is not evaluated
  - **This work: bus-relative STT–LCT prediction + coarse-acquisition evaluation**
- 引用は各行末かスライド脚注に代表例だけを小さく置く。光通信: Kaushal / Shi / Zhang、温度補正: Hu / Li / Turella。著者名は口頭では読まない
- **Say**: 粗捕捉では相手光のFBがまだなく、不確定域の面積が点数と時間を決める。熱は既知の運用条件（食、太陽面、被覆、内部発熱）に支配されるので、未知外乱としてすべて掃く必要はない。位置づけは次の3文で30秒以内:
  1. *Temperature-based LOS correction itself is not new; it has been studied for Earth-observation and deep-space optical instruments.*
  2. *Representative optical-communication studies have mainly absorbed or reduced pointing uncertainty through PAT and structural design.*
  3. *This work connects the two by predicting bus-level STT–LCT thermal LOS and applying it to coarse-acquisition feedforward.*
- **Do not**: PAT全体の教科書、トラッキング、ビーコン設計の詳細、個別論文の逐次紹介、論文の関連研究表をそのまま縮小
- **Source**: Introduction、Related Work and Positioning、Table 1。図は論文 Figure 1 と同趣旨。光RG slide 4 の図が近い

---

### Slide 3 — LOS definition

- **Title**: The far-field quantity is the LCT optical-axis rotation relative to the STT
- **On slide**: 論文のLOS定義図（STT on PZ、LCT on MZ、相対回転）。式は1つだけ:
  \[
  \boldsymbol{\theta}_\mathrm{th} = \boldsymbol{\theta}_\mathrm{LCT} - \boldsymbol{\theta}_\mathrm{STT}
  \]
  一言: 並進による centerline tilt は遠方リンクでは距離で割れて無視。二次指標
- **Say**: STT自身の熱回転は姿勢基準の回転に吸収される。通信軸の誤差は、STTに対するLCT光軸の相対回転である。これが scan center の熱オフセット
- **Do not**: 6成分変位の表、拘束条件、剛体フィットの議論（裏 B5）
- **Source**: §3、Figure 2。代表節点回転であることは聞かれたら裏

---

### Slide 4 — Analysis setup

- **Title**: A box-structure LEO bus is analysed across 21 operating conditions
- **On slide**: 衛星メッシュ／温度場の1枚（論文 Figure 3）。右に最小スペックのみ:
  - 外形 0.6 m × 0.6 m × 1.0 m、A5052、基準温度 24 °C
  - STT on PZ、LCT on MZ、boresight ≈ −Z
  - 21 conditions: sun face（MX/MY/PX/PY）× dissipation × surface/orbit variants
  - 流れの1行: Thermal Desktop 温度場 → Femap 回転 → 相対LOS
- **Say**: 特定機の設計審査ではなく、同一構造で条件を横断する評価。内部発熱の代表は PROP 25 W on PY、PCDU 10 W on MY。太陽面、発熱、被覆、COLD/HOT/LTAN18を変える。評価IDと除外ケースは読まず、聞かれたら裏 B1
- **Do not**: 評価IDの列挙、除外ケースの説明、軌道パラメータの全表、API／case_matrix の自動化、材料定数の全部
- **Source**: §4–5、Tables 2–4、Figure 3

---

### Slide 5 — Observations

- **Title**: Thermal LOS varies at the orbital period; the dominant axis and DC offset follow the sun face
- **On slide**: Case 04（MY、全発熱）の温度とLOS時系列（論文 Figure 4）。観察は3点、短く。太陽面別の4レンジは文章で並べず、図中ラベルまたは最小の模式図で示す:
  1. 温度と熱LOSは同じ軌道周期
  2. 支配軸は MY/PY で y、MX/PX で x。生RMSの全体幅を **150–1280 µrad** と大きく示す
  3. 被覆は振幅と残差床、内部発熱はケース間の平均バイアス
- **Say**: MYは比較的小さく、PYは最大級。必要なら口頭で MY 150–265 µrad、PY 1180–1280 µrad だけを補足し、4面のレンジを全部は読まない。だからモデルは、太陽面を陽に持ち、軌道内の時変とケース間DCを分けなければならない。次の階層はその最小形
- **Do not**: この枚で \(a\Delta T+b\) を先に出す。観察が先
- **Source**: §5、Figure 4

---

### Slide 6 — Hierarchical model

- **Title**: Orbital variation is \(a(\mathrm{sun})\,\Delta T\); the DC term is predicted from sun face and dissipation
- **On slide**: 論文 Figure 5 の3箱を主役にし、**orbital variation** と **case-dependent DC** の分離が一目で分かる配置にする。3式を同じ強さで並べない:
  - 中央に最も大きく置く主式:
  \[
  \theta_\mathrm{dom}(t)\approx b_\mathrm{case}+a(\mathrm{sun})\,\Delta T(t)
  \]
  - \(\Delta T\) の定義は入力箱の中に小さく置く:
  \[
  \Delta T(t)=T_\mathrm{sunface}(t)-T_\mathrm{opposite}(t)
  \]
  - DCモデルは下段の小さな箱に置く:
  \[
  b_\mathrm{case}\approx b_0(\mathrm{sun})+c_\mathrm{prop}I_\mathrm{prop}+c_\mathrm{pcdu}I_\mathrm{pcdu}
  \]
  - 固定16係数は隅に小さく置く。非支配軸のDCと約 −600 µrad は必要なら口頭または裏へ
- **Say**: TD/Femap を毎回オンボードでは回せないので、入力をパネル中心温度差と運用フラグへ落とす。Slide 2 で位置づけたとおり、温度差とLOSの一次関係自体は既報。ここで見せる新規性は、分離したSTT–LCTのバス相対LOS、条件横断のDC、粗捕捉への接続。係数値の他構造への普遍性は主張しない
- **Do not**: 3式を同じ大きさで見せる、Level-1/2 の学習フローチャート全体、取付点温度を足した失敗例（裏でも可）
- **Source**: §6、Eqs. 3–6、Figure 5

---

### Slide 7 — Cross-case accuracy

- **Title**: Nested leave-one-case-out RMSE is 4.9 µrad (median) against 615 µrad raw RMS
- **On slide**: 論文 Figure 6。左: 太陽面ごとに固まる \(a_\mathrm{emp}\)（共有感度 MX/MY/PX/PY = +30.6, +28.6, −28.1, −28.7 µrad/K）。右: \(b_\mathrm{emp}\) vs \(b_\mathrm{pred}\)、支配軸バイアス RMSE 3.1 µrad in-sample / 3.8 µrad LOO。本文数字:
  - 21ケース、nested LOO（テストケースを \(a_\mathrm{shared}\) と両軸 Level-2 から除外）
  - 支配軸 test RMSE: median **4.9 µrad**、mean **5.5 µrad**
  - 生LOS 支配軸 RMS median **615 µrad**
- **Say**: 係数はテストケースを知らなくても、1–2桁落ちる。標準COLDではおおむね 3–7 µrad。難しいのは Black（≈13 µrad）、HOT（数µradのDC残り）、PROP半電力（≈16 µrad）。詳細は12と裏
- **Do not**: 全21行のRMSE表。mean と median を Abstract のように混ぜない。この枚は median 4.9 を主、mean 5.5 は口頭で補足可
- **Source**: §6、Table 5、Figure 6、Abstract/結論

---

### Slide 8 — Time-series example

- **Title**: Case 08 (PY, all units on): 1250 µrad raw RMS falls to 3.9 µrad test RMSE
- **On slide**: 論文 Figure 7。図中タイトルが解析ログなら、スライド用に消すか短くする。本文と揃える数字は **raw RMS 1250 µrad、test RMSE 3.9 µrad**（図ファイル内が 1252 でも口頭は 1250）
- **Say**: PY は生LOSが最大級。\(b_\mathrm{pred}+a_\mathrm{shared}\Delta T(t)\) で軌道変動を追う。これが次のPATで効く理由
- **Do not**: 他ケースの時系列を並べる。1例でよい
- **Source**: §6、Figure 7

---

### Slide 9 — PAT connection

- **Title**: The prediction is subtracted from the scan center before the rectangular spiral starts
- **On slide**: 論文 Figure 8 の流れ（TD/Femap truth → 階層モデル → \(\boldsymbol{\theta}_\mathrm{scan}=\boldsymbol{\theta}_\mathrm{nom}-\hat{\boldsymbol{\theta}}_\mathrm{th}\) → 矩形スパイラル）。幾何は3行:
  - 範囲 ±1600 µrad
  - ステップ 120 µrad、検出半径 150 µrad（ビーコン級、重なり60%）
  - dwell 0.1 s/点、最大 729 点
- **Say**: 真の目標が検出円に入った時点を捕捉とする。時間は残差不確かさの実用proxy。スイープ・整定・確率検出は無視。スキャン軌跡の図は裏 B2。比較は no correction / 階層モデル / thermal truth（熱のみの上界）
- **Do not**: 光RGの 40 µrad / 25 µrad。軌道誤差のブロック図3枚
- **Source**: §7.1、Table 6、Figures 8–9

---

### Slide 10 — PAT, thermal only

- **Title**: With thermal error only, mean acquisition time falls from 14.6 s to 0.10 s
- **On slide**: 14 COLD・標準表面（Cases 4–6, 8–9, 13–21）。301 epoch × 3軌道、ケース平均の平均。表または棒:
  - No correction: **14.6 s**、成功率 100%
  - Hierarchical ΔT: **0.10 s**、100%
  - Thermal truth: **0.10 s**、100%
  - 補正後の平均熱残差 **9.3 µrad** ≪ 150 µrad → ほぼ1点目で捕捉
- **Say**: これは熱モデル単体の能力。thermal truth に到達しているのは、残差が検出半径より十分小さいから。主結果は次の非熱込み
- **Do not**: 光RGの 124.6 s。非熱の数字をこの枚に混ぜない
- **Source**: §7.3、Table 7

---

### Slide 11 — PAT, with nonthermal error

- **Title**: With nonthermal error, the search floor is no longer thermal: 19.2 s to 5.45 s
- **On slide**: 同じ14ケース、非熱は1 seed/ケース（MCなし）:
  - No correction: **19.2 s**、成功率 **98%**
  - Hierarchical ΔT: **5.45 s**（約72%減）、**100%**
  - 補正後の平均初期誤差 **448 µrad** ≈ 非熱
- 太陽面の1行（口頭のフック）: MY は熱が 150–260 µrad で改善は小さい。PY は熱 ≈1.2 mrad で **37.3–39.5 s・成功率 88–97% → 1.3–1.8 s・100%**
- **Say**: 方法の役割は全指向誤差を消すことではない。大きい時変熱バイアスを落とし、探索負担を非熱の床まで下げる。軌道予測と熱はどちらも軌道周期族なので、捕捉後に周波数だけでは熱を分離できない。だから捕捉前の温度・運用FFに意味がある。非熱の内訳（TLE–POEORB、アラインメント \(1\sigma=50\) µrad 等）は裏 B3
- **Do not**: 光RGの 156.9→59.6 s。Adaptive をこの枚の結論にしない。Constant-bias がまだなら空欄のまま
- **Source**: §7.2–7.3、Table 7

---

### Slide 12 — Limitations

- **Title**: The evaluation is numerical on one box structure; several floors remain
- **On slide**: 箇条は4つまで:
  1. 真値とモデルが同一の TD/Femap 機械。LOO はケースを外すだけで、構造・LOS定義は共有
  2. LOS は代表節点回転。取付面の剛体フィットは未実施
  3. Black / HOT / 半電力で残差が上がる。被覆・軌道・連続発熱は Level-2 未導入
  4. 非熱とスキャンは簡略。地上試験なし。残差 Fourier は2ケースの予備（全指向残差、疎サンプル未実証）
- **Say**: 係数 \(a\approx30\) µrad/K は本構造・配置・LOS定義に固有。センサ 0.1 K の ΔT 誤差は約 3 µrad。他機へは再同定が必要。残差更新の中身を聞かれたら裏 B4
- **Do not**: 今後課題の長いリスト。Adaptive 推定器の設計図
- **Source**: §6 限界、§7.4、§8

---

### Slide 13 — Conclusion

- **Title**: Predictable thermal bias can be removed before acquisition; the remaining search is set by nonthermal error
- **On slide**: 定量は3行だけ:
  - nested LOO median RMSE **4.9 µrad** vs raw RMS **615 µrad**
  - 熱のみ **14.6 → 0.10 s**
  - 非熱込み **19.2 → 5.45 s**、成功率 98% → 100%
- 締めの1文: 評価条件下では、光FB前の衛星光リンク確立を速くし得る
- **Say**: 新規性は一次の温度モデルそのものではなく、バス相対LOSへの適用、係数共有、捕捉時間への接続。ご清聴＋質疑へ
- **Do not**: 新しい数字、残差 Fourier の表、将来計画の羅列
- **Source**: 結論段落

---

## 2. 裏スライド（質疑。本編では開かない）

枚数は話さない。ファイル末尾に置き、想定問と対応づける。

| ID | Title（案） | 中身 | 想定問 |
|---|---|---|---|
| B1 | Case matrix | 21ケース要約。13–21 は 4×3 の一部、残りは 06 と 23–24。欠番 01–03, 07 | ケース数・欠番 |
| B2 | Scan geometry | 論文 Figure 9。120 µrad ステップ、150 µrad 検出円、27×27 | 走査が粗い／穴 |
| B3 | Nonthermal error | TLE vs POEORB をリンク横断面へ。アラインメント・姿勢 \(1\sigma=50\) µrad、ドリフト 30 µrad / 900 s。1 seed | 非熱の根拠、MCしていない |
| B4 | Residual Fourier | 本節は数値実験。観測は捕捉成功後の全指向残差。Case 13/16 の表。初周は FF、周1以降 ≈0.4 s。いきなり Fourier は PY 初周 39.5 s | Adaptive は？熱残差の測り方 |
| B5 | Attitude extraction | 代表節点回転は代理。取付面LS剛体フィットは今後 | 高嶋FBと同じ |
| B6 | Hard cases | Black ≈13 µrad、HOT のDC、半電力 ≈16 µrad | 被覆・HOT は？ |
| B7 | Constant-bias only | 未計算。ΔT=0 のPAT列。取れ次第ここか本編11 | 改善の大半はDCでは？ |
| B8 | Prior work and positioning | 論文 Table 1 を再利用。光通信PAT／衛星バス熱変形／EO・深宇宙の温度補正／本研究を、thermal prediction と acquisition evaluation の2軸で比較 | 何が新しい？／JANUS、Shi、Zhangとの差は？ |

---

## 3. 光RG v3 から変えること（再掲）

| 項目 | 光RG v3（2026-07-21） | 本発表 |
|---|---|---|
| 枚数 | 本編約40 + Appendix | 本編13 + 裏 |
| 言語 | 日本語 | 英語 |
| 題 | Feedforward **and Adaptive** | Adaptive を題に入れない |
| PAT 熱のみ | 124.6 → 0.12 s 級 | **14.6 → 0.10 s** |
| PAT 非熱 | 156.9 → 59.6 s | **19.2 → 5.45 s** |
| 走査 | 40 µrad / 25 µrad | **120 / 150 µrad** |
| 単位 | °C が残る | 感度は **K** |
| 目的スライド | 今日レビューしてほしい | 置かない |
| 軌道誤差 | 本編3枚 | 裏 B3 の1枚 |
| 残差／Adaptive | 本編の議論点 | 裏 B4、本編12で「予備」とだけ |
| 関連研究 | 本編での整理が曖昧 | **Slide 2で30秒のpositioning strip、詳細は裏B8** |

---

## 4. 作り方メモ

- 新規 pptx を切る。v3 を英語化して削らない（旧数字が残る）
- テンプレ・章区切りスライドの青帯は使ってよいが、本編13に区切り専用枚は入れない（時間を食う）
- Slide 2 は問題図＋誤差オーダー＋下部positioning stripまで。表が読めないほど詰まる場合は、文献名を脚注へ落とし、3行の役割対比を優先する
- 図は提出稿 `papers/icso/figure/` を優先。ログタイトル付き matplotlib はスライド用にトリムする
- スライド提出は会議側 2026-10-19 まで。会場PCは Windows、16:9、標準フォント

## 5. 次の作業

1. 本ノートの Title 文面を1枚ずつ確定する（長すぎるタイトルは口頭用に短くしてよい。主張は変えない）
2. Slide 2 のpositioning stripを先に試作し、通常表示で3行が読めるか確認する
3. 英語本編13枚の pptx を新規作成
4. 余裕があれば Constant-bias を回して B7 を埋める
