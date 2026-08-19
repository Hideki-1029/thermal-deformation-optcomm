# ICSO英語稿　ハイフン表現の点検候補

## 対象と抽出条件

- 対象: `papers/icso/main_en.typ`
- 抽出日: 2026-08-19
- 英字のハイフン結合語: 117種類、307出現
- 引用キー、数式のマイナス、`150--265` のような数値範囲は除外した。
- このメモ作成時点で `main_en.typ` の修正は行っていない。

## 処理結果（2026-08-20）

- `main_en.typ` の題名、Abstract、本文、見出し、図表キャプション、表内文を全文点検した。
- `coarse-acquisition`、`orbit-prediction`、`dominant-axis`、`STT-relative`、`scan-center`、`within-orbit`、`optical-communication`、`inter-panel`、数値＋単位の不自然な連結は、open compoundまたは自然な句・節へ修正した。
- 指定用語の `hierarchical sun-face ΔT model`、`dominant / non-dominant axis`、`nested leave-one-case-out` は維持した。
- `line-of-sight`、`far-field`、`reduced-order`、`time-varying`、`sun-facing`、`signal-to-noise` など、文法上または専門用語上自然なハイフンは維持した。
- Typstを再コンパイルし、`main_en.pdf` が16ページで生成されることを確認した。数値・論理・主張は変更していない。

## まず確認したい高頻度語

AI的な「複合語をとりあえずハイフンで繋ぐ」書き方に見えやすい群。原則として、open compound、前置詞句、関係節のいずれかに書き換える。

- [ ] `sun-face` — 21回（L46, 64, 82, 106, 131, 203, 242, 244, 258, 262, 276, 292, 304, 349, 355, 361, 364, 397）
  - 例外候補: 指定用語 `hierarchical sun-face ΔT model` に含まれるため、モデル名は維持する。一般文の `sun face` と切り分ける。

- [ ] `sun-facing` — 16回（L25, 82, 98, 100, 197, 203, 210, 219, 228, 237, 248, 309, 403）
  - 文法的には正しい複合形容詞。ただし頻度が高いため、`panel facing the Sun` や `sun face` との使い分けを確認する。

- [ ] `coarse-acquisition` — 12回（L32, 100, 104, 117, 148, 246, 260, 316, 318, 340, 361, 401）
  - 推奨: 指定用語どおり `coarse acquisition` に開く。

- [ ] `within-orbit` — 12回（L82, 106, 240, 242, 248, 254, 276, 309, 364, 401）
  - 推奨: `variation within an orbit`、`during an orbit`、`over an orbit` に分散して言い換える。

- [ ] `dominant-axis` — 10回（L240, 260, 262, 266, 281, 304, 312, 372, 407）
  - 推奨: 名詞は指定用語 `dominant axis`。修飾用法は `RMSE on the dominant axis` などに書き換える。

- [ ] `STT-relative` — 8回（L144, 148, 201, 206, 228, 237, 240, 254）
  - 推奨: `relative to the STT`、`with respect to the STT` を使う。

- [ ] `scan-center` — 7回（L66, 106, 110, 148, 156, 318, 322）
  - 推奨: `scan center` に開く。

- [ ] `orbit-prediction` — 6回（L96, 98, 102, 152, 345, 368）
  - 推奨: `orbit prediction error` に開く。

- [ ] `time-varying` — 6回（L25, 73, 260, 312, 314, 366）
  - 例外候補: 標準的な複合形容詞であり、題名と主要な対比では維持できる。過密な箇所のみ言い換える。

- [ ] `non-dominant` — 6回（L260, 266, 279, 290, 292）
  - 例外候補: 指定用語なので維持する。`non-dominant-axis` は別途書き換える。

- [ ] `far-field` — 6回（L140, 144, 146, 156, 206）
  - 例外候補: 光学の定着語として維持する。

- [ ] `leave-one-case-out` — 5回（L82, 106, 279, 304）
  - 例外候補: 指定用語 `nested leave-one-case-out` なので維持する。

- [ ] `optical-communication` — 5回（L115, 126, 131, 133, 136）
  - 推奨: `optical communication` に開く。

- [ ] `inter-panel` — 4回（L228, 250, 276, 295）
  - 推奨: `temperature difference between the panels` などに書き換える。

## 優先的に開く、または文を組み替える候補

### 条件間・ケース間の表現

- [ ] `across-case` — 3回（L240, 242, 276）
- [ ] `across-condition` — 2回（L106, 401）
- [ ] `cross-condition` — 3回（L106, 163, 304）
- [ ] `case-constant` — 3回（L248, 260, 401）
- [ ] `condition-dependent` — 2回（L117, 364）
- [ ] `dissipation-dependent` — 1回（L82）
- [ ] `sun-face-dependent` — 1回（L295）
- [ ] `all-dissipation` — 1回（L312）
- [ ] `all-Alodine` — 2回（L197, 219）
- [ ] `always-ON` — 2回（L210, 225）
- [ ] `baseline-surface` — 1回（L349）
- [ ] `axis-bias` — 1回（L349）
- [ ] `dissipation-flag` — 1回（L292）
- [ ] `internal-dissipation` — 1回（L276）

### 軸・LOS・指向誤差

- [ ] `non-dominant-axis` — 5回（L262, 266, 279, 295, 304）
- [ ] `pointing-error` — 3回（L98, 115）
- [ ] `beam-pointing` — 1回（L115）
- [ ] `communication-axis` — 1回（L140）
- [ ] `outgoing-axis` — 1回（L146）
- [ ] `reference-frame` — 1回（L140）
- [ ] `LCT-rotation` — 1回（L206）
- [ ] `STT-rotation` — 1回（L206）
- [ ] `STT-defined` — 1回（L156）
- [ ] `MY-panel` — 2回（L228, 237）
- [ ] `two-component` — 3回（L201, 240, 254）
- [ ] `six-component` — 1回（L187）

### 分析・時系列・評価区間

- [ ] `attitude-reference` — 1回（L163）
- [ ] `bus-level` — 2回（L104, 401）
- [ ] `spacecraft-bus` — 1回（L115）
- [ ] `communication-system` — 1回（L318）
- [ ] `finite-element` — 2回（L115, 127）
- [ ] `geometry-input` — 1回（L117）
- [ ] `in-orbit` — 1回（L167）
- [ ] `mounting-point` — 1回（L248）
- [ ] `laser-terminal` — 1回（L115）
- [ ] `training-orbit` — 1回（L279）
- [ ] `subsequent-orbit` — 1回（L82）
- [ ] `first-orbit` — 2回（L392, 395）
- [ ] `orbital-period` — 1回（L395）
- [ ] `post-model` — 2回（L312）
- [ ] `in-sample` — 1回（L304）
- [ ] `rectangular-scan` — 1回（L82）
- [ ] `state-based` — 1回（L136）
- [ ] `temperature-based` — 2回（L104, 117）
- [ ] `time-series` — 1回（L100）
- [ ] `temperature-difference` — 3回（L130, 295, 403）
- [ ] `temperature-to-LOS` — 1回（L117）
- [ ] `thermal-deformation` — 3回（L123, 133, 368）
- [ ] `thermal-deformation-induced` — 1回（L82）
- [ ] `thermoelastic-analysis` — 1回（L203）
- [ ] `thermal-truth` — 3回（L349, 361, 364）
- [ ] `reduced-order` — 3回（L64, 242, 322）
- [ ] `nonthermal-error` — 3回（L343, 366, 405）

### 捕捉前後・運用時点

- [ ] `post-acquisition` — 3回（L102, 115, 372）
- [ ] `pre-acquisition` — 1回（L372）
- [ ] `post-correction` — 1回（L368）
- [ ] `post-observation` — 1回（L345）
- [ ] `post-processing` — 1回（L187）
- [ ] `on-orbit` — 3回（L115, 124, 136）
- [ ] `link-establishment` — 1回（L96）
- [ ] `two-case` — 3回（L82, 395, 405）
- [ ] `one-to-two-order` — 1回（L314）

### 装置・分野・スキャンの表現

- [ ] `deep-space` — 2回（L117, 130）
- [ ] `Earth-observation` — 3回（L104, 117, 133）
- [ ] `optical-instrument` — 1回（L133）
- [ ] `beacon-class` — 2回（L327, 336）
- [ ] `mrad-class` — 2回（L327, 335）
- [ ] `cold-side` — 1回（L194）
- [ ] `full-power` — 1回（L314）
- [ ] `half-power` — 2回（L221, 314）
- [ ] `full-scan` — 1回（L338）
- [ ] `inter-point` — 2回（L340, 405）
- [ ] `received-power` — 1回（L340）
- [ ] `worst-case` — 1回（L338）
- [ ] `TLE-class` — 1回（L98）
- [ ] `several-hundred-microradian` — 2回（L206, 403）
- [ ] `sun-facing-to-opposite-panel` — 1回（L401）

## 技術用語・定着表現として維持が有力な候補

この群は、ハイフンが文法的または専門用語上自然。一括削除せず、周囲のハイフン密度が高い文だけ言い換えを検討する。

- [ ] `line-of-sight` — 3回（題名、Abstract、Keywords）
- [ ] `first-order` — 2回
- [ ] `half-width` — 1回
- [ ] `high-fidelity` — 1回
- [ ] `inter-satellite` — 1回
- [ ] `low-frequency` — 1回
- [ ] `mid-December` — 1回
- [ ] `non-negligible` — 1回
- [ ] `periodic-steady-state` — 1回
- [ ] `re-identification` / `re-identified` — 各1回
- [ ] `signal-to-noise` — 1回
- [ ] `structural-thermal-optical-performance` — 1回（STOPの正式展開）
- [ ] `wall-to-wall` — 1回（先行研究の表現）
- [ ] `y-axis` — 1回
- [ ] `Twenty-one` — 1回（数詞21の文頭表記）

## 数値＋単位のハイフン

文法上は複合形容詞として許容されるが、本稿では数が多く視覚的なハイフン密度を上げている。`a detection radius of 150 µrad` のように、名詞句へ書き換えるのが有力。

- [ ] `16-coefficient` — 1回（L82）
- [ ] `100-min` — 2回（L102, 345）
- [ ] `800-km` — 1回（L194）
- [ ] `693-km` — 2回（L194, 312）
- [ ] `6,050-s` — 1回（L195）
- [ ] `60.5-s` — 2回（L195, 395）
- [ ] `900-s` — 1回（L345）
- [ ] `0.2-s` — 1回（L327）
- [ ] `30-s` — 1回（L392）
- [ ] `30-µrad` — 1回（L345）
- [ ] `120-µrad` — 1回（L327）
- [ ] `150-µrad` — 2回（L327, 364）
- [ ] `1600-µrad` — 1回（L327）
- [ ] `0.3-mrad-class` — 2回（L327, 335）
- [ ] `1.3-mrad` — 1回（L334）
- [ ] `1-mrad` — 1回（L395）
- [ ] `0.1-°C` — 1回（L403）
- [ ] `Sentinel-1-like` — 2回（L194, 312）

## 本文修正の対象外

以下はコード識別子、メールドメイン、または住所の固有表記なので変更しない。

- `flow-node`
- `flow-arrow`
- `model-schematic`
- `pat-schematic`
- `problem-schematic`
- `spie-paper`
- `spie-table`
- `corresponding-email`
- `u-tokyo`
- `Bunkyo-ku`

## 確認時の提案順

1. 指定用語を固定する: `sun-face`、`non-dominant`、`leave-one-case-out`。
2. 開いても意味が変わらない語を一括修正する: `coarse acquisition`、`scan center`、`orbit prediction error`、`optical communication`、`pointing error`。
3. `within-orbit`、`dominant-axis`、`STT-relative` は、単純にハイフンを削らず文を組み替える。
4. 数値＋単位は、文法上正しくても密度が高い箇所を名詞句に書き換える。
5. 最後に `line-of-sight`、`time-varying`、`far-field` などの定着語を目視確認する。
