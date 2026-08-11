# 軌道予測誤差：仮定・座標系・PAT 接続

- 作成: 2026-07-18
- 目的: 実装（特に STT フレームへの射影）に入る前に、現行パイプラインの仮定を固定する
- 関連:
  - 方針メモ: [`memo_in_repository.md`](memo_in_repository.md)（軌道予測誤差との分離）
  - 誤差バジェット全体: [`260718_pat_error_budget_frequency.md`](260718_pat_error_budget_frequency.md)
  - 熱 LOS 定義: [`femap_stt_lct_los_definition.md`](femap_stt_lct_los_definition.md)
  - 実装: `src/orbit/`、`src/pat_acquisition/runners/pat_common.py`
  - 結果: `results/orbit/sentinel1_tle_vs_pod/`

---

## 0. 一言で

現行の軌道予測誤差は、

```text
Sentinel-1 POD（真値） vs 最新 TLE の SGP4 forward
  → 位置誤差 [m]
  → 「相手位置既知」の ISL 視線に対する角度誤差 [µrad]
  → PAT 非熱項へ cyclic リサンプルして足す
```

である。**サイズ・軌道位相依存のオーダー感は熱と同桁で使える**が、**角度の x/y 軸は STT/ボディ標準系と一致していない**（LOS 横断面上の便宜的 2 軸）。

次の実験候補: **1 ケースだけ** orbit catalog 姿勢を使い、軌道角度誤差を STT 標準 x/y に射影して PAT に載せる。

---

## 1. 研究上の位置づけ

五十里先生指摘: 軌道予測誤差も軌道周期連動の低周波バイアスに見え、熱ひずみと同種。研究から外すのは危ない。

本リポジトリの答え:

| 項目 | 方針 |
|------|------|
| 代表シナリオ | GNSS 非搭載の一般 LEO 小型（TLE-only baseline） |
| 代理データ | Sentinel-1（dawn-dusk SSO、LTAN06 条件の代理） |
| 真値 | `AUX_POEORB` |
| 予測 | 各評価時刻で `epoch ≤ t` の最新 GP/TLE を **forward** SGP4 |
| 使わない | 未来 TLE の backward 伝搬 |
| 評価の置き方 | 熱の完全分離ではなく、**同帯域非熱共存下での熱 FF** |

GNSS / RESORB 級はバックアップ（今はやらない）。SEIRIOS 向け改善オプションとして別論。  
論文の GPS級シナリオ妥当性・文献・誤差生成は [`260811_gnss_optical_comm_orbit_error.md`](260811_gnss_optical_comm_orbit_error.md)。

---

## 2. パイプラインと成果物

```text
python src/orbit/run_orbit_prediction_error.py
```

設定: `src/orbit/orbit_prediction_error_config.yaml`

| 出力 | 内容 |
|------|------|
| `orbit_prediction_error_timeseries.csv` | 時刻・TLE age・位置誤差 RTN・`isl_angle_{x,y,norm}_urad` |
| `orbit_prediction_error.png` | 全窓（~26 h） |
| `orbit_prediction_error_3orbits.png` | 先頭 3 軌道（Torb=6050 s、熱/PAT 窓と揃えた図） |
| `orbit_prediction_error_summary.csv` | TLE age ビン別 RMS |

代表スケール（2026-06 POEORB 窓、相手 800 km）:

- 位置: 沿トラックが支配、数百 m〜km
- ISL 角度ノルム: 平均 ~280 µrad、p95 ~510 µrad、vector RMS ~310 µrad

---

## 3. 幾何・相手機の仮定

### 3.1 シナリオ（実装どおり）

```text
自分（chaser）: TLE 予測位置（誤差あり）
相手（partner）: 真値既知（GNSS 想定）
相手の置き方: 自分の真値位置から、沿トラック前方 isl_range_km（既定 800 km）
```

コード: `nominal_isl_partner_position`（RTN の along-track に置く）  
変換: `position_error_to_isl_angle_urad`

```text
δr_perp = 位置誤差の LOS 垂直成分
θ ≈ |δr_perp| / range     →  [µrad]
```

地上局リンクではない。**衛星間（ISL）片側誤差**モデル。

### 3.2 意図的に入れていないもの

| 省略 | 理由・影響 |
|------|------------|
| 相手側の軌道誤差 | 両側 TLE だと相対が複雑。まず片側でオーダーを見る |
| 地上局幾何 | 研究対象が LEO–LEO 寄り。地上は別幾何 |
| 自機姿勢誤差との同時厳密結合 | 非熱の姿勢項は別の簡易ガウス |
| 熱解析エポック（~2031 TD）と S1 窓（2026）の位相一致 | PAT では `cyclic` で時間軸だけ合わせる近似 |

### 3.3 ユーザー直観との対応

「相手（or 地上局）の位置は分かっていて、自分は予測しかない → 視線角誤差」は **正しい**。  
現行実装はその衛星間版（相手＝沿トラック、位置真値既知）。

---

## 4. 角度 x,y の座標系（重要）

### 4.1 現行定義（STT ではない）

`isl_angle_x/y` は **STT ボディ X/Y でも RTN でもない**。

```text
los     = 自分(真値) → 相手 の単位ベクトル（ECEF）
ref     ≈ ECEF +Z（los とほぼ平行なら +Y に切替）
axis_x  = normalize(los × ref)
axis_y  = los × axis_x

(x, y)  = δr_perp を axis_x/y に射影した角度
```

コメント上も “arbitrary but stable 2D PAT basis”。

| 量 | 基底依存 |
|----|----------|
| `isl_angle_norm` | **非依存**（物理的な角度大きさ） |
| `isl_angle_x`, `isl_angle_y` | **依存**（便宜軸。軌道周回で回転し、時々不連続） |

### 4.2 3 軌道図で x,y が縦に飛ぶ理由

先頭 3 軌道では TLE 更新なし（TLE age は直線）。  
縦ジャンプは **基底の符号反転・急回転**で、ノルムは連続。物理的な LOS 誤差の飛びではない。

### 4.3 熱 LOS（Femap）との関係

熱の主値 `far_field_los`（≈ `relative_rotation`）:

```text
PAT / far-field = LCT 光軸回転 − STT 姿勢基準回転
名目 LOS = ボディ −Z（LCT = MZ、STT = PZ）
x,y ≈ その横倒れのボディ成分
```

PAT では現状:

```text
pointing = e_nonthermal + θ_thermal − θ̂
```

で **成分ごと加算**している。ノルム同居としてはよいが、**軸が同じとは限らない**。

### 4.4 ECEF-Z と衛星 MZ（LCT）は一致するか

**しない。** ECEF-Z は北極方向。衛星 MZ はボディ固定で姿勢則に従い回転する。  
軌道誤差の基底作りに使う ECEF-Z と、LCT の −Z は無関係。

---

## 5. TLE「更新」とは何か

下段プロットの鋸歯リセット = **新しい GP/TLE 要素セットへの切替**。  
SGP4 アルゴリズムの更新ではない。

```text
各時刻 t:
  record = epoch ≤ t の最新 TLE
  r_pred = SGP4_forward(record, t)
  error = r_pred − r_POD(t)
```

更新しても誤差が必ず減るとは限らない（新しい TLE でも POD との差は残る。角度ノルムがわずかに悪化する例もある）。長期的には「古い TLE のまま」よりマシ、という程度。

---

## 6. PAT への入力方法（現行）

設定: `pat_femap_los_config.yaml`

```yaml
orbit_error:
  source: sentinel1_tle_vs_pod
  timeseries_csv: results/orbit/sentinel1_tle_vs_pod/orbit_prediction_error_timeseries.csv
  resample_mode: cyclic
```

処理 (`generate_nonthermal_error` / `generate_orbit_prediction_error`):

1. CSV から `isl_angle_x/y` を読む  
2. Femap `time_s` へ `cyclic` マップ（目標長 ≪ CSV 長なら先頭区間をそのまま使う）  
3. アライメント定数・姿勢乱数・ドリフトを加算  
4. 熱 LOS と同じ `[N,2]` として PAT に渡す  

典型熱解析窓: **3 軌道**（~Torb×3、Torb≈6050 s ≈ 101 min）。  
図: `orbit_prediction_error_3orbits.png` がこの窓に対応。

---

## 7. 周期の見え方（熱 vs 軌道）

| | 熱ひずみ | 軌道予測（角度ノルム） |
|--|----------|------------------------|
| 駆動 | 日照/蝕（真に ~Torb） | 位置誤差は準静的〜数時間 ＋ 投影が軌道位相で変化 |
| 成分 | 太陽面により 1 軸支配が多い | 2 軸が正負に振れる |
| ノルム | ~Torb が目立つ | ~Torb/2（double-hump）が目立ちやすい |

どちらも **軌道位相にロックした ~1e-4 Hz 台**。五十里先生の「同じ軌道周期族」と矛盾しない（基本波 vs ノルムで目立つ 2 倍波）。

---

## 8. orbit catalog 姿勢とのギャップ

`cases/orbit_catalog.xlsx` にはケースごとの姿勢意図がある:

```text
sun_face + constraint_target/face
  → eff_sun_face / eff_velocity_face / eff_nadir_face
```

例:

| 軌道 | 速度面 | 含意（LCT=MZ のとき） |
|------|--------|----------------------|
| `..._MY_SUN` | MZ | LCT が速度方向 ≈ 沿トラック相手と整合しやすい |
| `..._MX_SUN` | PY | LCT は沿トラックを向いていない → 現行「相手＝沿トラック」と矛盾しうる |

現行軌道誤差パイプラインは **この catalog 姿勢を使っていない**。  
常に「沿トラック相手 + 任意 2 軸」で、全太陽面ケースに同じ CSV を cyclic 流し込み。

---

## 9. 既知の限界（論文・口頭での言い方）

正直に書ける範囲:

1. 軌道は Sentinel-1 TLE vs POD の実データ（ISL 角度換算、相手 800 km、片側誤差）  
2. 姿勢・アライメント・ドリフトは代表オーダーの簡易モデル  
3. **角度 2 成分の軸は STT と未接続**。同居評価は主にノルム／探索半径のオーダー  
4. 熱時刻と軌道誤差時刻の位相は cyclic 近似  
5. Sentinel-1 の TLE 運用品質は本物の超小型より良い可能性（誤差やや小さめ側）

---

## 10. STT 射影（bcase 全軌道・2026-07-18）

**目的:** `sunface_deltaT_bcase` が使う orbit catalog 行について、TLE 軌道誤差を STT x/y で見る。

### 10.1 実行

```powershell
python src/orbit/run_orbit_error_stt_frame.py --all-bcase-orbits --update-orbit-catalog
```

| 出力 | パス |
|------|------|
| 各軌道 CSV/PNG | `results/orbit/sentinel1_tle_vs_pod/orbit_error_stt_<td_orbit_name>*` |
| サマリ | `.../orbit_error_stt_summary.csv` |
| catalog 列 | `cases/orbit_catalog.xlsx`（灰列、下記） |

実装: `src/orbit/body_attitude.py`, `src/orbit/run_orbit_error_stt_frame.py`

### 10.2 相手機／地上局の置き方

LCT = ボディ −Z。その向きでモードを自動判定:

| LCT の向き | mode | range | 備考 |
|------------|------|--------|------|
| ~nadir | `ground_nadir` | 高度（\|r\|−R_E） | 天底の地上局仮定 |
| ~±velocity | `isl_along_track` | 800 km | 前後の ISL |
| ~zenith | `zenith_proxy` | 800 km | **計算はできるがリンク非現実** |
| その他 | `isl_along_boresight` | 800 km | ボアサイト上の仮想相手 |

### 10.3 bcase 6 軌道の結果

| 軌道 | partner | status | STT norm mean (3orb) |
|------|---------|--------|----------------------|
| `..._MY_SUN` | isl along-track | ready | ~285 µrad |
| `..._HOT_MY_SUN` | isl along-track | ready | ~285 |
| `..._LTAN18_..._MY_SUN` | isl along-track | ready | ~290 |
| `..._PY_SUN` | isl anti-along-track | ready | ~285 |
| `..._PX_SUN` | **ground_nadir** | ready | ~694（沿トラック誤差が角度にフル寄与） |
| `..._MX_SUN` | **zenith_proxy** | ready_unrealistic_link | ~612 |

- MY 系: legacy ノルムと一致（軸変換のみ）  
- PX: 地上局＋天底視線のため、沿トラック位置誤差が角度に効きノルム増  
- **MX: LCT が天頂向き。計算済みだが光通信リンクとしては非現実**（唯一の注意軌道）  
- 未使用の `..._MZ_SUN`（LCT∥太陽）は bcase 対象外。必要なら別途

注意: 姿勢・高度は Sentinel-1 POD 状態から作っている（TD の 800 km Kepler そのものではない）。LTAN06 代理としての近似。

### 10.4 orbit_catalog 列（姿勢依存なので case ではなく orbit に記載）

| 列 | 意味 |
|----|------|
| `pat_orbit_error_frame` | **PAT が今実際に足している枠**。`stt_body_lct_boresight_cyclic`（2026-07-18 配線後） |
| `orbit_error_stt_frame` | STT 解析成果の枠名 `stt_body_lct_boresight` |
| `orbit_error_partner_mode` | 上記 partner mode |
| `orbit_error_stt_status` | `ready` / `ready_unrealistic_link` / `n/a` |
| `orbit_error_stt_notes` | 短い説明 |

PAT 設定: `pat_femap_los_config.yaml` の `orbit_error.frame: stt_body`。  
`case_matrix.orbit_case` → `orbit_error_stt_<orbit>.csv` の x/y を cyclic で非熱に加算。  
legacy に戻すときは `frame: legacy`。

### 10.5 まだやっていないこと

- 熱 LOS との符号・位相の最終キャリブ  
- TD 軌道要素そのものでの r,v（S1 代理をやめる）  
- MX（zenith_proxy）のリンク解釈の扱い（現状は計算値をそのまま PAT に載せる）

---

## 11. 主要コード参照

| 役割 | 場所 |
|------|------|
| TLE vs POD 本体 | `src/orbit/prediction_error.py` |
| 角度・相手幾何 | `src/orbit/isl_geometry.py` |
| 実行・図 | `src/orbit/run_orbit_prediction_error.py` |
| PAT 読込・リサンプル | `src/orbit/pat_orbit_error.py` |
| 非熱合成 | `src/pat_acquisition/runners/pat_common.py` → `generate_nonthermal_error` |
| PAT 加算 | `pat_acquisition_simulator.py`: `pointing = nonthermal + thermal − θ̂` |
| 姿勢メタ | `cases/orbit_catalog.xlsx`（`eff_*_face` 等） |
