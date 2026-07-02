# Analysis Case Management

このディレクトリでは、TD解析からFemap解析、PythonでのLOS角度誤差解析、軽量モデル用データセット作成までに使う解析ケースを管理する。

## Purpose

TD解析で定義した熱環境・軌道・コンポーネント条件を、Femap解析とPython解析まで一貫して伝搬させる。

解析ケースが増えても、以下を追跡できる状態にする。

- どのTD条件から作られたケースか
- どのFemap荷重セット・解析結果に対応するか
- どのPython出力CSV・図・軽量モデル用データに対応するか
- 学習用・検証用・汎化評価用のどのグループに属するか

## Files

- `case_matrix.xlsx`: 人が編集・比較するケース一覧。ケース間の差分を横並びで確認するためのマスター表。
- `case_schema.yaml`: `case_matrix` の列名、単位、必須/任意、許容値を定義する。
- `orbit_catalog.xlsx`: TDで使う軌道条件の一覧。既存衛星プロジェクトの軌道表を英語列名で管理する。
- `../inputs/spacecraft_models/`: 衛星寸法、パネル厚み、材料物性などの構造モデル定義。

## Basic Policy

ケース設計の正本は `case_matrix.xlsx` とし、軌道条件の正本は `orbit_catalog.xlsx` とする。

Pythonスクリプトや自動処理も、原則としてこの2つのExcelファイルを直接読み込む。Excelで編集した内容を解析に反映するには、Excelファイルを保存してから解析スクリプトを実行する。

`case_schema.yaml` はケース本体ではなく、列の意味と制約を定義するために使う。

CSVが必要な場合は、確認用・共有用の派生物として必要なタイミングで書き出す。解析運用の必須手順にはしない。

衛星寸法やパネル素材のようにケース間で共有する構造モデル情報は、`case_matrix.xlsx` に直接展開せず、`inputs/spacecraft_models/` 以下のモデル定義に集約する。ケース表では `spacecraft_model` 列で参照する。

## Case Group and Model Use

`case_group` は、その解析ケースを研究上どの目的で作ったかを表す。

例:

- `check`: TD -> Femap -> Python の解析ルートが正しく動くかを確認する。
- `sensitivity`: 発熱量、太陽方向、拘束条件、STT/LCT位置などの感度を見る。
- `train`: 軽量モデルの学習データを作る。
- `validation`: 軽量モデルの選定や調整に使う。
- `generalization`: 学習していない熱環境・軌道・電源モードへの汎化性能を見る。

`use_for_model` は、そのケースを軽量モデルのデータセットとしてどう使うかを表す。

例:

- `exclude`: モデル学習には使わない。動作確認や感度解析だけに使う。
- `train`: 学習に使う。
- `validation`: モデル選定や調整に使う。
- `test`: 最終評価に使う。

つまり、`case_group` は研究・解析上の目的、`use_for_model` は機械学習データとしての役割である。

例:

```text
case_group=sensitivity, use_for_model=exclude
```

これは「感度解析用のケースだが、軽量モデルの学習・評価データには入れない」という意味になる。

## Orbit Metadata

軌道条件は現状TDのOrbit設定が持っているため、ケース表ではTD内の軌道設定を識別できる情報を残す。

- `orbit_case`: 解析ケース間で軌道条件をグループ化するためのラベル。
- `td_orbit_name`: Thermal Desktop内で使ったOrbitオブジェクト名または軌道設定名。
- `orbit_source_path`: TLE、軌道暦、TD設定のエクスポートなど、TD外に軌道定義を残した場合の参照先。
- `epoch_utc`: 軌道と太陽方向を決める基準時刻。

`beta_angle_deg` は、独立に入力する熱条件というより、軌道面と太陽方向から決まる派生メタデータとして扱う。TDから直接出せない場合は空欄でもよく、後でPython側で計算または手入力する。

軽量モデルで日照/蝕遷移を扱うため、軌道イベントは秒単位で残す。

- `orbit_period_s`: 軌道周期。軌道位相や複数周回のイベント展開に使う。
- `eclipse_entry_time_s`: ケース開始から見た代表周回の蝕入り時刻。
- `eclipse_exit_time_s`: ケース開始から見た代表周回の蝕明け時刻。
- `eclipse_duration_s`: 代表周回の蝕継続時間。
- `sunlit_duration_s`: 代表周回の日照継続時間。

Femapのケース番号は `sample_interval_s` と `femap_loadset_start` から時刻に戻せるため、蝕入り/蝕明けはケース番号ではなく時刻で管理する。

軌道条件の詳細は `orbit_catalog.xlsx` に集約し、`case_matrix.xlsx` からは `td_orbit_name` などで参照する。軌道カタログ側は列名・値を英語に寄せ、スクリプトで扱いやすいようにする。

## Case ID

すべての下流成果物は `case_id` を持つ。

`case_id` はTD解析でケースを作る時点で決め、Femap解析、Python解析、軽量モデル用データセットまで変更しない。

例:

```text
TD001_uniform_temp_check
TD002_linear_gradient_beta30
TD003_lct_heat_acquisition
```

## Data Flow

```text
case_matrix.xlsx
  -> TD temperature output
  -> Femap thermal deformation result
  -> Python STT-LCT LOS angle CSV
  -> lightweight model dataset
  -> PAT simulation
```

## Directory Convention

今後、解析データが増えてきたら以下のように分ける。

```text
data/
  td_raw/{case_id}/
  femap_raw/{case_id}/
  processed/{case_id}/

results/
  {case_id}/
    los_angles.csv
    summary.json
    plots/
```

現時点で既存の解析ファイルをすぐ移動する必要はない。まずは新しいケースからこの規則に寄せる。

## Main Output Target

軽量モデルの教師データとして主に使う量は、STT観測基準で見たLCT光軸ずれとする。

- `stt_relative_los_angle_x_urad`
- `stt_relative_los_angle_y_urad`
- `stt_relative_los_angle_magnitude_urad`

`global_los_angle_*` は診断用として残し、STT自身の回転がどの程度効いているかを確認する。
