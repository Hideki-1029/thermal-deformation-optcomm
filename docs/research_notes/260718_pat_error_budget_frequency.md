# PAT 誤差バジェット：周期・サイズ・妥当性

- 作成: 2026-07-18
- 対象: `pat_femap_los_config.yaml` の非熱合成 + Femap 熱 LOS（`sunface_deltaT_bcase_los` PAT）
- 関連: `memo_in_repository.md`（軌道予測誤差方針）、`src/pat_acquisition/runners/pat_common.py`（`generate_nonthermal_error`）

---

## 0. 結論

五十里先生の予想どおり、**軌道予測誤差は熱ひずみと同じく軌道周期連動の低周波バイアス**として見える。現行 PAT 図で非熱ノルムがきれいな周期（しばしば 1 軌道に 2 ピーク）を示す主因は、非熱合成のうち **TLE vs POD の軌道予測誤差が卓越**していること。

研究テーマの置き方としても、「熱だけを観測から完全分離」ではなく、「軌道予測などと同帯域・同桁の非熱と共存する中で、熱モデル FF が粗捕捉の探索域をどれだけ減らすか」が手堅い。

**設定の妥当性（総評）:** LEO 小型・GNSS 非搭載を想定した粗捕捉の共存シナリオとしては妥当。特定機体の誤差バジェット再現ではない。軌道は実データ根拠が強く、姿勢・アライメント・ドリフトは代表オーダーの簡易モデル。

---

## 1. 非熱の合成式（実装）

```text
e_nonthermal(t)
  = e_orbit(t)          # sentinel1_tle_vs_pod（既定）
  + e_alignment         # 定数バイアス
  + e_attitude(t)       # サンプルごとガウス
  + e_drift(t)          # 正弦（設定周期）
```

設定: `src/pat_acquisition/configs/pat_femap_los_config.yaml`

| キー | 現行値 |
|------|--------|
| `orbit_error.source` | `sentinel1_tle_vs_pod` |
| `orbit_error.resample_mode` | `cyclic` |
| `attitude_random_1sigma_urad` | 50 |
| `alignment_bias_1sigma_urad` | 50 |
| `drift_amplitude_urad` | 30 |
| `drift_period_s` | 900（15 min） |

軌道誤差時系列: `results/orbit/sentinel1_tle_vs_pod/orbit_prediction_error_timeseries.csv`  
（Sentinel-1 POEORB 真値 vs 利用可能最新 TLE の SGP4 forward。ISL 角度は相手機 800 km 想定。）

---

## 2. 基準スケール

LTAN06 800 km 相当:

| 量 | 値 |
|----|-----|
| 軌道周期 Torb | ≈ 6050 s ≈ 101 min（設定 `orbit_period_s: 6050`） |
| 軌道周波数 forb | ≈ 1.65e-4 Hz（0.165 mHz） |
| 2 倍波 Torb/2 | ≈ 50.5 min ≈ 3.3e-4 Hz |

サイズは LOS 角度 [µrad]。熱は PAT 21 ケース（cases 4–6, 8–25）、軌道は上記 CSV、非熱合計は PAT 結果 CSV に基づく目安。

---

## 3. 誤差成分一覧（マージ表）

| 誤差成分 | 主周期 | 周波数（目安） | サイズ [µrad] | 妥当性 | メモ |
|----------|--------|----------------|---------------|--------|------|
| 熱ひずみ LOS（Femap） | Torb（~101 min）が主。2 倍波 ~50 min あり | ~1.7e-4 Hz（2 倍 ~3.3e-4） | ノルム平均（バイアス）: 百〜千数百（ケース横断中央値 ~900）。軌道内: std ~0–120、pp ~数〜500（中央値 ~340） | 高い（本解析の本体） | 日照/蝕駆動。太陽面・発熱で DC が大きく変わる。支配軸の軌道内スイングが主。MY など小さいケースでは軌道内ほぼフラット。case23 FFT でも 101 min 最大・50.6 min 次 |
| 軌道予測誤差（TLE vs POD） | Torb 族（Torb, Torb/2）＋ TLE age の数時間エンベロープ | ~1e-4 Hz 台 ＋ ~1e-5 Hz | ノルム: 平均 ~280、std ~130、p95 ~510、pp ~600。軸成分 1σ ~200–230。vector RMS ~310 | 高い（意図的 baseline） | 非熱の周期の主役。角度ノルムで T/2（~50 min）が目立ちやすい＝ PAT 図の double-hump。GNSS 非搭載小型の代表として採用。Sentinel-1 代理は軌道族は合うが TLE 運用品質は本物の超小型より良い可能性（誤差やや小さめ側） |
| 低周波ドリフト（モデル） | 設定 900 s = 15 min | ~1.1e-3 Hz | 振幅 30（正弦ピーク） | 弱い（埋め草） | 900 s に強い物理根拠は薄い。振幅は小さく結果を支配しない |
| アライメント残差 | DC（準静的） | ≈ 0 | 1σ 50 の定数バイアス | 校正後残差としては妥当寄り | 未校正なら mrad 級もあり得る。粗捕捉前提では「校正済み残差」の置き方でよい |
| 姿勢ランダム | 広帯域（サンプル上は白） | 概念的には mHz〜Hz 級 | 1σ 50（時刻サンプルごと） | だいたい妥当（オーダー） | 文献帯「数十〜数百 µrad」に入る。STT 付き小型なら現実的、悪い超小型系ならやや楽観。60 s 刻み白ガウスは PAT 用簡易化（実 ADCS は有色） |
| 非熱合計（上の合成） | 軌道予測に支配され Torb 族 | ~1e-4 Hz 台 | ノルム: 平均 ~270–320、std ~130、p95 ~500、pp ~600（ケース間でほぼ同型） | シナリオとして妥当 | PAT 図の nonthermal magnitude。`cyclic` リサンプルで見た目の規則性が強調される。相手機側軌道誤差の二重化・振動（高周波）は未投入 |

---

## 4. 五十里先生指摘との対応

指摘（要旨）: 軌道予測誤差も軌道周期と連動する低周波バイアスに見え、熱ひずみと同種の動きをする。研究から外すのは危ない。

本設定での答え:

1. **周期** — 熱も軌道予測も主に Torb（および Torb/2）。帯域はともに ~1e-4 Hz 台で重なる。
2. **サイズ** — TLE-only で軌道 ~300 µrad RMS 級。熱の軌道内スイングやケースによっては熱 DC と同桁〜熱の方が大きい。
3. **含意** — 周波数分離で熱だけ抜くのは難しい。共存下での熱 FF 評価が本線。

昔メモの「熱ひずみ 0.01–0.1 Hz」は過大。本解析の熱は **1e-4 Hz 台**（PAT 時間スケールでは準静的）。

---

## 5. 論文・口頭での言い方（案）

- 軌道誤差は Sentinel-1 TLE vs POD の実データ（ISL 角度換算）。姿勢・アライメント・ドリフトは代表的オーダーの簡易モデル。
- 非熱の周期構造は主に軌道予測誤差の幾何投影であり、熱ひずみと同じく軌道位相依存。
- 主張は「熱の完全分離」ではなく「同帯域非熱共存下での粗捕捉改善」。

---

## 6. 数値の出所（再現）

| 項目 | 出所 |
|------|------|
| 軌道ノルム統計 | `results/orbit/sentinel1_tle_vs_pod/orbit_prediction_error_timeseries.csv` |
| 熱・非熱 PAT 統計 | `results/pat_acquisition/sunface_deltaT_bcase_los_model/pat/*/pat_acquisition_results.csv`（21 ケース） |
| 例示ケース FFT | case23 `..._MX_STTLCT_PROP_HEAT_MX_0p5`（熱ノルム: 101 min 主、非熱ノルム: ~50 min 主） |
| 合成ロジック | `generate_nonthermal_error` in `src/pat_acquisition/runners/pat_common.py` |
