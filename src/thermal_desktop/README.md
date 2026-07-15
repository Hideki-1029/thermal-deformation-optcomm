# Thermal Desktop (OpenTD) automation

TD の Case Set を実行し、DataMapper 出力を Femap の
`{case_id}/mapper_from_TD/` にコピーする。

## GUI 設定（一度だけ）

1. `research_thermal_model.dwg` を TD で開く
2. DataMapper を **Enabled**
3. Output File を staging に固定して DWG 保存:

```text
..\..\Femap\research_model\_td_mapper_staging\output.dat
```

ケース直下の `mapper_from_TD` を Output File にしない（別ケース Map 時に上書きされる）。  
`DataMapper.Update()` はこのモデルでは落ちるので、Enabled / 出力先は GUI のみで変える。

## スクリプトの流れ（ケースごと）

1. staging の `output*` を削除  
2. 指定ケースの `.sav` を Set Current（**DWG 相対パスのみ**登録。絶対パスは使わない）  
3. `tdmapallmappers`（TD → staging）  
4. staging の `output.dat` ヘッダがケース名を含むか検証  
5. `{femap}/{case_id}/mapper_from_TD/` へコピー（フォルダは自動作成）  
6. staging を空にする  

## 使い方

リポジトリルートから（TD を開いた状態で）:

```powershell
# 一覧
python -m src.thermal_desktop.run_td_cases --group transient --list-cases --attach-only

# Case Set 新規作成（case_matrix → symbols 既定オン、case 04 をテンプレに clone）
python -m src.thermal_desktop.create_td_cases --cases 22 --template 4 --attach-only --dry-run
python -m src.thermal_desktop.create_td_cases --cases 22 --template 4 --attach-only

# Orbit 新規作成（orbit_catalog 白列 → TD）
python -m src.thermal_desktop.create_td_orbits --names LTAN18_693km_SENTINEL1_MY_SUN --attach-only --dry-run
python -m src.thermal_desktop.create_td_orbits --names LTAN18_693km_SENTINEL1_MY_SUN --attach-only
python -m src.thermal_desktop.refresh_orbit_catalog_attitude --attach-only

# 解析 + mapper
python -m src.thermal_desktop.run_td_cases --group transient --cases 7,8,9 --attach-only

# mapper のみ（.sav 済み）
python -m src.thermal_desktop.run_td_cases --group transient --cases 9 --map-only --attach-only

# パス確認のみ
python -m src.thermal_desktop.run_td_cases --group transient --cases 8,9 --dry-run --attach-only
```

出力:

```text
C:/Users/Hide/Femap/research_model/{case_id}/mapper_from_TD/output.dat
```

## トラブルシュート

| 症状 | 対処 |
|---|---|
| OutputFile is not staging | GUI で `_td_mapper_staging\output.dat` に設定して保存 |
| Enabled≠1 | GUI で Enabled |
| header does not mention case | Set Current 失敗。Postprocessing Datasets を確認 |
| 同じ `.sav` が相対/絶対で二重表示 | 古い絶対パス行を GUI で Delete して DWG 保存。以後の自動化は相対パスのみ |
| `eNotOpenForWrite` | `DataMapper.Update` を使わない。TD を開き直して `--attach-only` |
| `RCDataSetManager: already open for write` | 連続 map 中のロック残り。既定でケース間 10s pause（`--case-pause 0` で無効）。再発時は TD 再起動して該当ケースから `--map-only` |
| Connect 失敗 | 対象 DWG を開いてから `--attach-only` |

## オプション

| オプション | 意味 |
|---|---|
| `--group` | グループ名（既定 `transient`） |
| `--cases` | `7,8,9` / `10-15` |
| `--map-only` | 解析スキップ |
| `--skip-map` | 解析のみ |
| `--staging-dir` | staging（既定 `...\research_model\_td_mapper_staging`） |
| `--attach-only` | 起動中 TD に attach（推奨） |
| `--dry-run` | 実行せずパス表示 |
| `--fail-fast` | 最初の失敗で停止 |
| `--case-pause` | ケース間待機秒（既定 `10`、`0` で無効） |

## ファイル

| ファイル | 役割 |
|---|---|
| `run_td_cases.py` | CLI（解析 + mapper） |
| `create_td_orbits.py` | catalog の白列（sun / constraint / Keplerian）から TD Orbit を作成 |
| `create_td_cases.py` | case_matrix 行から Case Set をテンプレ clone で作成 |
| `refresh_orbit_catalog_attitude.py` | TD から姿勢を読み、灰色列（`eff_*` / Rot* 等）を更新。新規行は `notes` まで手入力→本コマンドで確認列を埋める |
| `orbit_catalog_io.py` | catalog 列順・入力(白)/確認(灰)スタイル |
| `opentd_runtime.py` | OpenTD 接続 |
| `case_selection.py` | ケース番号パース |
| `test_case_selection.py` | 単体テスト |
| `test_create_td_cases.py` | matrix→symbol マッピング単体テスト |

### `create_td_cases` の方針

- テンプレ Case Set を clone し、`orbit_case` / symbols を差し替える
- **解析時間 / Output**: `orbit_catalog.orbit_period_s` から算出
  - End time (`timend`) = **3 × period**
  - Thermal Output Increment (`OUTPUT`) = **period / 100**
  - period が無いときだけ `case_matrix.duration_s` / `sample_interval_s` にフォールバック
- 既存 Case の timing だけ直す: `--patch-timing`（例: `--cases 22-25 --patch-timing`）
- **出力先は常に `UserDirectory=<group>`**（例: `transient/`）。未設定だと DWG 直下に落ちる
- **既定で case_matrix から symbols を適用**（`--no-symbols-from-matrix` でオフ）
- `*_heat_w = 0` は `INT_HEAT_*` を書かず、テンプレ定格 W を残す（OFF は `IS_COMPO_*=0`）
- 光学 override は太陽面 `Opt_{sun_face}` のみ（他面の `Opt_MY=Black` 等はモデル既定）

## 次のステップ

```powershell
python -m src.femap_deformation.run_femap_case --case-id 09_LTAN06_800km_1213COLD_MX_ALL_HEAT_MX_0p5
```
