# Femap thermal deformation

Femap の熱変形解析結果から STT/LCT 相対変形・LOS 角度を出すためのスクリプト群。

リポジトリルートから実行する。

## メインの実行ファイル

| ファイル | 役割 |
|---|---|
| `run_femap_case.py` | **Femap 自動化の入口**。クリーン → mapper import → 解析 → STT/LCT(+パネル中心) Excel 出力 |
| `reexport_from_op2.py` | **既存 `.op2` から再出力**。結果削除 → OP2 import → Excel 更新（再解析なし） |
| `plot_stt_lct_relative_deformation.py` | **図の入口**。Excel から相対変形・LOS 予算図を作成 |
| `plot_lct_face_proxy_los.py` | **LCT 配置代理**。STT 固定 + 各パネル中心を LCT とみなした far-field LOS サマリ |

それ以外はライブラリ:

- `femap_com.py` — Femap COM 接続・解析セット操作
- `export_stt_lct_excel.py` — STT/LCT + パネル中心ノード結果の Excel 出力

## 前提

1. Femap で `C:/Users/Hide/Femap/research_model/research_model.modfem` を開く
2. ケースフォルダに `mapper_from_TD/output.dat` があること  
   （TD 側: `python -m src.thermal_desktop.run_td_cases --cases ...`）

## 1. Femap ケース実行

TD と同じ **ケース番号** 指定（`NN_*` フォルダを自動解決）:

```powershell
# 一覧
python -m src.femap_deformation.run_femap_case --list-cases

# 複数ケース
python -m src.femap_deformation.run_femap_case --cases 8,9

# 範囲
python -m src.femap_deformation.run_femap_case --cases 10-15
```

フルフォルダ名でも可:

```powershell
python -m src.femap_deformation.run_femap_case `
  --case-id 07_LTAN06_800km_1213COLD_MZ_ALL_HEAT_MZ_0p5_delta_t_60s
```

出力:

- Excel: `inputs/data_femap_deformation/{case_id}.xlsx`（ケースフォルダにもコピー）
- Nastran 出力: `C:/Users/Hide/Femap/research_model/{case_id}/`

よく使うオプション:

```powershell
# 解析済み結果から Excel だけ再出力
python -m src.femap_deformation.run_femap_case --cases 8,9 --export-only

# 解析までやって Excel は出さない
python -m src.femap_deformation.run_femap_case --cases 8 --skip-export

# 少数 load だけでスモークテスト
python -m src.femap_deformation.run_femap_case --cases 9 --max-loads 3
```

Excel には STT/LCT に加え、パネル中心 6 点（MX/PX/MY/PY/MZ/PZ）の並進・回転も出る。  
ノード定義は `inputs/data_femap_deformation/stt_lct_node_config.json`。

## 2. 既存 `.op2` から Excel を更新（再解析なし）

ケースフォルダの `.op2` を Femap に読み直し、STT/LCT + パネル中心の Excel を更新する:

```powershell
# 計画だけ確認
python -m src.femap_deformation.reexport_from_op2 --cases 3-15 --dry-run

# 実行（Femap で research_model.modfem を開いておく）
python -m src.femap_deformation.reexport_from_op2 --cases 3-15

# 単一 / 複数
python -m src.femap_deformation.reexport_from_op2 --cases 4
python -m src.femap_deformation.reexport_from_op2 --cases 4,5,8
```

ケースごとに: 既存 output set 削除 → `.op2` import → Excel 出力  
（`inputs/data_femap_deformation/{case_id}.xlsx` とケースフォルダへコピー）。

`run_femap_case` の Analyze 実行中は使わないこと。

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
## 4. 相対変形・LOS 図

TD / Femap と同じ **ケース番号** 指定:

```powershell
# 一覧
python -m src.femap_deformation.plot_stt_lct_relative_deformation --list-cases

# 複数ケース
python -m src.femap_deformation.plot_stt_lct_relative_deformation --cases 8,9

# 範囲
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

## 典型フロー

```text
TD:    --cases 8,9  → mapper_from_TD/output.dat
Femap: --cases 8,9  → Excel
plot:  --cases 8,9  → 図
```
