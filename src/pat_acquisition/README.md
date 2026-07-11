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
│   └── sunface_los/
│       ├── features.py / dataset.py / model.py
│       ├── validate.py            # → results/.../sunface_los_model/{case}_within_case/
│       └── run_pat.py             # → results/.../sunface_los_model/pat/
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

```powershell
python "src/pat_acquisition/models/temperature_los/train.py"
```

→ `results/pat_acquisition/temperature_los_model/`

### Sunface モデル

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

`validate.py` 実行後も同じ CSV を自動更新する。

PAT 粗捕捉評価（MX/MY/PX/PY ケース。MZ はスキップ）:

```powershell
python "src/pat_acquisition/models/sunface_los/run_pat.py"
python "src/pat_acquisition/models/sunface_los/run_pat.py" --cases 4,5,6
python "src/pat_acquisition/models/sunface_los/run_pat.py" --list-cases
```

→ `results/pat_acquisition/sunface_los_model/pat/`

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
