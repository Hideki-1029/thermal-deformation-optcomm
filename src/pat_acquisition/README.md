# Optical Communication PAT Simulation

このフォルダでは、Femap由来の熱LOSバイアスを光通信PATの粗捕捉シミュレータへ接続する。

## Femap LOS Truthを使った粗捕捉評価

リポジトリルートで次を実行する。

```powershell
python "src/pat_acquisition/run_pat_with_femap_los.py"
```

このスクリプトは、以下の入力を自動で読む。

```text
results/femap_deformation/*/los_angles.csv
```

各 `los_angles.csv` の `far_field_los_angle_x_urad` と
`far_field_los_angle_y_urad` を、熱LOSバイアス真値として扱う。

`far_field_los_angle_*` は、STT姿勢基準に対するLCT外向き光軸の相対回転であり、STT/LCT代表点間の並進変位から作るcenterline tiltは足さない。これは `relative_rotation_angle_*` と同じ回転由来の定義で、遠方通信PATのscan center補正に使う主LOS誤差である。

`stt_relative_los_angle_*` は、centerline tiltと相対回転を足した角度バジェット確認用の量なので、通常のPAT粗捕捉評価では既定入力にしない。

比較するケースは以下。

- `no_correction`: 熱LOSを補正せず、そのままscan center誤差に入れる。
- `thermal_truth_correction`: Femap由来の熱LOS真値をscan center補正に入れる。

出力先は以下。

```text
results/pat_acquisition/femap_los_truth/
```

主な出力は以下。

- `summary.csv`: 各ケース・補正モデルの捕捉成功率、平均捕捉時間、95%捕捉時間など。
- `{case_id}/pat_acquisition_results.csv`: 各時刻の捕捉結果。
- `{case_id}/pat_acquisition_comparison.png`: 熱LOS、捕捉時間、scan-center誤差の確認図。

## よく変えるパラメータ

例:

```powershell
python "src/pat_acquisition/run_pat_with_femap_los.py" `
  --max-range-urad 1600 `
  --step-urad 40 `
  --detect-radius-urad 25 `
  --dwell-time-s 0.1
```

`--los-prefix` を変えると、別のLOS定義も評価できる。既定値は `far_field_los`。

```powershell
python "src/pat_acquisition/run_pat_with_femap_los.py" --los-prefix stt_relative_los
```

## 粗捕捉スキャンの想定

粗捕捉は、scan centerから外側へ広がる矩形スパイラルスキャンとしてモデル化している。各scan点で `dwell_time_s` だけ滞在し、真の目標位置がそのscan点から `detect_radius_urad` 以内に入れば捕捉成功とする。

このモデルは、アクチュエータの詳細な運動方程式をまだ持たない。現段階では、scan center周りにビーム/受信視野を順に向けられる有効なPAT指向機構を抽象化している。実機対応としては、LCT内部のFSM/ジンバル、または衛星姿勢制御によるbody pointing scanのどちらにも読み替えられるが、駆動帯域、整定時間、飽和、加速度制限は未モデル化である。これらは後で `dwell_time_s`、scan点列、または別のscan modelとして追加する。

## ファイルの役割

- `pat_acquisition_simulator.py`: PAT粗捕捉シミュレータの部品ライブラリ。矩形スパイラルscan点の生成、捕捉判定、各時刻での評価、結果サマリを担当する。入力データの出所や出力ファイル名はここでは扱わない。
- `run_pat_with_femap_los.py`: Femap後処理済み `los_angles.csv` をPAT入力に接続する実行スクリプト。`far_field_los_angle_x/y_urad` を熱LOS真値として読み、`pat_acquisition_simulator.py` の評価関数へ渡し、CSVと図を `results/pat_acquisition/femap_los_truth/` に保存する。
- `test_thermo_PAT_system_1.py`: 以前の試作スクリプト。合成熱LOSや軽量モデル検討用のメモ的実装。

責務分担は次の通り。

```text
run_pat_with_femap_los.py
  = Femap CSVの読み込み、補正ケースの定義、結果保存、図化

pat_acquisition_simulator.py
  = scan center誤差から捕捉成否・捕捉時間を計算するPAT粗捕捉ロジック
```

今後、軌道予測誤差や姿勢誤差などの非熱誤差を足す場合は、まず `run_pat_with_femap_los.py` 側で `nonthermal_error_urad` を作り、`pat_acquisition_simulator.py` の `evaluate_coarse_acquisition()` に渡す。
