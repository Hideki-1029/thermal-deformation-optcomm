# Femap thermal deformation

Femap の熱変形解析結果から STT/LCT 相対変形・LOS 角度を出すためのスクリプト群。

リポジトリルートから実行する。

## 典型フロー（通常はこれだけ）

```text
TD:    run_td_cases --cases ...     → mapper_from_TD/output.dat
Femap: run_femap_case --cases ...   → 解析 + Excel（STT/LCT + パネル中心）
plot:  plot_stt_lct_relative_deformation --cases ... → 図 / los_angles.csv
```

通常のケース追加では **`run_femap_case` が Excel まで出す**。  
既存 `.op2` からの再出力（`reexport_from_op2`）は毎回やるものではない（後述）。

## メインの実行ファイル

| ファイル | 役割 |
|---|---|
| `run_femap_case.py` | **通常の入口**。クリーン → mapper import → 解析 → Excel 出力 |
| `plot_stt_lct_relative_deformation.py` | Excel から相対変形・LOS 予算図 / `los_angles.csv` |
| `plot_lct_face_proxy_los.py` | LCT 配置代理（パネル中心を LCT とみなした far-field LOS） |
| `reexport_from_op2.py` | **たまに使う**。既存 `.op2` から再解析なしで Excel だけ作り直し |

ライブラリ:

- `femap_com.py` — Femap COM 接続・解析セット操作
- `export_stt_lct_excel.py` — STT/LCT + パネル中心ノード結果の Excel 出力

## 前提

1. Femap で `C:/Users/Hide/Femap/research_model/research_model.modfem` を開く
2. ケースフォルダに `mapper_from_TD/output.dat` があること  
   （TD 側: `python -m src.thermal_desktop.run_td_cases --cases ...`）

## 1. Femap ケース実行（通常パス）

TD と同じ **ケース番号** 指定（`NN_*` フォルダを自動解決）:

```powershell
# 一覧
python -m src.femap_deformation.run_femap_case --list-cases

# 複数ケース
python -m src.femap_deformation.run_femap_case --cases 8,9

# 範囲
python -m src.femap_deformation.run_femap_case --cases 16-21
```

フルフォルダ名でも可:

```powershell
python -m src.femap_deformation.run_femap_case `
  --case-id 07_LTAN06_800km_1213COLD_MZ_ALL_HEAT_MZ_0p5_delta_t_60s
```

出力:

- Excel: `inputs/data_femap_deformation/{case_id}.xlsx`（ケースフォルダにもコピー）
- Nastran 出力: `C:/Users/Hide/Femap/research_model/{case_id}/`（`.op2` など）

Excel には **STT / LCT** に加え、**パネル中心 6 点**（MX/PX/MY/PY/MZ/PZ）の並進・回転も出る。  
ノード定義: `inputs/data_femap_deformation/stt_lct_node_config.json`（`points` + `panel_center_points`）。

よく使うオプション:

```powershell
# 解析までやって Excel は出さない（後で export したいとき）
python -m src.femap_deformation.run_femap_case --cases 8 --skip-export

# 少数 load だけでスモークテスト
python -m src.femap_deformation.run_femap_case --cases 9 --max-loads 3
```

## 2. 相対変形・LOS 図

```powershell
python -m src.femap_deformation.plot_stt_lct_relative_deformation --list-cases
python -m src.femap_deformation.plot_stt_lct_relative_deformation --cases 8,9
python -m src.femap_deformation.plot_stt_lct_relative_deformation --cases 10-15
```

フル case id または単一 Excel でも可:

```powershell
python -m src.femap_deformation.plot_stt_lct_relative_deformation `
  --case-id 08_LTAN06_800km_1213COLD_PY_ALL_HEAT_PY_0p5

python -m src.femap_deformation.plot_stt_lct_relative_deformation `
  --input inputs/data_femap_deformation/08_LTAN06_800km_1213COLD_PY_ALL_HEAT_PY_0p5.xlsx
```

入力 Excel の stem（`case_id`）から自動で:

- `cases/case_matrix.xlsx` の時間軸
- `C:/Users/Hide/Femap/research_model/{case_id}/mapper_from_TD` の温度プローブ

を使う。

出力先: `results/femap_deformation/{case_id}/`  
（遠視野 LOS 予算図は `results/femap_deformation/{case_id}_far_field_los_angle_budget.png`）

## 3. LCT 配置代理の far-field LOS

STT は固定し、指定したパネル中心（または現状 LCT）を LCT 代理として、面外向き法線を名目光軸にした相対回転 LOS（metric B）を出す。  
デフォルトは **summary.csv のみ**（ファイルが増えにくい）。

```powershell
# サマリだけ
python -m src.femap_deformation.plot_lct_face_proxy_los `
  --cases 4,5 --lct-faces MX,MY,PY

# 気になった組み合わせだけ時系列・図も
python -m src.femap_deformation.plot_lct_face_proxy_los `
  --cases 4 --lct-faces MX --write-timeseries --plot --heatmap
```

出力:

```text
results/femap_deformation/lct_face_proxy/
  summary.csv                       # 全ケース横断（再実行分はマージ更新）
  summary_heatmap_rms_mag.png       # --heatmap
  {case_id}/
    summary.csv
    timeseries/LCT_{face}.csv       # --write-timeseries
    plots/LCT_{face}.png            # --plot
```

## 4. 既存 `.op2` から Excel を更新（たまに使う）

**通常フローでは不要。** 解析は済んでいて Excel だけ作り直したいとき用。

使う例:

- `stt_lct_node_config.json` を変えたあと、再解析せずに Excel を更新したい
- 古いケースの Excel にパネル中心列が無く、`.op2` から揃えて出したい
- Excel を消してしまった / 壊した

```powershell
# 計画だけ確認
python -m src.femap_deformation.reexport_from_op2 --cases 3-15 --dry-run

# 実行（Femap で research_model.modfem を開いておく）
python -m src.femap_deformation.reexport_from_op2 --cases 3-15

python -m src.femap_deformation.reexport_from_op2 --cases 4
python -m src.femap_deformation.reexport_from_op2 --cases 4,5,8
```

ケースごとに: 既存 output set 削除 → `.op2` import → Excel 出力  
（`inputs/data_femap_deformation/{case_id}.xlsx` とケースフォルダへコピー）。

注意:

- `run_femap_case` の Analyze 実行中は使わない
- 新規ケースは `run_femap_case` で解析＋Excel まで一気にやる方が普通

関連で、Femap 上に結果が残っているときだけ Excel を出すなら:

```powershell
python -m src.femap_deformation.run_femap_case --cases 8,9 --export-only
```

これも常時ではなく、`--skip-export` で解析だけ先に走らせたあとなどに使う。
