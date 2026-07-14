# sunface_compo_los モデル — 意図と研究室 PC での作り方

- 作成: 2026-07-14
- 目的: この PC には Femap / mapper 出力が無いので、**研究室 PC（mapper あり）で Cursor に渡して実装・抽出するための手順書**
- 前提: `sunface_deltaT_los` は既にリポジトリにある（共線項なしの最小モデル）

---

## 1. 意図（なぜ作るか）

### 現状（deltaT）で分かったこと

モデル:

```text
LOS ≈ b + a · (T_sun − T_opp)
```

- 共線項 `T_sun` / `(T_sun − T_ref)` を外した結果、**切片 b が解釈可能な大きさ**になった
- MY 系で **a ≈ 28–30 µrad/°C** とケース横断でほぼ一定
- b のケース間振れも以前より大幅に縮小（ただし発熱配置でまだ数十 µrad オーダーは残る）

→ 「ケース間で同じ a を使う」方向が見えてきた。

### まだ足りないところ / JANUS との差分

JANUS 型は実質 `LOS = K · ΔT`（1 組の温度差）。
deltaT だけだと核がそれに近い。

内部発熱（PROP / PCDU）は **W や ON/OFF を直接入れず**、取付面近傍の**計測可能な温度**として入れる。

理由:

```text
発熱 P → 熱容量・コンダクタンス → パネル温度 → 熱ひずみ → LOS
```

の上流（P）を入れると不確定が増える。取付近傍 T なら一段短い。

### 目指すモデル形

```text
LOS ≈ b'
    + a  · (T_sun − T_opp)
    + d_p · (T_PROP_attach − T_ref)
    + d_c · (T_PCDU_attach − T_ref)
```

- `T_ref = 23.9 °C`（Femap 基準温度）
- 期待: **a は deltaT と同程度で安定**、発熱由来の切片変動が `d_p` / `d_c` に移り、**b' がさらに定数に近づく**
- 出力先（案）:
  - src: `src/pat_acquisition/models/sunface_compo_los/`
  - results: `results/pat_acquisition/sunface_compo_los_model/`
- 既存の `sunface_los` / `sunface_deltaT_los` は**消さない**（比較用アーカイブ）

参考実装: `src/pat_acquisition/models/sunface_deltaT_los/` をほぼコピーして特徴量だけ足すのが最短。

---

## 2. 取付点座標（温度プローブ目標）

座標系: Femap / mapper 絶対座標 [mm]  
基準 LCT COM（リポジトリ）: `(300, 300, 50)`  
（TD 由来相対座標なので数 mm ずれ可。最近傍ノード取りで十分）

| コンポ | 取付パネル | COM [mm] | **プローブ目標（パネル上）[mm]** |
|--------|------------|----------|----------------------------------|
| PROP | **PY** (`y=600`) | (576.11, 549.9, 157.4) | **(576.11, 600, 157.4)** |
| PCDU | **MY** (`y=0`) | (322.5, 60, 649) | **(322.5, 0, 649)** |

導出メモ:

- LCT→PROP 相対: `(276.11, 249.9, 107.4)` → COM = LCT + 相対
- LCT→PCDU 相対: `(22.5, −240, 599)`
- 取付点 = 重心から Y 方向にパネルまで（≒高さ/2）
- case matrix: `prop_location=PY_MZside`, `pcdu_location=MY_PZside` と一致

**既存 9 点プローブの最近傍は 140–150 mm 離れており代用不可。** mapper からこの座標の最近傍を取る必要がある。

---

## 3. 研究室 PC でやること（手順）

### Step A — probe set を追加

ファイル: `cases/temperature_probe_sets.yaml`

新しいセット例: `compo_attach_points`

現状の YAML は「全 face に同じ fractions」前提なので、次のどちらか:

1. **推奨:** `expand_probe_set` を拡張し、明示 XYZ を受け付ける  
   ```yaml
   compo_attach_points:
     description: PROP/PCDU attachment centers on panels
     selection: nearest_xyz_within_panel
     probes:
       - name: prop_attach
         panel: PANEL_PY
         xyz_mm: [576.11, 600.0, 157.4]
       - name: pcdu_attach
         panel: PANEL_MY
         xyz_mm: [322.5, 0.0, 649.0]
   ```
2. または MY/PY だけ face を定義し、fractions で近似  
   - PY prop: x frac ≈ 0.968, z frac ≈ 0.154  
   - MY pcdu: x frac ≈ 0.538, z frac ≈ 0.651  
   （全 face に両点が付くと余分な probe も出るので、読む列だけ選べば可）

変更が必要な展開ロジック（両方ある）:

- `scripts/extract_mapper_temperature_probe.py` の `expand_probe_set`
- `src/femap_deformation/plot_stt_lct_relative_deformation.py` の `expand_temperature_probe_set`

### Step B — 各ケースで温度抽出

mapper はリポジトリ外。既定パス例:

```text
C:/Users/Hide/Femap/research_model/<case_stem>/mapper_from_TD/
```

必要ファイル:

- `outputMapSummaryGridPoints.txt`
- `outputTransient.txt`

例（1 ケース）:

```powershell
python scripts/extract_mapper_temperature_probe.py `
  --mapper-dir "C:/Users/Hide/Femap/research_model/04_LTAN06_800km_1213COLD_MY_ALL_HEAT_MY_0p5/mapper_from_TD" `
  --probe-set compo_attach_points `
  --output-dir "results/femap_deformation/04_LTAN06_800km_1213COLD_MY_ALL_HEAT_MY_0p5"
```

対象ケース（まずは MY 発熱比較が本命）:

```text
04, 13, 14, 15
```

余裕があれば deltaT と同じく:

```text
04,05,06,08,09,10,11,12,13,14,15
```

期待出力（ケースフォルダ内）:

- `compo_attach_points_temperatures.csv`
- `compo_attach_points_nodes.csv`（選ばれた node id / 実座標の確認用）

### Step C — lightweight dataset に列を載せる

`scripts/build_lightweight_dataset.py` は今、既定で

```text
default_surface_9points_temperatures.csv
```

だけを読む。次のどちらか:

1. `compo_attach` CSV を **追加マージ**（推奨。9 点は残す）
2. 一時的に probe 名を 9 点 CSV に追記してから rebuild

最終的に `lightweight_dataset_all.csv` に例えば次が欲しい:

- `temp_prop_attach_c` または `temp_panel_py_prop_attach_c`
- `temp_pcdu_attach_c` または `temp_panel_my_pcdu_attach_c`

（pivot 後の列名は `temp_{probe_name}_c` 規則に従う）

```powershell
python scripts/build_lightweight_dataset.py
```

### Step D — モデル実装

`sunface_deltaT_los` をコピーして `sunface_compo_los` を作る。

特徴量:

| feature | 意味 |
|---------|------|
| `t_sunface_minus_opposite_c` | `T_sun − T_opp`（必須） |
| `t_prop_attach_minus_ref_c` | `T_PROP_attach − 23.9` |
| `t_pcdu_attach_minus_ref_c` | `T_PCDU_attach − 23.9` |

**入れないもの:** 絶対 `T_sun` と共線の `(T_sun − T_ref)`（deltaT で外した理由と同じ）

CLI 例:

```powershell
python "src/pat_acquisition/models/sunface_compo_los/validate.py" --cases 4,13,14,15
python "src/pat_acquisition/models/sunface_compo_los/summarize_coefficients.py"
```

### Step E — 見たい結果

特に MY・COLD・0p5 の発熱違い:

| case | power_mode |
|------|------------|
| 04 | ALL_HEAT |
| 13 | STTLCT_PROP_HEAT |
| 14 | STTLCT_PCDU_HEAT |
| 15 | STTLCT_HEAT |

成功の目安:

1. **a（ΔT 係数）が deltaT と同程度でケース間安定**（~28–30）
2. **b' のケース間差が deltaT の b よりさらに小さい**
3. PROP ON 系で `d_p`、PCDU ON 系で `d_c` が意味のある符号・大きさ
4. within-case 支配軸 RMSE が deltaT（~6–7 µrad）と同程度か改善

注意: `T_PROP_attach` は PY 上なので、太陽が MY のとき `T_sun−T_opp` の `T_opp`（PY center）と相関しうる。係数の安定性は必ず見る。

---

## 4. Cursor への短い依頼文（コピペ用）

```text
docs/research_notes/260714_sunface_compo_handoff.md に従って
sunface_compo_los を実装・実行して。

要点:
1. cases/temperature_probe_sets.yaml に PROP/PCDU 取付プローブを追加
   PROP (576.11, 600, 157.4) on PY / PCDU (322.5, 0, 649) on MY [mm]
2. この PC の mapper_from_TD から各ケースで温度抽出
3. lightweight_dataset に列をマージして rebuild
4. sunface_deltaT_los を雛形に sunface_compo_los を作り、
   LOS ~ b + a*(T_sun-T_opp) + d_p*(T_prop-T_ref) + d_c*(T_pcdu-T_ref)
5. まず cases 4,13,14,15 で validate。既存 sunface / deltaT は消さない。
6. 係数表で a の安定性と b の縮小を報告して。
```

---

## 5. 関連パス（このリポジトリ）

| 内容 | パス |
|------|------|
| deltaT 実装 | `src/pat_acquisition/models/sunface_deltaT_los/` |
| deltaT 結果 | `results/pat_acquisition/sunface_deltaT_los_model/` |
| 既存 sunface（3 特徴・アーカイブ） | `src/pat_acquisition/models/sunface_los/` |
| probe 定義 | `cases/temperature_probe_sets.yaml` |
| 温度抽出 | `scripts/extract_mapper_temperature_probe.py` |
| dataset 構築 | `scripts/build_lightweight_dataset.py` |
| case 発熱・配置 | `cases/case_matrix.xlsx` |
| LCT 絶対座標 | `inputs/data_femap_deformation/stt_lct_node_config.json` |
| PAT README | `src/pat_acquisition/README.md` |
