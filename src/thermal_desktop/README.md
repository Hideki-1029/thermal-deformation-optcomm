# Thermal Desktop (OpenTD) automation

TD の Case Set をグループ＋番号指定で実行し、PostProcessing DataMapper の出力を
Femap 側の `mapper_from_TD` に書き出す。

## 前提

1. **先に TD で** `research_thermal_model.dwg` を開いておく（推奨）  
   既定: `C:/Users/Hide/v2_Thermal_Desktop_Models/research_thermal_model/research_thermal_model.dwg`
2. Model Browser に DataMapper があること（既定では **Disabled**）
3. Python に `pythonnet` が入っていること（`pip install pythonnet`）
4. `OpenTD.dll` / `OpenTDv241.dll` が解決できること  
   この PC では GAC の `OpenTDv241` を自動検出する。別バージョンなら `OPENTD_DLL` か `--opentd-dll` で指定。

Mapper は解析のたびに自動実行されないよう、普段は Disabled のままにする。

**重要:** OpenTD の `DataMapper.Map()` は内部で `Update()` し、このモデルでは落ちる。
Mapper を GUI で **Enabled** にし、Output File を対象ケースの
`mapper_from_TD/output.dat` にしてあるときは `--map-backend tdmapallmappers` が本命。
（スクリプトは `mapper_from_TD` フォルダを自動作成する。手動時と同じ前提。）

既定の **`mapnastran`** は別経路で、TEMP* 付き `output.dat` が欠けることがある。

## 使い方

リポジトリルートから:

```powershell
# グループ内のケース一覧（TD を開いた状態で）
python -m src.thermal_desktop.run_td_cases --group transient --list-cases

# 7,8,9 を解析 → mapper → Femap mapper_from_TD
python -m src.thermal_desktop.run_td_cases --group transient --cases 7,8,9

# 範囲指定
python -m src.thermal_desktop.run_td_cases --group transient --cases 10-15

# 混在
python -m src.thermal_desktop.run_td_cases --group transient --cases 7,10-12,15

# 既に .sav があるとき mapper だけ
python -m src.thermal_desktop.run_td_cases --group transient --cases 8 --map-only

# パス確認のみ
python -m src.thermal_desktop.run_td_cases --group transient --cases 8 --dry-run
```

出力先（ケースごと）:

```text
C:/Users/Hide/Femap/research_model/{case_id}/mapper_from_TD/output.dat
(+ outputTransient.txt, outputMapSummary*.txt など)
```

## トラブルシュート

| 症状 | 対処 |
|---|---|
| `eNotOpenForWrite` / パイプ切断 | 多くは `DataMapper.Update` が原因。現行版は Update しない。TD を開き直して `--attach-only`。Output File は GUI で staging に固定 |
| Ctrl+C が効かない | OpenTD 待ちはネイティブブロック。ダイアログ OK のあと、残った `python.exe` はタスクマネージャで終了 |
| Connect 失敗 | TD で対象 DWG を開いてから `--attach-only` |
| Map 後に dest が空 | TD の DataMapper Output File 先に `output*` が出ているか確認し、スクリプトがそこからコピーできているかログを見る |

## 主なオプション

| オプション | 意味 |
|---|---|
| `--group` | Case Set Manager のグループ名（既定 `transient`） |
| `--cases` | `7,8,9` / `10-15` / `7,10-12,15` |
| `--map-only` | 解析スキップ、既存 `.sav` から mapper のみ |
| `--skip-map` | 解析のみ（mapper しない） |
| `--clear-mapper-dir` | mapper 前に `mapper_from_TD` を空にする |
| `--mapper-handle` | DataMapper が複数あるときの handle（例: `7C8A`） |
| `--dwg` | TD の dwg パス |
| `--femap-root` | Femap `research_model` ルート |
| `--map-backend` | `mapnastran`（既定）/ `tdmapallmappers` / `opentd-map`（落ちやすい） |
| `--nastran-bdf` | `mapnastran` 用 BDF |
| `--opentd-dll` / `OPENTD_DLL` | `OpenTD.dll` の明示パス |
| `--attach-only` | 起動中の TD に attach（推奨） |
| `--start-new` | 新規 TD 起動（DWG が既に開いているときは使わない） |

## ファイル

| ファイル | 役割 |
|---|---|
| `run_td_cases.py` | CLI 入口 |
| `opentd_runtime.py` | OpenTD.dll 解決と TD 接続 |
| `case_selection.py` | ケース番号パースとグループ絞り込み |

## 次のステップ

このあと Femap 側は既存の:

```powershell
python -m src.femap_deformation.run_femap_case --case-id 08_...
```

で `mapper_from_TD/output.dat` を読んで熱変形解析できる。
