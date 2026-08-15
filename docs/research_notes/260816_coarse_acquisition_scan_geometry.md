# 粗捕捉スキャン幾何の更新（ビーコン／粗FOV級）

- 作成: 2026-08-16
- 目的: ICSO フルペーパーのアブストで、補正なし捕捉時間が文献の 30 s 級に対して長すぎた問題を、走査設定の見直しで直す
- 状態: 実装済み。階層 bcase PAT を再実行済み
- 関連:
  - 旧スキャン箱の議論（領域最適化は未着手）: [`260813_scan_region_optimization.md`](260813_scan_region_optimization.md)
  - PAT 章・旧秒: [`260802_update_main_typ_to_260721_slides.md`](260802_update_main_typ_to_260721_slides.md) §2.10
  - 残差 Fourier: [`260813_post_ff_residual_fourier.md`](260813_post_ff_residual_fourier.md)
  - 非熱・dwell が保守的という指摘: [`google_doc/MD/260713_非熱誤差の扱い/content.md`](google_doc/MD/260713_非熱誤差の扱い/content.md)

---

## 0. 結論

初期指向誤差（熱LOS 中央値 ~615 µrad、大きいケース 1.2 mrad 超）は妥当だった。長すぎたのは誤差ではなく、**通信ビーム級の密なスパイラル**だったこと。

粗捕捉は通信ビームではなくビーコン／粗FOVで掃く、という前提に切り替え、Shi ら 2023 の矩形走査パラメータを参考に設定を直した。熱LOSモデルは触っていない。PAT の走査評価だけを、最新の階層 `b_case` モデルで再計算した。

---

## 1. なぜ旧設定が長かったか

旧設定（試作から据え置き）:

```text
max_range_urad: 1600
step_urad: 40
detect_radius_urad: 25
dwell_time_s: 0.1
```

- 全箱 6561 点、最大 656 s。平均 ~125 s（熱のみ・補正なし）は環 ~18（半径 ~720 µrad）で当たることに対応
- `step=40`, `detect=25` は `step/√2 > detect_radius` なので、正方格子に**被覆の穴**があった
- 7/13 メモでも dwell 0.1 s と密な step が遅い、と既出

誤差のオーダー自体は Shi らの FOU 予算（30 s 要求なら不確定領域 1.53 mrad 以下）と同世界。秒だけが、狭い検出円で 1.6 mrad 箱を掃いた結果だった。

---

## 2. Shi らをどう参考にしたか

文献: Y. Shi, S. Chen, M. Yu, Y. Wu, J. Yu, and L. Zhang, “Thermal Deformation Stability Optimization Design and Experiment of the Satellite Bus to Control the Laser Communication Load's Acquisition Time,” *Appl. Sci.*, vol. 13, no. 9, 5502, 2023. doi: [10.3390/app13095502](https://doi.org/10.3390/app13095502)（bib: `2023-shi-thermal`）

粗捕捉の矩形走査（論文 Formula (1) 付近）:

| Shi ら | 値 | こちらへの写し方 |
|--------|----|------------------|
| ビーコン拡がり `θ_bc` | 0.313 mrad | 検出半径 ≈ 半角 → **150 µrad** |
| 重なり係数 `k` | 60% | step = (1−k)×300 µrad → **120 µrad** |
| 滞在時間 `T_d` | 0.2 s | 既存の **0.1 s** を維持（Shi より短い。2 倍にすると秒もだいたい 2 倍） |
| 30 s 要求時の FOU | 1.53 mrad 以下 | `max_range` **±1600 µrad** は据え置き |

Shi らは構造最適化で熱変形そのものを小さくする研究。走査パラメータのオーダー合わせに使っただけで、PAT アルゴリズムをコピーしたわけではない。通信ビーム（10–100 µrad）ではなく、**粗捕捉用の瞬間視野**として 0.3 mrad 級を置く、という読み替え。

被覆の穴なし条件: `step/√2 = 85 µrad < detect_radius 150 µrad`。

---

## 3. 実装

| ファイル | 変更 |
|----------|------|
| `src/pat_acquisition/configs/pat_femap_los_config.yaml` | scan を上記に変更。RESORB 用 yaml も同じ幾何 |
| `src/pat_acquisition/pat_acquisition_simulator.py` | 既定値を合わせ、穴がある設定は `ValueError` |
| `src/pat_acquisition/runners/pat_common.py` | fallback 既定値 |
| `src/pat_acquisition/README.md` | 粗捕捉の想定を追記 |

再実行（2026-08-16）:

```text
python src/pat_acquisition/models/sunface_deltaT_bcase_los/run_pat.py --cases 4-6,8-21
python src/pat_acquisition/models/sunface_deltaT_bcase_los/run_residual_fourier_pat.py --cases 13 --fit-mode causal
```

- モデル: 階層 sunface ΔT + `b_case`（`sunface_deltaT_bcase_los`）、Level-2 は **leave-one-case-out**
- ケース: 4–6, 8–21（17 本）。熱LOS係数の再同定はしていない
- 出力: `results/pat_acquisition/sunface_deltaT_bcase_los_model/pat/`
- 残差 Fourier: 同設定で case 13 のみ

やっていないもの: 旧 Fourier / sunface / temperature モデルの PAT、`run_adaptive_pat.py` の `b_case` 更新、RESORB 軌道誤差オーバーレイ、TD/Femap の再解析。ICSO 本線の定量は階層 bcase FF なので、本線の再計算は済んでいる。

---

## 4. 新しい PAT 数字（17 ケース、ケース平均の平均）

熱LOS残差は走査を変えても同じ（補正なし 692 µrad、bcase 8.5 µrad）。変わるのは時間と成功率。

**熱のみ**

| | 成功率 | 平均 `t_acq` | 旧（密スキャン） |
|--|--------|--------------|------------------|
| 補正なし | 100% | **12.1 s** | 124.6 s（21ケース表）/ 136.9 s（本文17ケース） |
| static | 100% | 0.27 s | 4.8 s |
| 階層 bcase | 100% | **0.10 s** | 0.116 s |
| 熱真値 | 100% | 0.10 s | 0.100 s |

**非熱込み（TLE vs POD）**

| | 成功率 | 平均 `t_acq` | ケース平均の中央値 | 旧平均 |
|--|--------|--------------|-------------------|--------|
| 補正なし | 98.3% | **16.3 s** | 15.8 s | 156.9 s |
| 階層 FF | **100%** | **4.75 s** | 1.63 s | 59.6 s |

短縮は約 71%（16.3 → 4.75 s）。成功率の改善幅は旧 94.0% → 97.1% より小さい。広い検出円のおかげで、補正なしでもほとんど箱に入る。

**残差 Fourier（case 13 MY、causal、非熱込み）**

| | 新 | 旧 |
|--|----|----|
| FF only | 1.64 s | 22.7 s |
| FF + 残差 Fourier | 0.78 s | 12.4 s |

比は同程度。絶対秒は走査に合わせて落ちた。

---

## 5. ケースによる見え方

- **MY**（熱 150–250 µrad）: 検出半径 150 µrad にほぼ入る。熱のみ補正なしでも 0.3–1 s。熱補正の本命ではない
- **PX/MX**（熱 ~0.9 mrad）: 熱のみ補正なし ~9–12 s。非熱込みでは軌道誤差が大きく、FF 後も PX は ~12 s 残る
- **PY**（熱 1.2 mrad 級）: 熱のみ補正なし ~32–37 s。Shi の 30 s 要求と同じオーダー。非熱込みは失敗が残り得るが、FF 後は ~1.5 s・成功率 100%

平均 12 s は PY/PX/MX が引き上げている。アブストでは平均に加えて、大きい太陽面で効く、と読めるようにする。

---

## 6. 論文への入れ方

- 秒は「この走査条件での proxy」。Shi と同じ 0.2 s dwell ならだいたい 2 倍
- 熱のみ 0.10 s は 1 dwell（残差 < 検出半径）。真値上限と同じ、という意味
- 本命のシステム数字は非熱込み 16.3 → 4.75 s
- `main.typ` 本文の旧 136.9 s / 171.0 s は未更新。アブストは執筆中

未着手（[`260813_scan_region_optimization.md`](260813_scan_region_optimization.md)）: 当たった半径や必要 scan area を独立指標にする話。今回は中心ずらしの時間だけを、妥当な幾何で出し直した。
