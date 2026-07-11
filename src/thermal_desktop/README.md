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
| `run_td_cases.py` | CLI |
| `opentd_runtime.py` | OpenTD 接続 |
| `case_selection.py` | ケース番号パース |
| `test_case_selection.py` | 単体テスト |

## 次のステップ

```powershell
python -m src.femap_deformation.run_femap_case --case-id 09_LTAN06_800km_1213COLD_MX_ALL_HEAT_MX_0p5
```
