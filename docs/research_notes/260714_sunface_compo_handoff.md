# sunface / ΔT / コンポ温度モデル — 進捗ハンドオフ（2026-07-14）

- 作成: 2026-07-14（初版: 研究室 PC 実装依頼）
- 更新: 2026-07-14 午後 — **実装・検証済みの知見を追記**。ノート PC でも既存結果を回せるようにする
- いま研究室 PC: Femap `cases 16–21` 解析中（完了待ち）
- ノート PC 向け: mapper / 新規 Femap は不要。**既存 deltaT・係数表の再読・考察・次モデル設計**まで可

---

## 0. いまの結論（先に読む）

1. **`sunface_deltaT_los` が本命の核**  
   `LOS ≈ b + a · (T_sun − T_opp)`。`a ≈ ±28–30 µrad/°C` がケース横断で安定。
2. **残り課題はほぼケース間 DC の `b`**（軌道内時変ではない）。within-case に温度時系列を足しても、低 SNR / 共線で係数が暴れる。
3. **次は階層分離**が筋:  
   - 軌道内: 共有 `a` + ケース定数 `b_case`  
   - ケース間: `b_case` を別回帰（発熱 ON/OFF、局所温度の**軌道平均**など）
4. 追加ケース **16–21** を `case_matrix` に登録済み。TD 作成済み想定、**Femap 解析中** → 完了後に温度抽出〜deltaT 再評価。

既存 `sunface_los` / `sunface_deltaT_los` / `sunface_compo_los` / `sunface_compo_local_los` は**消さない**（比較アーカイブ）。

---

## 1. 実装済みもの

### プローブ・データ

| 項目 | 状態 |
|------|------|
| `cases/temperature_probe_sets.yaml` → `compo_attach_points` | 済（明示 XYZ） |
| `expand_probe_set`（extract + femap plot） | 済（`probes:` / `xyz_mm` 対応、PyYAML） |
| mapper から温度抽出（04–06,08–15） | 済 |
| `build_lightweight_dataset.py` の extra CSV マージ | 済（既定で `compo_attach_points_temperatures.csv`） |
| 列名 | `temp_prop_attach_c`, `temp_pcdu_attach_c` |

プローブ目標 [mm]:

| 名前 | パネル | xyz |
|------|--------|-----|
| `prop_attach` | PY | (576.11, 600, 157.4) |
| `pcdu_attach` | MY | (322.5, 0, 649) |

最近傍例（case04）: PROP≈(575,600,155), PCDU≈(325,0,645)。

### モデルパッケージ

| パッケージ | 特徴量 | results |
|------------|--------|---------|
| `sunface_deltaT_los` | `b + a·ΔT` | `results/.../sunface_deltaT_los_model/` |
| `sunface_compo_los` | + `(T_attach − T_ref)` | `results/.../sunface_compo_los_model/` |
| `sunface_compo_local_los` | + `(T_attach − T_panel_center)` | `results/.../sunface_compo_local_los_model/` |

```powershell
python "src/pat_acquisition/models/sunface_deltaT_los/validate.py" --cases 4,5,6,8,9,10,11,12,13,14,15
python "src/pat_acquisition/models/sunface_compo_local_los/validate.py" --cases 4,5,6,8,9,10,11,12,13,14,15
```

係数表（display）:

- `.../deltaT_coefficients_comparison_display.csv`
- `.../compo_coefficients_comparison_display.csv`
- `.../compo_local_coefficients_comparison_display.csv`

---

## 2. 検証で分かったこと

### 2.1 deltaT（優秀）

- MY: `a ≈ 28.6` ほぼ定数。PX/PY は符号反転で `|a|≈28`、MX≈30.6。
- `b` は解釈可能な数十 µrad オーダー（旧 3 特徴より大幅に小さくなった）。
- 被覆（11/12）は **b ほぼ不変**、RMSE 側。HOT(10) でも `a` は同じ。

**MY 発熱スクリーニング（04/13/14/15）の b:**

| case | power | b [µrad] |
|------|-------|----------|
| 04 | ALL | −34 |
| 13 | +PROP | −23 |
| 14 | +PCDU | −8 |
| 15 | STTLCT only | **+3** |

直感「15 が 13 と 14 の間」は**不成立**。理由:

- 面を温める主効果はすでに **`a·ΔT` に吸収**（PROP→PY で dT↓、PCDU→MY で dT↑）。
- `b` は ΔT 残差 DC。PROP/PCDU とも **同符号（より負）** に寄与し、ほぼ足し算:  
  `Δb_PROP≈−26`, `Δb_PCDU≈−11`, 両方≈−37 → case04 と一致。

### 2.2 compo（`T_attach − T_ref`）— 失敗寄り

- MY で `corr(ΔT, T_pcdu)≈0.995`（PCDU が太陽面上）→ 共線再導入。
- `a` が 28→~170 に飛び、`b` 振れも悪化。RMSE は下がっても係数解釈不可。

### 2.3 compo_local（`T_attach − T_center`）— 部分成功／本質は別

- MY 発熱系列の **b 振れ 37→11 µrad**、`a≈26` で deltaT に近い。
- しかし **`d_p`/`d_c` がケース間バラバラ**。
- 原因: within-case で局所差の std が **~0.1 °C**（ΔT は ~4 °C）。ほぼ定数 × 巨大係数で切片を食うだけ。
- 効いていたのは主に **ケース平均 DC** であり、時変特徴としては SNR 不足。

→ **within-case にコンポ温度を足す方針は打ち切り寄り。階層へ。**

---

## 3. 次のモデル方針（未実装・設計メモ）

```text
# Level 1（軌道内・既存 deltaT）
LOS(t) ≈ b_case + a_shared(sun_face) · ΔT(t)

# Level 2（ケース間 DC）
b_case ≈ f( sun_face, I_prop, I_pcdu,
            mean(T_prop−T_PY), mean(T_pcdu−T_MY), ... )
```

候補入力（優先度イメージ）:

1. 太陽方位（カテゴリ）+ PROP/PCDU の 0/1 または W  
2. 局所温度の**軌道平均**（時系列ではない）  
3. 軌道環境（COLD/HOT 等）— 現状 coarser  
4. 被覆 — b には弱そう  

実装するなら新フォルダ推奨（例: `sunface_deltaT_bcase_los`）。探索中はモデルごとにフォルダ分離がよい。

---

## 4. 追加ケース 16–21（Femap 進行中）

`cases/case_matrix.xlsx` に登録済み。`case_group=sensitivity`, `use_for_model=exclude`。

| # | sun | power | 対になる既存 | 狙い |
|---|-----|-------|--------------|------|
| 16 | PY | STTLCT | 08 ALL | PY の b=−59 が STTLCT でどこまで寄るか |
| 17 | MX | STTLCT | 09 ALL | MX でも ALL↔STTLCT |
| 18 | PY | +PROP | 16/19 | **PROP＝太陽面**の発熱スクリーニング |
| 19 | PY | +PCDU | 16/18 | PCDU＝裏面 |
| 20 | PX | +PROP | 06/21 | PX を MY(13) 型に揃える |
| 21 | PX | +PCDU | 06/20 | PX を MY(14) 型に揃える |

対で見る表:

- PY: **08 / 16 / 18 / 19** ⇔ MY の 04 / 15 / 13 / 14  
- PX: **05 / 06 / 20 / 21**  
- MX: **09 / 17**

### Femap 完了後（研究室 PC）にやること

```powershell
# 1) 温度抽出（9点 + compo_attach）
#    run_femap_case が 9点まで出すなら、compo は別途:
foreach ($n in 16..21) { ... extract_mapper_temperature_probe.py --probe-set compo_attach_points ... }

# 2) dataset rebuild
python scripts/build_lightweight_dataset.py

# 3) deltaT（本命）を新ケース込みで
python "src/pat_acquisition/models/sunface_deltaT_los/validate.py" --cases 4,5,6,8,9,10,11,12,13,14,15,16,17,18,19,20,21
```

特に見る: **PY の b(08 vs 16 vs 18 vs 19)** が MY と同符号パターンか。

---

## 5. ノート PC で今できること

mapper / Femap なしで可能な作業:

1. **deltaT 係数表の読み直し・考察**  
   `results/pat_acquisition/sunface_deltaT_los_model/deltaT_coefficients_comparison_display.csv`
2. **compo / local 失敗理由の再確認**（上 §2）
3. **階層 b モデルの設計・スケルトン実装**（データは既存 11 ケースで試作可）  
   - 目的変数: 各ケースの `intercept_urad`（deltaT）  
   - 説明変数: sun_face, prop/pcdu flags, `mean(local_*)`（lightweight から集計）
4. このメモの「次アクション」整理

ノートで validate を回す場合、既存 `lightweight_dataset` に prop/pcdu 列がある前提（研究室で rebuild 済みを pull していること）。

---

## 6. 取付点座標（再掲）

座標系: Femap / mapper 絶対 [mm]。LCT COM 基準 ≈ `(300,300,50)`。

| コンポ | パネル | プローブ目標 [mm] |
|--------|--------|-------------------|
| PROP | PY (`y=600`) | (576.11, 600, 157.4) |
| PCDU | MY (`y=0`) | (322.5, 0, 649) |

既存 9 点では代用不可（140–150 mm 離れる）。

---

## 7. 関連パス

| 内容 | パス |
|------|------|
| deltaT | `src/pat_acquisition/models/sunface_deltaT_los/` |
| compo (`T−T_ref`) | `src/pat_acquisition/models/sunface_compo_los/` |
| compo local | `src/pat_acquisition/models/sunface_compo_local_los/` |
| probe 定義 | `cases/temperature_probe_sets.yaml` |
| case 表（16–21 含む） | `cases/case_matrix.xlsx` |
| 温度抽出 | `scripts/extract_mapper_temperature_probe.py` |
| dataset | `scripts/build_lightweight_dataset.py` |
| PAT README | `src/pat_acquisition/README.md` |

---

## 8. 旧・初版依頼文（アーカイブ）

初版は研究室 PC で compo 実装するためのコピペ依頼だった。**実装は完了**している。再実行が必要なのは主に **16–21 の後処理**と、任意で **階層 b モデル**。
