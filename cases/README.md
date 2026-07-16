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
- `thermal_optical_properties.yaml`: `case_matrix.xlsx` の `Opt_MX`、`Opt_MY`、`Opt_MZ`、`Opt_PX`、`Opt_PY`、`Opt_PZ` で参照する熱光学特性名と、太陽吸収率・赤外放射率の対応表。
- `temperature_probe_sets.yaml`: TD mapper出力から代表温度点を抽出するためのプローブセット定義。デフォルトでは各面の中央、4頂点、4辺中点を使う。
- `orbit_catalog.xlsx`: TD Orbit の正本一覧。シート `orbit_catalog` は **いま `case_matrix` が参照している軌道だけ**。未使用の旧行は `orbit_catalog_archive` に退避する。
- `../inputs/data_symbols_TD/`: TDからExcel出力したシンボル時系列。日照/蝕の履歴は各ケースの `LOGIC_SUN` 列を正本とする。
- `../inputs/spacecraft_models/`: 衛星寸法、パネル厚み、材料物性などの構造モデル定義。

## Basic Policy

ケース設計の正本は `case_matrix.xlsx` とし、軌道条件の正本は `orbit_catalog.xlsx`（シート `orbit_catalog`）とする。

Pythonスクリプトや自動処理も、原則としてこの2つのExcelファイルを直接読み込む。Excelで編集した内容を解析に反映するには、Excelファイルを保存してから解析スクリプトを実行する。

`case_schema.yaml` はケース本体ではなく、列の意味と制約を定義するために使う。

CSVが必要な場合は、確認用・共有用の派生物として必要なタイミングで書き出す。解析運用の必須手順にはしない。

衛星寸法やパネル素材のようにケース間で共有する構造モデル情報は、`case_matrix.xlsx` に直接展開せず、`inputs/spacecraft_models/` 以下のモデル定義に集約する。ケース表では `spacecraft_model` 列で参照する。

各パネル面の熱光学特性は、`case_matrix.xlsx` では `Opt_MX`、`Opt_MY`、`Opt_MZ`、`Opt_PX`、`Opt_PY`、`Opt_PZ` に特性名だけを書く。各特性名に対応する太陽吸収率、赤外放射率、a/e は `thermal_optical_properties.yaml` に集約する。`0p5` は感度解析用の仮想特性で、太陽吸収率と赤外放射率をどちらも0.5にしたものとする。

軽量モデル用に抽出する代表温度点は、`temperature_probe_sets.yaml` にプローブセットとして定義する。デフォルトは `default_surface_9points` とし、各パネル面について中央、4頂点、4辺中点の計9点をFemap mapper座標で指定し、実際の温度は最も近いFemapノードから取得する。

TDとFemapは、TD側で作ったケースセット名を基準にした1ファイル運用を正とする。TDの温度出力、Femapモデル・解析結果、Python解析後のCSV・図は、同じTDケースセット名または同名フォルダ配下に置く。

これにより、ファイル名やフォルダ名を個別に推測せず、`case_id` の命名規則から次を追跡できる状態にする。

- TDの出力ファイル
- Femapに読み込む解析ファイル
- Femapの変形解析結果
- Pythonで後処理したLOS角度結果

Excelが作成する `~$*.xlsx` は一時ロックファイルなので、ケース管理の対象外とする。

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

軌道の正本は Thermal Desktop の Orbit オブジェクト名とする。`case_matrix.orbit_case` と `orbit_catalog.td_orbit_name` は同じ文字列で揃える。

### 入力（白）とスクリプト記入（灰）

人が触るのは意図だけ。TD の Pointing / Additional rotations は入力にしない（灰色列は手編集しない）。

| 種別 | 列 | 意味 |
|---|---|---|
| 入力 | `td_orbit_name`, `sun_face`, `constraint_target`, `constraint_face` | Orbit 名・太陽面・第二軸の種類と体軸面 |
| 入力 | Keplerian / `notes` まで | 軌道面パラメータ・メモ（ここまでが新規行の手入力範囲） |
| 灰（結果） | `eff_sun_face`, `eff_velocity_face`, `eff_nadir_face` | TD 上の実際の太陽／速度／Nadir 面（確認用） |
| 灰（TD内部） | `orient_type`, `constraint_type`, `pointing_axis`, `constraint_axis`, `rot*` | GUI/OpenTD の生設定。確認用 |

姿勢の意図は **太陽面 + 第二軸** の2つで決める（第三軸は直交から決まる）。

- `sun_face`: 太陽指向面（`MX`/`MY`/`MZ`/`PX`/`PY`）。`case_matrix.sun_direction_body` と一致。
- `constraint_target`: 第二軸が追うもの。`velocity` または `nadir`。
- `constraint_face`: その第二軸に向ける体軸面（例: `velocity`+`MZ` → 速度に `MZ`）。
- `constraint_type`: **TD の生 enum**（`VELOCITY` / `PLANET`）。`constraint_target` と同じ事実の dump。入力しない。
- `eff_*_face` / `eff_*_source`: TD dump 後の正味面と由来。入力の確認用。

### 新規軌道の運用

1. **手入力は `notes` 列まで**（白列のみ）。灰色列は空のままでよい。
2. TD に Orbit を作る／反映する:

```powershell
python -m src.thermal_desktop.create_td_orbits --names LTAN18_693km_SENTINEL1_MY_SUN --attach-only --dry-run
python -m src.thermal_desktop.create_td_orbits --names LTAN18_693km_SENTINEL1_MY_SUN --attach-only
```

3. 開いている TD から姿勢を読み戻して Excel の灰色列を更新する:

```powershell
python -m src.thermal_desktop.refresh_orbit_catalog_attitude --attach-only --dry-run
python -m src.thermal_desktop.refresh_orbit_catalog_attitude --attach-only
```

4. `sun_face` / `constraint_target` / `constraint_face` と `eff_*` が一致しているか確認する。ずれがあれば `notes_attitude` に WARNING が出る。

列順と灰色スタイルだけ直す（TD 不要）:

```powershell
python -m src.thermal_desktop.refresh_orbit_catalog_attitude --layout-only
```

軽量モデルで日照/蝕遷移を扱うときは、`orbit_catalog.xlsx` に代表時刻を手入力せず、TDからExcel出力したシンボル時系列を使う。各ケースの履歴は `inputs/data_symbols_TD/{case_id}.xlsx` に置き、`LOGIC_SUN` 列を読む。

```text
LOGIC_SUN = 0: 蝕
LOGIC_SUN = 1: 日照
```

`orbit_period_s` は軌道周期や軌道位相を扱うためのメタデータとして残すが、蝕入り/蝕明けのタイミングは `LOGIC_SUN` の時系列を正本とする。

未使用の旧軌道行は削除せず `orbit_catalog_archive` シートへ移す。

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
  -> TD temperature output / mapper output.dat
  -> TD symbol history Excel in inputs/data_symbols_TD/
  -> Femap thermal deformation result
  -> Python STT-LCT LOS angle CSV
  -> lightweight model dataset
  -> PAT simulation
```

TD mapper用の `output.dat` は、Femap側のケースフォルダ配下にあるTD mapper出力を使う。代表温度点のCSVや温度確認図は、Python後処理で `results/` 配下に生成される派生成果物として扱う。

TDのシンボル出力は `inputs/data_symbols_TD/` に保存する。ここにあるExcelの `LOGIC_SUN` 列が、軌道中の各時刻が日照か蝕かを示す履歴である。

Femap解析は、同じFemap解析ファイルを使い、解析ごとの出力先をTDケースセット名のフォルダに切り替える運用を基本とする。STT/LCTノードの変位・回転入力Excelは `inputs/data_femap_deformation/{case_id}.xlsx`、Femapケースフォルダや `mapper_from_TD` は `{mapper_root}/{case_id}/` に置く。

## Directory Convention

解析データはTDケースセット名で束ねる。既存実行分の `case set 03-06` はこの方針に合わせて格納済みとし、以後の新規ケースも同じ規則に従う。

```text
data/
  td_raw/{td_case_set_name}/
  femap_raw/{td_case_set_name}/
  processed/{td_case_set_name}/

inputs/
  data_symbols_TD/{td_case_set_name}.xlsx

results/
  femap_deformation/{td_case_set_name}_far_field_los_angle_budget.png
  femap_deformation/{td_case_set_name}/
    los_angles.csv
    stt_lct_plane_sketch.png
```

ケース表にパス列は持たない。下流成果物は `case_id` から次の規則で解決する。TD symbol Excelは `inputs/data_symbols_TD/{case_id}.xlsx`。

## Main Output Target

軽量モデルの教師データとして主に使う量は、STT観測基準で見たLCT光軸ずれとする。

- `stt_relative_los_angle_x_urad`
- `stt_relative_los_angle_y_urad`
- `stt_relative_los_angle_magnitude_urad`

`global_los_angle_*` は診断用として残し、STT自身の回転がどの程度効いているかを確認する。