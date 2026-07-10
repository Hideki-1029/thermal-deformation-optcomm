# Thermal Desktop (OpenTD) automation

TD の Case Set をグループ＋番号指定で実行し、PostProcessing DataMapper の出力を
Femap 側の `mapper_from_TD` に書き出す。

## 前提（GUI で一度だけ）

1. **先に TD で** `research_thermal_model.dwg` を開く  
   既定: `C:/Users/Hide/v2_Thermal_Desktop_Models/research_thermal_model/research_thermal_model.dwg`
2. DataMapper を **Enabled** にする
3. DataMapper の **Output File を staging に固定**して DWG を保存:

```text
..\..\Femap\research_model\_td_mapper_staging\output.dat
```

絶対パスなら `C:/Users/Hide/Femap/research_model/_td_mapper_staging/output.dat`。  
**ケースの `mapper_from_TD` を直接指定しない**（別ケース Map 時に上書きされる）。

4. Python に `pythonnet`、`OpenTDv241` が解決できること

`DataMapper.Update()` / `Map()` はこの DWG では落ちるので、スクリプトは使わない。  
Enabled と Output File は GUI で固定する。

## スクリプトの流れ（ケースごと）

1. staging の `output*` を削除  
2. 指定ケースの `.sav` を Set Current  
3. `tdmapallmappers`（TD が staging に書く）  
4. staging の `output.dat` ヘッダが **そのケース名** を含むことを検証（違えばコピーしない）  
5. `...\Femap\research_model\{case_id}\mapper_from_TD\` へコピー  
6. staging を再度空にする  

これでケース混線と、誤ったケースの Femap 送りを防ぐ。

## 使い方

リポジトリルートから:

```powershell
# グループ内のケース一覧（TD を開いた状態で）
python -m src.thermal_desktop.run_td_cases --group transient --list-cases

# 7,8,9 を解析 → mapper → Femap mapper_from_TD
python -m src.thermal_desktop.run_td_cases --group transient --cases 7,8,9 --attach-only

# 既に .sav があるとき mapper だけ
python -m src.thermal_desktop.run_td_cases --group transient --cases 9 --map-only --attach-only

# パス確認のみ
python -m src.thermal_desktop.run_td_cases --group transient --cases 8 --dry-run --attach-only
```

最終出力（ケースごと）:

```text
C:/Users/Hide/Femap/research_model/{case_id}/mapper_from_TD/output.dat
(+ outputTransient.txt, outputMapSummary*.txt など)
```

## トラブルシュート

| 症状 | 対処 |
|---|---|
| OutputFile is not the shared staging folder | GUI で Output File を `_td_mapper_staging\output.dat` にして保存 |
| DataMapper Enabled≠1 | GUI で Enabled にする（`--enable-mapper` は使わない） |
| header does not mention case | Set Current 失敗か staging 残留。ログの current dataset を確認 |
| `eNotOpenForWrite` / パイプ切断 | `DataMapper.Update` を呼ばないこと。TD を開き直して `--attach-only` |
| Connect 失敗 | TD で対象 DWG を開いてから `--attach-only` |

## 主なオプション

| オプション | 意味 |
|---|---|
| `--group` | Case Set Manager のグループ名（既定 `transient`） |
| `--cases` | `7,8,9` / `10-15` / `7,10-12,15` |
| `--map-only` | 解析スキップ、既存 `.sav` から mapper のみ |
| `--skip-map` | 解析のみ（mapper しない） |
| `--staging-dir` | staging フォルダ（既定 `...\research_model\_td_mapper_staging`） |
| `--map-backend` | `tdmapallmappers`（既定）/ `mapnastran` / `opentd-map` |
| `--clear-mapper-dir` | コピー前にケース側 `mapper_from_TD` を空にする |
| `--mapper-handle` | DataMapper が複数あるときの handle（例: `7C8A`） |
| `--attach-only` | 起動中の TD に attach（推奨） |

## ファイル

| ファイル | 役割 |
|---|---|
| `run_td_cases.py` | CLI 入口 |
| `opentd_runtime.py` | OpenTD.dll 解決と TD 接続 |
| `case_selection.py` | ケース番号パースとグループ絞り込み |

## 次のステップ

```powershell
python -m src.femap_deformation.run_femap_case --case-id 09_LTAN06_800km_1213COLD_MX_ALL_HEAT_MX_0p5
```
