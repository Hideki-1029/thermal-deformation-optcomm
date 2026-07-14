# PAT acquisition results

このフォルダは、熱LOS補正モデルとPAT粗捕捉評価の出力置き場。

## 構成

```text
pat_acquisition/
├── femap_los_truth/              # Femap LOS 真値ベースラインの PAT 評価
├── fourier_los_model/            # Fourier / static-bias 軽量モデルの PAT 評価
├── lightweight_dataset/          # 温度・sunface モデルが参照する共通データセット
├── temperature_los_model/        # 温度特徴量モデルの学習・予測結果
├── temperature_los_model_no_dtmid/
├── sunface_los_model/            # 日照面温度モデル（学習検証 + PAT）
│   ├── case*_within_case/        # LOS 予測検証
│   └── pat/                      # PAT 粗捕捉評価
```

## 役割の分け方

- `femap_los_truth`: 補正なし / 真値補正など、理想上限とベースラインのみ。予測モデルの線は入れない。
- `fourier_los_model`: 各ケースの `los_angles.csv` からフィットした Fourier 系モデルの PAT 評価。
- `lightweight_dataset`: `scripts/build_lightweight_dataset.py` が作る共通入力。温度・日照・LOS真値などをケース横断でまとめたもの。
- `temperature_los_model`: 上記データセットを読んで学習・検証した結果。現状は LOS 予測評価が主で、PAT 粗捕捉評価は未接続。
- `sunface_los_model`: 同上データセットを読む。`case*_within_case/` が LOS 予測検証、`pat/` が PAT 粗捕捉評価。係数比較は `sunface_coefficients_comparison.csv`（フル精度）と `sunface_coefficients_comparison_display.csv`（有効数字3桁、閲覧用）。`summarize_coefficients.py` で再生成。

## データ依存

```text
results/femap_deformation/*/los_angles.csv
        │
        ├──► femap_los_truth
        │      (runners/run_femap_los_truth.py)
        │
        ├──► fourier_los_model
        │      (models/fourier_los/run_pat.py)
        │
        └──► lightweight_dataset
               (scripts/build_lightweight_dataset.py)
                     │
                     ├──► temperature_los_model
                     │      (models/temperature_los/train.py)
                     └──► sunface_los_model
                            ├── validate.py → case*_within_case/
                            └── run_pat.py  → pat/
```

実行手順やパラメータの詳細は `src/pat_acquisition/README.md` を参照。
