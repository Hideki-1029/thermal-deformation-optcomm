# Optical Communication PAT Simulation

このフォルダでは、Femap由来の熱LOSバイアスを光通信PATの粗捕捉シミュレータへ接続する。
軽量LOSモデルは `models/` 配下にモデルごとのパッケージとして置く。

## ソース構成

```text
src/pat_acquisition/
├── pat_acquisition_simulator.py   # PAT粗捕捉コア（モデル非依存）
├── runners/
│   ├── pat_common.py              # 共有 I/O・非熱誤差・図出力
│   └── run_femap_los_truth.py     # → results/.../femap_los_truth/
├── models/
│   ├── _common/                   # Ridge / metrics / static bias
│   ├── fourier_los/
│   │   ├── model.py
│   │   └── run_pat.py             # → results/.../fourier_los_model/
│   ├── temperature_los/
│   │   ├── features.py / dataset.py / model.py
│   │   └── train.py               # → results/.../temperature_los_model/
│   ├── sunface_los/
│   │   ├── features.py / dataset.py / model.py
│   │   ├── validate.py            # → results/.../sunface_los_model/{case}_within_case/
│   │   └── run_pat.py             # → results/.../sunface_los_model/pat/
│   ├── sunface_deltaT_los/
│   │   ├── features.py / dataset.py / model.py
│   │   └── validate.py            # → results/.../sunface_deltaT_los_model/{case}_within_case/
│   │                              # LOS ~ b + a*(T_sun - T_opp) only
│   └── sunface_deltaT_bcase_los/
│       ├── features.py / dataset.py / model.py / plots.py
│       ├── validate.py            # → results/.../sunface_deltaT_bcase_los_model/
│       └── run_pat.py             # → .../sunface_deltaT_bcase_los_model/pat/
│                                  # hierarchical: shared a + b_case(sun, I_heat)
├── configs/
├── docs/
├── tools/                         # スライド等の派生・互換ラッパー
└── archive/                       # 旧試作スクリプト
```

## 実行方法

リポジトリルートで実行する。設定は共通 YAML:

```text
src/pat_acquisition/configs/pat_femap_los_config.yaml
```

### 前提：軽量データセットの構築（温度・Sunface 用）

温度モデルと Sunface モデルを動かす前に、必ず共通入力データセットを作る。

```powershell
python scripts/build_lightweight_dataset.py
```

→ `results/pat_acquisition/lightweight_dataset/`

Femap 結果（`results/femap_deformation/*/los_angles.csv` と温度 CSV）・ケース行列・軌道カタログ・TD 日照シンボルをマージする。Femap ケースを追加・更新したあとも再実行する。

真値ベースラインと Fourier モデルは `los_angles.csv` を直接読むため、このステップは不要。

### 真値ベースライン（モデルなし）

```powershell
python "src/pat_acquisition/runners/run_femap_los_truth.py"
```

→ `results/pat_acquisition/femap_los_truth/`

### Fourier 軽量モデル

```powershell
python "src/pat_acquisition/models/fourier_los/run_pat.py"
```

→ `results/pat_acquisition/fourier_los_model/`

### 温度モデル

事前に `python scripts/build_lightweight_dataset.py` を実行済みであること。

```powershell
python "src/pat_acquisition/models/temperature_los/train.py"
```

→ `results/pat_acquisition/temperature_los_model/`

### Sunface モデル（既存: T_sun + (T_sun−T_ref) + (T_sun−T_opp)）

事前に `python scripts/build_lightweight_dataset.py` を実行済みであること。

LOS 予測の within-case 検証:

```powershell
python "src/pat_acquisition/models/sunface_los/validate.py" --case 4
python "src/pat_acquisition/models/sunface_los/validate.py" --cases 4,5,6
python "src/pat_acquisition/models/sunface_los/validate.py" --list-cases
```

→ `results/pat_acquisition/sunface_los_model/case*_within_case/`

係数のケース横断比較表（`case*_within_case/` を集約）:

```powershell
python "src/pat_acquisition/models/sunface_los/summarize_coefficients.py"
```

→ `results/pat_acquisition/sunface_los_model/sunface_coefficients_comparison.csv`
（閲覧用の有効数字3桁版: `sunface_coefficients_comparison_display.csv`）

`validate.py` 実行後も同じ CSV を自動更新する。

PAT 粗捕捉評価（MX/MY/PX/PY ケース。MZ はスキップ）:

```powershell
python "src/pat_acquisition/models/sunface_los/run_pat.py"
python "src/pat_acquisition/models/sunface_los/run_pat.py" --cases 4,5,6

# 一覧示す用。実行はしない
python "src/pat_acquisition/models/sunface_los/run_pat.py" --list-cases
```

→ `results/pat_acquisition/sunface_los_model/pat/`

### Sunface ΔT モデル（最小: LOS ~ b + a·(T_sun − T_opp)）

既存 `sunface_los` は残し、共線項 `T_sun` / `(T_sun−T_ref)` を外した版。切片 `b` の解釈用。

```powershell
python "src/pat_acquisition/models/sunface_deltaT_los/validate.py" --cases 4,5,6,8,9,10,11,12,13,14,15
python "src/pat_acquisition/models/sunface_deltaT_los/validate.py" --cases 16-21
python "src/pat_acquisition/models/sunface_deltaT_los/validate.py" --list-cases
python "src/pat_acquisition/models/sunface_deltaT_los/summarize_coefficients.py"
```

→ `results/pat_acquisition/sunface_deltaT_los_model/case*_within_case/`  
→ `results/pat_acquisition/sunface_deltaT_los_model/deltaT_coefficients_comparison.csv`

### Sunface ΔT + case bias（階層: `sunface_deltaT_bcase_los`）

軌道内は共有 `a(sun)` + ケース定数 `b_case`。ケース間で

`b_case ≈ b0(sun) + c_prop·I_prop + c_pcdu·I_pcdu`

within-case にコンポ温度を足さない。コンポ効果はケース定数 `b` 側に置く。

**「発熱フラグは MY/PY のみ有効」（既定 `--heat-faces MY,PY`）の意味:**  
TD で MY/PY だけ発熱させる、という意味ではない。Level 2 の設計行列で `I_prop` / `I_pcdu`（PROP/PCDU 発熱 ON/OFF）を使う条件が、**太陽面が MY または PY のケースだけ**、という意味。

- 太陽面 = MY / PY（かつ PROP/PCDU ON）→ `I_*` を使い、`c_prop` / `c_pcdu` で `b` の差を説明
- 太陽面 = MX / PX → たとえ PROP/PCDU が ON でも設計行列上は `I_*=0`（差は `b0(MX/PX)` 側に吸収）

PROP/PCDU 効果が主に ±Y 太陽面で効き、MX/PX では発熱モード差が小さいため。全太陽面でフラグを使うなら `--heat-faces all`。

```powershell
python "src/pat_acquisition/models/sunface_deltaT_bcase_los/validate.py" --cases 4-6,8-21
python "src/pat_acquisition/models/sunface_deltaT_bcase_los/validate.py" --list-cases
# 発熱フラグを全太陽面に広げる例:
python "src/pat_acquisition/models/sunface_deltaT_bcase_los/validate.py" --cases 4-6,8-21 --heat-faces all
# プロット省略 / 時系列ケース指定:
python "src/pat_acquisition/models/sunface_deltaT_bcase_los/validate.py" --cases 4-6,8-21 --no-plots
python "src/pat_acquisition/models/sunface_deltaT_bcase_los/validate.py" --cases 4-6,8-21 --plot-cases 4,8,15
```

→ `results/pat_acquisition/sunface_deltaT_bcase_los_model/bcase_case_table.csv`
→ `.../bcase_level2_coefficients.csv` / `bcase_a_shared.csv` / `bcase_los_metrics.csv`
→ `.../bcase_a_emp_by_sunface.png` / `bcase_b_emp_vs_b_pred.png` / `bcase_raw_vs_model_rmse.png`
→ `.../timeseries/case*_bcase_true_vs_pred.png`

PAT（no / static / bcase / truth）:

```powershell
python "src/pat_acquisition/models/sunface_deltaT_bcase_los/run_pat.py" --cases 4-6,8-21
python "src/pat_acquisition/models/sunface_deltaT_bcase_los/run_pat.py" --cases 4-6,8-21 --b-mode insample
```

→ `results/pat_acquisition/sunface_deltaT_bcase_los_model/pat/summary.csv`
→ `.../pat/pat_model_comparison.png`
→ `.../pat/{case_id}/pat_acquisition_comparison.png`

### Sunface + コンポ取付温度モデル（compo: ΔT + PROP/PCDU attach）

`sunface_deltaT_los` に PROP/PCDU 取付点温度（`T − T_ref`）を追加した版。  
事前に `compo_attach_points` の温度抽出と `build_lightweight_dataset.py` が必要。

```powershell
python "src/pat_acquisition/models/sunface_compo_los/validate.py" --cases 4,13,14,15
python "src/pat_acquisition/models/sunface_compo_los/summarize_coefficients.py"
```

→ `results/pat_acquisition/sunface_compo_los_model/case*_within_case/`  
→ `results/pat_acquisition/sunface_compo_los_model/compo_coefficients_comparison.csv`

### 互換エントリ（truth + Fourier を連続実行）

```powershell
python "src/pat_acquisition/run_pat_with_femap_los.py"
```

## 入力

```text
results/femap_deformation/*/los_angles.csv
```

各 `los_angles.csv` の `far_field_los_angle_x_urad` と
`far_field_los_angle_y_urad` を、熱LOSバイアス真値として扱う。

`far_field_los_angle_*` は、STT姿勢基準に対するLCT外向き光軸の相対回転であり、STT/LCT代表点間の並進変位から作るcenterline tiltは足さない。これは `relative_rotation_angle_*` と同じ回転由来の定義で、遠方通信PATのscan center補正に使う主LOS誤差である。

`stt_relative_los_angle_*` は、centerline tiltと相対回転を足した角度バジェット確認用の量なので、通常のPAT粗捕捉評価では既定入力にしない。

## 補正ケース

`femap_los_truth/`（真値・理想上限のみ）:

- `no_correction`
- `thermal_truth_correction`
- `thermal_plus_nonthermal_no_correction`
- `thermal_truth_correction_with_nonthermal`

`fourier_los_model/`（軽量Fourier予測モデル）:

- `static_bias_correction`
- `fourier_ff_correction`
- `fourier_plus_drift_correction`
- `fourier_ff_correction_with_nonthermal`

`sunface_los_model/pat/`（軽量 sunface 予測モデル）:

- `thermal_plus_nonthermal_no_correction`（熱+非熱・補正なし）
- `sunface_correction`（sunface のみ・非熱なし）
- `sunface_correction_with_nonthermal`（sunface + 非熱）

非熱誤差は、現時点では簡易モデルとして以下を足し合わせる。

- 軌道予測誤差
- 姿勢決定/制御のランダム誤差
- アライメント残差
- 低周波ドリフト

いずれもPAT入力面での角度誤差 `[urad]` として扱う。

## 出力

```text
results/pat_acquisition/
├── femap_los_truth/
├── fourier_los_model/
├── temperature_los_model/
├── sunface_los_model/
├── sunface_deltaT_los_model/      # b + a*(T_sun-T_opp) only
├── sunface_deltaT_bcase_los_model/ # hierarchical b_case + shared a
└── lightweight_dataset/   # 温度・sunface の共通入力
```

各 PAT 出力フォルダの主なファイル:

- `summary.csv`
- `{case_id}/pat_acquisition_results.csv`
- `{case_id}/pat_acquisition_comparison.png`

詳細は `results/pat_acquisition/README.md` を参照。

## よく変えるパラメータ

通常は `configs/pat_femap_los_config.yaml` の次の項目を変える。

- `scan.*`
- `nonthermal_error.*`
- `lightweight_model.*`（Fourier 用）
- `orbit_error.*`

コマンドライン引数で一時的に上書きすることもできる。例:

```powershell
python "src/pat_acquisition/models/fourier_los/run_pat.py" `
  --lightweight-fourier-order 6 `
  --max-range-urad 1600
```

## 粗捕捉スキャンの想定

粗捕捉は、scan centerから外側へ広がる矩形スパイラルスキャンとしてモデル化している。各scan点で `dwell_time_s` だけ滞在し、真の目標位置がそのscan点から `detect_radius_urad` 以内に入れば捕捉成功とする。

アクチュエータの詳細な運動方程式はまだ持たない。現段階では有効なPAT指向機構を抽象化している。

## ファイルの役割

- `pat_acquisition_simulator.py`: PAT粗捕捉ロジック（scan・捕捉判定・サマリ）
- `runners/pat_common.py`: Femap CSV読込、非熱誤差、結果CSV/図の共有部品
- `runners/run_femap_los_truth.py`: 真値ベースラインの PAT 評価
- `models/fourier_los/`: Fourier / static-bias モデルと PAT 評価
- `models/temperature_los/`: 温度特徴量モデルの学習・評価
- `models/sunface_los/`: 日照面温度モデルの within-case 検証と PAT 評価
- `models/_common/`: Ridge / metrics / static bias の薄い共有
- `docs/lightweight_los_model.md`: Fourier モデル仕様
- `tools/`: スライド図など派生ツール、旧パス互換ラッパー
- `archive/`: 旧試作スクリプト

Sentinel-1 POD を真値とした TLE 誤差を使う場合:

```powershell
python src/orbit/run_orbit_prediction_error.py
python src/pat_acquisition/runners/run_femap_los_truth.py
python src/pat_acquisition/models/fourier_los/run_pat.py
```

