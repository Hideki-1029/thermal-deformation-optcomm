# ICSO 予稿 章立て（sunface_deltaT_bcase 本線）

- 作成: 2026-07-15
- 目的: ICSO full paper（日本語ドラフト → 英語 SPIE）の章立て・話すこと・必須図を固定する
- 前提モデル: `sunface_deltaT_bcase_los`（詳細: [`260714_sunface_deltaT_bcase_los.md`](260714_sunface_deltaT_bcase_los.md)）
- 根拠: 提出アブスト（`docs/research_notes/MD/ICSO_abstract_submitted/`）、`google_doc` メモ（〜7/12）、進捗振り返り（`260712_research_progress_retrospective.md`）
- 既存ドラフト: `papers/ICSO/main.typ` / `full_paper_story.md` は Fourier 先行の旧ストーリー。**本ノートの章立てで置き換える**
- **題名は提出アブストと同一**（ICSO ルール上そのまま出す必要がありそう）:
  `Feedforward and Adaptive Correction of Time-Varying Thermal Bias for Coarse Acquisition in Optical Communication Systems`

---

## 0. 論文の一本線

```text
熱 LOS は時変で粗捕捉に効く
  → TD/Femap で測れる
  → 共有 a·ΔT + 階層 b(太陽面, 発熱) でケース横断に予測できる
  → scan center FF で捕捉が楽になる
  → adaptive は第2層の枠（実装は薄くてよい）
```

### メインモデル（本文で主役）

```text
# Level 1（軌道内・時刻 t）
LOS_dom(t) ≈ b_case + a(sun_face) · ΔT(t)

# Level 2（ケース間・定数）
b_case ≈ b0(sun_face) + c_prop · I_prop + c_pcdu · I_pcdu
```

- `ΔT(t) = T_sunface_center − T_opposite_center`
- `a`, `b0_*`, `c_prop`, `c_pcdu` はケース横断の固定係数（計 10 スカラー）
- パッケージ: `src/pat_acquisition/models/sunface_deltaT_bcase_los/`

### 新規性の置き方（注意）

| 主張 | 新規性 |
|------|--------|
| `LOS = a·ΔT`（比例） | JANUS そのもの |
| `LOS = b + a·ΔT`（切片付き一次） | 統計・校正では普通 |
| 衛星バス **STT–LCT 相対 LOS**で、主説明変数が**太陽面−反対面 ΔT**、かつ `a` がケース横断で共有可能 | 差分の本体 |
| さらに **`b` を発熱 ON/OFF でケース間モデル化**し、固定少数係数で複数モードを説明 | JANUS 型には無い寄与 |

✗「切片付き ΔT モデルは世界初」  
○「JANUS 型の ΔT 一次関係が衛星バス相対 LOS でも成り立ち、感度 `a` はケース横断で共有可能。さらに ΔT に入りきらない DC をコンポ発熱で階層的に説明できる」

---

## 1. 章立て

ページ目安は SPIE 最低 6 ページ前後を想定した配分。

### §1 Introduction（~1 p）

話すこと:

- 粗捕捉は光フィードバック前 → 初期指向誤差が scan area / 捕捉時間を決める
- LEO では熱ひずみ由来 LOS が数十〜数百 µrad 級で時変しうる
- 熱を未知外乱ではなく、予測可能な時変バイアスとして扱う
- 貢献を 3 点で明示:
  1. 熱構造解析による STT–LCT 相対 LOS の定量
  2. **階層 ΔT モデル（共有感度 + ケースバイアス）**
  3. PAT への feedforward 接続と比較評価

言わないこと: 飛行実証済み、全軌道一般化済み

### §2 Related work（~0.5–0.8 p）

話すこと（短く）:

- JANUS: 光学機器で `LoS ≈ K·ΔT`
- Shi ら: STT–LCT 相対角を構造最適化で小さくする
- DLR 等: 光通信の body-pointing FF だが熱変形ではない
- 差分: **衛星バス相対 LOS × 太陽面 ΔT × 階層 `b` × 粗捕捉 FF**

### §3 Problem formulation / LOS definition（~0.5 p）

話すこと:

- 遠方通信 PAT 用 LOS = STT 基準で見た LCT 相対回転（far-field）
- `θ_scan = θ_nom − θ̂_thermal`
- 残差 = 非熱 + 熱真値 − 予測
- **すべての指向誤差を消す手法ではなく、予測可能な熱成分を減らす**と明記

参照: `docs/research_notes/femap_stt_lct_los_definition.md`

### §4 Thermo-structural analysis（~1.5–2 p）

話すこと:

- TD → Femap → LOS パイプライン（ケース行列で太陽面・被覆・発熱を振る）
- 代表結果: 支配軸・ptp 数百 µrad、太陽面で支配軸が変わる
- 感度は「モデル入力の物理説明」に必要なだけ（MY/PX の支配軸、被覆で ptp、発熱で mean/波形）

言わないこと: 全ケース巨大マトリクス、拘束領域の網羅感度

### §5 Hierarchical sunface ΔT model（**本命**・~1–1.5 p）

話すこと:

- Level 1 / Level 2 の式と、入力（ケース依存）vs 固定 10 係数の切り分け
- 設計原則（失敗から得たこと）:
  1. 軌道内の時変は **ΔT 一本**で足りる（`a` は面ごと固定）
  2. コンポ発熱の残りは **ケース定数 `b`** に出す（within-case 時系列に足さない）
  3. `b` のケース間差は、まず **太陽面 + 発熱 ON/OFF** の線形モデルで足りる
- 結果の核:
  - `|a| ≈ 28–31 µrad/°C`（符号は太陽面で決まる）
  - 標準ケース test RMSE ~数 µrad（生スケールから 1～2 桁低減）
  - LOO `b` RMSE ~2 µrad
- 限界を正直に: Black（床が上がる）、HOT（Level-2 未投入で `b` ずれ）、MZ 太陽指向など特異ケース

Fourier / 旧 `sunface_los` 3 特徴は本文の主役にしない（必要なら baseline 1 行）。

### §6 PAT evaluation（~1–1.5 p）

話すこと:

- 熱 LOS → scan center residual → 捕捉時間 の流れ
- 比較: no correction / static bias / **bcase 予測** / ideal truth（上界）
- 評価指標: 捕捉時間（＋必要なら success / scan area proxy）
- adaptive: アブスト整合のため「二層の第2層」を 1 段落。同列比較は必須にしない

**評価の切り分け（執筆方針）:**

- **熱LOSモデルの当てはまり**（数百 µrad → 数 µrad）は熱成分のみで語ってよい（§5）
- **捕捉時間・全体誤差**は非熱誤差込みを主報告にする。熱のみ 137→0.12 s は「モデルが熱を取りきれる」参考に留め、主数字は非熱込み（例: ~171→~22 s）

数字（17 ケース・LOO `b`）:

| 条件 | no | static | bcase | truth |
|------|-----|--------|-------|-------|
| 熱のみ（参考） | ~137 s | ~5 s | ~0.12 s | 0.10 s |
| 非熱込み（主） | ~171 s | — | ~22 s | — |

### §7 Discussion（~0.5–0.8 p）

話すこと:

- 言えること: 固定少数係数 + ΔT + 太陽面 + 発熱フラグで熱主成分を落とせる
- 言えないこと: 全軌道一般化、飛行実証、熱/非熱の完全分離
- JANUS 差分の再確認（式形の新規性を煽らない）
- 配置変更 proxy・コンポ温度時系列失敗は、必要ならここで短く補強

### §8 Conclusion（~0.3 p）

- 主張を 3 文で回収
- 今後: HOT/被覆の Level-2 拡張、adaptive 実装、地上試験は予稿後可

---

## 2. 構成上の判断（レビュー済み）

| 判断 | 方針 |
|------|------|
| Fourier / 旧 sunface | 主役にしない。baseline 程度 |
| コンポ温度を時系列特徴に入れた失敗 | §5 の設計原則か Discussion で短く（新規性の補強） |
| PAT 未接続のまま書くか | ~~数字待ち~~ → `run_pat.py` 済。§6 に no/static/bcase/truth を書ける |
| adaptive | 枠のみ。実装未完でもアブスト破綻にしにくい |
| 配置変更（パネル center proxy） | §4 か Discussion の 1 段落で十分 |
| 地上恒温槽試験 | 予稿必須ではない |

---

## 3. 必須図

### 3.1 自作・概念図

| ID | 図 | 中身 | 節 |
|----|-----|------|-----|
| **S1** | 問題設定 | 箱衛星 + STT/LCT + 太陽光 + 曲げ → 相対 LOS。下に scan center 補正式と「非熱は残る」 | §1 / §3 |
| **S2** | **階層モデル図（最重要）** | 上段: `ΔT(t)` → `a·ΔT`（時変）。下段: 太陽面・発熱フラグ → `b_case`。合流して `LOS_hat`。固定 10 係数を小さく表示 | §5 |
| **S3** | 評価系の流れ | TD/Femap truth → bcase 予測 → scan center FF → spiral → 捕捉時間。比較箱: no / static / bcase / truth | §6 |

任意:

| ID | 図 | コメント |
|----|-----|----------|
| S4 | 解析パイプライン | case_matrix → TD → Femap → LOS。再現性アピール。S3 と兼ねてもよい |
| S5 | ΔT の物理スケッチ | 対向パネル + ΔT → 差動膨張 → 曲げ → LOS（JANUS 差分の口頭説明用） |

### 3.2 結果プロット（既存から整形）

| ID | 図 | 中身 | 既存の当たり |
|----|-----|------|--------------|
| **P1** | 熱 LOS 時系列 | 代表 1 ケースで数百 µrad の時変 | `results/femap_deformation/*_far_field_los_angle_budget.png`（例: case04） |
| **P2** | 真値 vs 階層予測 | `b_pred + a_shared·ΔT` の当てはまり | `sunface_deltaT_bcase_los_model/timeseries/case08_bcase_true_vs_pred.png` 等 |
| **P3** | **横断性の本命図** | 面ごとの `a` 安定性、および `b_emp` vs `b_pred` | `bcase_a_emp_by_sunface.png`, `bcase_b_emp_vs_b_pred.png` |
| **P4** | PAT 比較 | no / static / bcase / truth の捕捉時間 | `sunface_deltaT_bcase_los_model/pat/pat_model_comparison.png` |
| P5 | オーダー感（任意） | 生 RMS/peak → モデル後 RMSE（例: 1250→3 µrad） | `bcase_raw_vs_model_rmse.png` |

`papers/ICSO/figure/` の旧図はストーリーが古いので差し替え前提。

### 3.3 最短セット

必須 5 点: **S1, S2, P1, P3, P4**

- PAT 数字がまだなら P4 を後回しにし、先に **S2 + P3** で §5 を固める
- 今は作らなくてよい: 全ケース巨大マトリクス、adaptive 詳細ブロック、Femap GUI 連発、LOS 動画（発表用）

---

## 4. アブストとの対応

提出アブスト（Rev.2）の約束:

1. 時変熱 LOS バイアスが粗捕捉に効く → §1, §4
2. 二層補正（物理ベース FF + adaptive） → FF は §5–§6、adaptive は枠（§6/§7）
3. シミュレーション評価（成功率・時間・scan area、no/static/feedback-only 比較） → §6（feedback-only は必須にしない／書けたら）
4. 新規性: 熱バイアスを予測可能な時変成分として粗捕捉に直結 → §5 + §7

---

## 5. 次アクション（執筆順）

1. 本ノートの章立てで `papers/ICSO/main.typ` の骨格を組み替え
2. 自作図 S1・S2 を先に作る（文章の骨格が決まる）
3. ~~P2・P3・P5 を bcase 結果から出力~~（済: `validate.py`）
4. ~~bcase → PAT 接続・P4~~（済: `run_pat.py` → `.../pat/`）
5. P1（熱 LOS 時系列）を論文用に再出力
6. 自作図 S1・S2
7. 日本語ドラフト → 五十里先生確認 → 英語 SPIE テンプレ整合

提出期限: **2026-08-20**（ICSO full paper）
