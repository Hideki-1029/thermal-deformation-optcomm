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


### cursorの特徴
テキストの読み込みはPDFでもmdでもできる。（がmdの方がディレクトリ構造は明確に把握できる）
画像は.png等に直すのが確実。（PDF内の図は読めていない可能性がある）