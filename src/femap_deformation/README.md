# Femap thermal deformation

Femap の熱変形解析結果から STT/LCT 相対変形・LOS 角度を出すためのスクリプト群。

リポジトリルートから実行する。

## メインの実行ファイル

| ファイル | 役割 |
|---|---|
| `run_femap_case.py` | **Femap 自動化の入口**。クリーン → mapper import → 解析 → STT/LCT Excel 出力 |
| `plot_stt_lct_relative_deformation.py` | **図の入口**。Excel から相対変形・LOS 予算図を作成 |

それ以外はライブラリ:

- `femap_com.py` — Femap COM 接続・解析セット操作
- `export_stt_lct_excel.py` — STT/LCT ノード結果の Excel 出力（`run_femap_case` から呼ばれる）

## 前提

1. Femap で `C:/Users/Hide/Femap/research_model/research_model.modfem` を開く
2. ケースフォルダに `mapper_from_TD/output.dat` があること  
   例: `C:/Users/Hide/Femap/research_model/{case_id}/mapper_from_TD/output.dat`

## 1. Femap ケース実行

```powershell
python -m src.femap_deformation.run_femap_case `
  --case-id 07_LTAN06_800km_1213COLD_MZ_ALL_HEAT_MZ_0p5_delta_t_60s
```

出力:

- Excel: `inputs/data_femap_deformation/{case_id}.xlsx`（ケースフォルダにもコピー）
- Nastran 出力 (`.dat` / `.op2` / `.f06` など): `C:/Users/Hide/Femap/research_model/{case_id}/`

よく使うオプション:

```powershell
# 解析済み結果から Excel だけ再出力
python -m src.femap_deformation.run_femap_case --case-id 07_... --export-only

# 解析までやって Excel は出さない
python -m src.femap_deformation.run_femap_case --case-id 07_... --skip-export

# 少数 load だけでスモークテスト
python -m src.femap_deformation.run_femap_case --case-id 07_... --max-loads 3
```

## 2. 相対変形・LOS 図

```powershell
python -m src.femap_deformation.plot_stt_lct_relative_deformation `
  --input inputs/data_femap_deformation/07_LTAN06_800km_1213COLD_MZ_ALL_HEAT_MZ_0p5_delta_t_60s.xlsx
```

入力 Excel の stem（`case_id`）から自動で:

- `cases/case_matrix.xlsx` の時間軸
- `C:/Users/Hide/Femap/research_model/{case_id}/mapper_from_TD` の温度プローブ

を使う。

出力先: `results/femap_deformation/{case_id}/`  
（遠視野 LOS 予算図は `results/femap_deformation/{case_id}_far_field_los_angle_budget.png`）

## 典型フロー

```text
TD mapper (output.dat)
    → run_femap_case.py          # Femap 解析 + Excel
    → plot_stt_lct_relative_deformation.py   # 図・CSV
```
