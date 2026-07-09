### リポジトリの説明：
熱ひずみによる光通信捕捉追尾系への影響評価および改善手法を検討する、ドキュメント・コードの統合リポジトリ


当面の目標は、修士輪講会・ICSOの予稿を書くこと。

ICSOに向けては研究を前に進める必要がある。

基本takmotoしか使わないのでmainブランチで作業。


### フォルダの構成
docs/      研究メモ・文献管理
inputs/    解析に使う入力データ（Femap Excel など、git 管理）
data/      大容量の外部データ（git 未収録、別 PC ではローカル取得が必要）
src/       再利用する研究コード本体
scripts/   実行用スクリプト
results/   解析結果・図・表
papers/    修士輪講会・ICSOなどの予稿
shared/    Typstテンプレート・共通図・共通bib

### src/ と scripts/ の使い分け：
src/ には、LOS角度計算、軽量モデル、PATシミュレータなど、他の解析から再利用するモデル本体や関数群を置く。
scripts/ には、ケース表の書き出し、解析の一括実行、論文用の図表生成など、コマンドとして実行する作業用スクリプトを置く。
つまり、src/ は「部品」、scripts/ は「作業手順」として分ける。

### inputs/ の位置づけ：
解析で使うINPUTデータを集約する場所。たとえば `inputs/data_femap_deformation/` には、Femapから出力した熱変形結果のExcelファイルや、STT/LCT代表節点の設定ファイルを置く。
src/ や scripts/ は、基本的にこの inputs/ 以下のデータを読み込んで results/ 以下に解析結果を出力する。


### data/の位置づけ：
data/フォルダは、git に含まれない大容量データ（別 PC で clone したとき）
`data/` 以下は容量が大きいため git に入れていない。研究室 PC など、既にファイルがある環境ではそのまま使える。別 PC で初めて clone した場合は、下表のデータをローカルに取得する。

| パス | 目安サイズ | 用途 | 取得方法 |
|------|-----------|------|----------|
| `data/orbit/tle/tle_2026.parquet` | 約 480 MB | TLE/GP 履歴（軌道予測誤差解析・PAT 連成） | HuggingFace から手動ダウンロード（下記） |
| `data/orbit/sentinel1/*.EOF` | 数 MB/ファイル | Sentinel-1 精密軌道（POD 真値） | スクリプト実行時に自動取得（キャッシュ） |

TLE/GP 履歴 parquet の最小手順（リポジトリルートで実行）：

```powershell
mkdir data\orbit\tle
curl -L -o data\orbit\tle\tle_2026.parquet "https://huggingface.co/datasets/juliensimon/space-track-tle-history/resolve/main/data/tle_2026.parquet"
```

取得元データセット: [juliensimon/space-track-tle-history](https://huggingface.co/datasets/juliensimon/space-track-tle-history)

軌道データの詳細（POEORB の S3 取得、設定ファイル、解析コマンド）は `data/orbit/README.md` を参照。

### 解析結果の再現性

メインの解析（case 03–06 の LOS → 軌道誤差 → PAT）は、下表のデータが揃えば再現できる。`results/` の一部は git 管理しているため、上流を再実行しなくても下流だけ回せる場合がある。

| 出力 | スクリプト | 再現に必要なもの |
|------|-----------|-----------------|
| `results/femap_deformation/*/los_angles.csv` | `src/thermal_deformation/plot_stt_lct_relative_deformation.py` | `inputs/data_femap_deformation/*.xlsx`（git 管理） |
| `results/orbit/sentinel1_tle_vs_pod/*` | `src/orbit/run_orbit_prediction_error.py` | `data/orbit/tle/tle_2026.parquet` ＋ `data/orbit/sentinel1/*.EOF`（実行時に自動取得） |
| `results/pat_acquisition/femap_los_truth/*` と `fourier_los_model/*` | `src/pat_acquisition/runners/run_femap_los_truth.py` と `models/fourier_los/run_pat.py` | 上の2つ、または git 上の既存 CSV |
| 温度プローブ図（`panel_*_temperature_probe.csv` 等） | 同上（オプション） | Femap 側 `mapper_from_TD`（リポジトリ外、下記） |

依存関係は次の通り。

```text
inputs/data_femap_deformation/*.xlsx  ──→  results/femap_deformation/*/los_angles.csv
                                                    │
data/orbit/tle/tle_2026.parquet        ──→  results/orbit/sentinel1_tle_vs_pod/*
data/orbit/sentinel1/*.EOF (自動DL)    ──→         │
                                                    ↓
                                          results/pat_acquisition/femap_los_truth/*
                                          results/pat_acquisition/fourier_los_model/*
```

補足：

- Sentinel-1 の `.EOF` は `data/orbit/sentinel1/` にキャッシュされるが git 未収録。`run_orbit_prediction_error.py` 実行時に AWS から自動取得される（ネット接続が必要）。
- 軌道誤差の時系列 CSV（`results/orbit/sentinel1_tle_vs_pod/orbit_prediction_error_timeseries.csv`）は git 管理している。`.EOF` がなくても、PAT 解析だけ再実行する場合はこの CSV で足りる。
- 温度プローブ関連は Femap ローカル出力に依存する。既定パスは `C:/Users/Hide/Femap/research_model/{case}/mapper_from_TD`（リポジトリ外）。別 PC では Femap 環境が必要。
- Femap 本体の熱解析そのものは再現対象外。git には Femap から書き出した Excel（`inputs/`）がある。

ゼロから回す最小コマンド（リポジトリルートで実行）：

```powershell
# 1. Femap LOS（case ごとに --input を変える）
python src/thermal_deformation/plot_stt_lct_relative_deformation.py --input inputs/data_femap_deformation/04_LTAN06_800km_1213COLD_MY_ALL_HEAT_MY_0p5.xlsx

# 2. 軌道誤差（.EOF はこのとき初めて DL される）
python src/orbit/run_orbit_prediction_error.py

# 3. PAT 粗捕捉評価
python src/pat_acquisition/runners/run_femap_los_truth.py
python src/pat_acquisition/models/fourier_los/run_pat.py
```

PAT の詳細は `src/pat_acquisition/README.md` を参照。


### cursorの特徴
テキストの読み込みはPDFでもmdでもできる。（がmdの方がディレクトリ構造は明確に把握できる）
画像は.png等に直すのが確実。（PDF内の図は読めていない可能性がある）