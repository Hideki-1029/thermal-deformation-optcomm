# 熱 LOS 軽量モデル（PAT 粗捕捉用）

このドキュメントは、`run_pat_with_femap_los.py` が PAT 粗捕捉の scan center 補正に使う **軽量熱 LOS 予測モデル** の現行仕様をまとめる。

実装: `src/pat_acquisition/thermal_los_lightweight_models.py`  
設定: `src/pat_acquisition/pat_femap_los_config.yaml`  
軌道周期の解決: `src/case_metadata.py`

評価結果の出力先: `results/pat_acquisition/femap_los_truth/`

---

## 目的と位置づけ

Femap / TD から得た STT 基準の遠方 LOS 熱バイアス

\[
\boldsymbol{\theta}_{\text{true}}(t) =
\begin{bmatrix}
\theta_x(t) \\
\theta_y(t)
\end{bmatrix}
\quad [\mu\text{rad}]
\]

（`far_field_los_angle_x_urad`, `far_field_los_angle_y_urad`）を、軌道上の各粗捕捉タイミング \(t\) で近似し、scan center 補正に使う。

現段階のモデルは **物理転移可能な汎用予測器ではない**。各解析ケース（軌道・熱条件・発熱・光学特性の組み合わせ）ごとに、そのケースの教師時系列から係数をフィットする **オフライン圧縮モデル** である。

---

## PAT への接続

粗捕捉時の scan center 誤差は次で定義する（`pat_acquisition_simulator.py`）。

\[
\boldsymbol{e}(t) = \boldsymbol{e}_{\text{nonthermal}}(t)
  + \boldsymbol{\theta}_{\text{true}}(t) - \hat{\boldsymbol{\theta}}(t)
\]

| 補正ケース名 | \(\hat{\boldsymbol{\theta}}(t)\) |
|-------------|----------------------------------|
| `no_correction` | \(\mathbf{0}\) |
| `static_bias_correction` | 学習区間の平均 \(\bar{\boldsymbol{\theta}}\)（時変なし） |
| `fourier_ff_correction` | Fourier feedforward（本ドキュメントの主対象） |
| `fourier_plus_drift_correction` | Fourier + 線形ドリフト 1 項 |
| `thermal_truth_correction` | \(\boldsymbol{\theta}_{\text{true}}(t)\)（理想上限） |

非熱誤差 \(\boldsymbol{e}_{\text{nonthermal}}\) は軌道予測・姿勢・アライメント・ドリフト等の簡易合成（別途 `pat_femap_los_config.yaml` の `nonthermal_error`）。

---

## モデル一覧

`fit_lightweight_predictions()` は 1 ケースにつき次の 3 出力を返す。

### 1. Static bias

\[
\hat{\boldsymbol{\theta}}_{\text{static}}(t) = \bar{\boldsymbol{\theta}}_{\text{train}}
= \frac{1}{N_{\text{train}}} \sum_{k \in \text{train}} \boldsymbol{\theta}_{\text{true}}(t_k)
\]

時変成分を無視した定数オフセット補正。

### 2. Fourier feedforward（`fourier_ff`）

軌道周期 \(T\) [s] を既知とし、位相

\[
\phi(t) = \frac{2\pi\, t}{T}
\]

に同期した Fourier 級数で x/y を独立に近似する。

次数 \(N\)（現在 \(N=4\)）のとき、特徴ベクトルは \(1 + 2N = 9\) 次元:

\[
\boldsymbol{\Phi}(t) =
\begin{bmatrix}
1 \\
\sin\phi,\ \cos\phi \\
\sin 2\phi,\ \cos 2\phi \\
\vdots \\
\sin N\phi,\ \cos N\phi
\end{bmatrix}
\]

\[
\hat{\theta}_x(t) = \boldsymbol{\Phi}(t)^\top \mathbf{c}_x, \qquad
\hat{\theta}_y(t) = \boldsymbol{\Phi}(t)^\top \mathbf{c}_y
\]

x と y は **同じ時間基底** \(\boldsymbol{\Phi}(t)\) を共有し、係数 \(\mathbf{c}_x, \mathbf{c}_y\) のみ別。

### 3. Fourier + drift（`fourier_plus_drift`）

上記 Fourier に、正規化時間

\[
\tau(t) = \frac{t - t_0}{t_{\text{end}} - t_0}
\]

を 1 項追加したモデル。長時間ドリフトの簡易表現用。

---

## 係数の推定（Ridge 回帰）

学習データ行列 \(\mathbf{Y} = [\boldsymbol{\theta}_x \;\; \boldsymbol{\theta}_y]\)、設計行列 \(\boldsymbol{\Phi}\) に対し

\[
\mathbf{C} = (\boldsymbol{\Phi}^\top \boldsymbol{\Phi} + \lambda \mathbf{I})^{-1} \boldsymbol{\Phi}^\top \mathbf{Y}
\]

\(\lambda\) = `ridge_lam`（現在 `0.001`）。過学習抑制のための Ridge 正則化。

学習区間は `train_fraction` で決まる:

- `train_fraction = 1.0`（現在）: ケース内の **全時刻** を学習に使用
- `train_fraction < 1.0`: 先頭 \( \texttt{train\_fraction} \times T \) 秒までを学習、以降を予測評価

**注意:** 現在の既定は全データフィットのため、「未知区間への汎化」より「既知熱履歴の圧縮・補正上限」に近い評価になっている。

---

## 軌道周期 \(T\) の決め方

熱 LOS の波形から周期を推定する `auto_orbit_period` は **既定で無効**（`false`）。

代わりに Excel メタデータからケースごとに解決する（`case_metadata` セクション）。

優先順位:

1. `cases/case_matrix.xlsx` の当該 `case_id` 行の `orbit_period_s`（列があれば）
2. `case_matrix.orbit_case` → `cases/orbit_catalog.xlsx` の `orbit_period_s`
3. `orbit_catalog` の `min_alt_km` / `max_alt_km` から Keplerian 周期を計算
4. YAML の `lightweight_model.orbit_period_s`（fallback、現在 `6050.0` s）

軌道周期は TLE / GNSS / STK 等で既知とみなし、**熱 LOS 振幅の局所最小から推定しない**。

---

## 現行パラメータ（2026-07 時点）

`src/pat_acquisition/pat_femap_los_config.yaml` より:

| パラメータ | 値 | 説明 |
|-----------|-----|------|
| `fourier_order` | `4` | 1〜4 次 sin/cos（9 基底関数） |
| `train_fraction` | `1.0` | 全時刻でフィット |
| `ridge_lam` | `0.001` | Ridge 正則化係数 |
| `include_drift` | `false` | `fourier_ff` にはドリフト項なし |
| `auto_orbit_period` | `false` | Excel から周期解決 |
| `orbit_period_s` | `6050.0` | Excel 未設定時の fallback [s] |

代表ケース（03–06, LTAN06 800 km）では Excel 経由で \(T \approx 6052\) s（約 101 min）が使われる。

---

## 1 ケースあたりの処理フロー

```text
los_angles.csv (Femap 熱 LOS 真値)
  + case_matrix.xlsx / orbit_catalog.xlsx (軌道周期 T)
        |
        v
  fit_lightweight_predictions()
    - static_bias
    - fourier_ff          <-- PAT 主評価の軽量補正
    - fourier_plus_drift
        |
        v
  evaluate_coarse_acquisition()  (各補正ケース)
        |
        v
  results/pat_acquisition/femap_los_truth/{case_id}/
```

各 `los_angles.csv`（= 各 `case_id`）ごとに **係数は独立に再フィット** される。Case 04 で学習した係数を Case 05 にそのまま持ち込む運用は想定していない。

---

## 表現できるもの・できないもの

### うまく近似できる例

- 軌道周期に同期した滑らかな熱 LOS 変動（例: Case 05/06 の x 成分 sawtooth）
- 定常オフセット主体のケース（static bias でもある程度有効）

### 近似が難しい例

- 非正弦・非対称な大振幅スイング（例: Case 04 の y 成分 V 字）
- 軌道周期と無関係な長時間トレンド（`fourier_plus_drift` で一部緩和可能）

Fourier 次数を 2 → 4 に上げると Case 04 の FF 残差は改善するが、次数をさらに上げても飽和に近い。根本的には **別の特徴量（代表温度・日照フラグ等）を入れたモデル** が必要になりうる。

---

## 他軌道・他熱条件への汎化

**学習なしで他ケースに係数を転用すると、予測は大きく外れる。**

理由:

- 軌道周期 \(T\) が変わると位相 \(\phi(t)\) がずれる
- 熱応答の振幅・波形が軌道・β角・日照/蝕・発熱・光学特性で変わる
- 係数はそのケース固有の Femap 教師からしか学習していない

将来の実機運用に向けては、例えば次が必要になる。

- ケース（または軌道条件）ごとの **再フィット**
- 軌道位相 + 熱状態特徴量 → LOS の **転移可能な回帰モデル**
- PAT 捕捉残差による **オンライン更新**

現行 Fourier FF は、その前段階として「周期既知・教師あり条件下で、熱 LOS 補正が PAT にどれだけ効くか」を見るベンチマークに位置づける。

---

## 関連ファイル

| ファイル | 内容 |
|---------|------|
| `src/pat_acquisition/thermal_los_lightweight_models.py` | 特徴量生成・Ridge フィット・予測 |
| `src/pat_acquisition/run_pat_with_femap_los.py` | Femap CSV 読込・モデル比較・結果出力 |
| `src/pat_acquisition/pat_acquisition_simulator.py` | 粗捕捉シミュレーション本体 |
| `src/case_metadata.py` | Excel からの `orbit_period_s` 解決 |
| `src/pat_acquisition/pat_femap_los_config.yaml` | 実行パラメータ |
| `cases/case_matrix.xlsx` | ケース定義・`orbit_case` 参照 |
| `cases/orbit_catalog.xlsx` | 軌道条件・`orbit_period_s` / 高度 |

---

## パラメータ変更例

```powershell
# Fourier 次数を変更（YAML を編集するか CLI で上書き）
python src/pat_acquisition/run_pat_with_femap_los.py --lightweight-fourier-order 6

# 先頭 1 軌道分だけ学習し、残りを予測評価
python src/pat_acquisition/run_pat_with_femap_los.py --lightweight-train-fraction 1.0

# デバッグ用: 熱 LOS から周期推定（本番評価では非推奨）
python src/pat_acquisition/run_pat_with_femap_los.py --auto-orbit-period
```

変更後は `results/pat_acquisition/femap_los_truth/summary.csv` と各ケースの `pat_acquisition_comparison.png` で効果を確認する。
