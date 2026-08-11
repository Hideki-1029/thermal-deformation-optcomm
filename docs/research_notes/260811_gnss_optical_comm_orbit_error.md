# GNSS搭載 LEO 光通信と GPS級軌道誤差シナリオ

- 作成: 2026-08-11
- 目的:
  1. 運用・実証のLEO光通信で GNSS/GPS がどう使われているかを文献で押さえる
  2. 論文に **「GPS搭載時の小さな軌道予測誤差」ケース** を入れる妥当性を示す
  3. 次節で書く **GPS級軌道予測誤差の生成方法** の受け皿にする
- 関連:
  - TLE baseline 実装: `[260718_orbit_prediction_error_assumptions.md](260718_orbit_prediction_error_assumptions.md)`
  - 方針メモ: `[memo_in_repository.md](memo_in_repository.md)`（軌道予測誤差との分離）
  - データ: `[data/orbit/README.md](../../data/orbit/README.md)`
  - Adaptive 二層: `[260808_adaptive_two_layer_b_update.md](260808_adaptive_two_layer_b_update.md)`

---

## 0. このメモの結論（論文で使う一文）

```text
近年のLEO光通信（特に狭ビームの初期捕捉）では onboard GNSS を使う例が多く、
TLE-only より桁違いに小さい軌道不確かさになる。
本研究は (A) GNSS非搭載〜TLE前提の厳しい一般ケースと、
(B) GPS/GNSS搭載時の小さな軌道誤差ケースの両方を評価する。
```

- (A) = 既存 `sentinel1_tle_vs_pod`（〜数百 µrad @ 800 km）
- (B) = **実装済み** `sentinel1_resorb_vs_pod`（RESORB−POEORB、〜22 µrad）。手順は §5

---



## 1. なぜ論文に GPS級ケースが必要か


| 観点       | 内容                                                           |
| -------- | ------------------------------------------------------------ |
| 運用現実     | 実証・商用の光リンクは GNSS ありが多い（§2）                                   |
| 技術的差分    | TLE 不確かさは熱LOSと同桁になり得る。GNSS級だと軌道項がほぼ床になる                      |
| 主張の守り    | 「熱FFは軌道誤差が大きいときだけ意味がある」と言われないよう、**軌道が小さいときでも熱補正が効く**ことを見せられる |
| Adaptive | Clean（軌道小）では `b_case` 吸い上げの誤学習が減り、目標Aのデモがしやすい                |


研究の主軸を GPS 全振りにしない。**TLE = baseline / GPS級 = 比較・SEIRIOS寄りオプション**。

---



## 2. 文献・事例マップ（GNSS × 光通信）



### 2.1 実証ミッション：onboard GPS を明示



#### TBIRD（NASA / MIT LL、LEO→地上 100/200 Gbps）

- Riesing et al., SPIE 2023: on-orbit PAT results  
- Schieler et al., SmallSat 2023 / NTRS: operations  
- Riesing, CLEO 2025 slides (NTRS): two-year summary

要点:

- パス直前に **onboard GPS 由来の fresh ephemeris** を RF で下ろし、OGS 用 TLE を作る
- 公開TLEだけでは捕捉が弱い／失敗しやすい、と明記されている例がある
- 捕捉失敗の常见因として ephemeris / TLE 配信の問題が挙がる

→ 「光通信の初期捕捉では軌道情報の質がクリティカル」「GPS級の新鮮な軌道を使うのが実運用」を示す強い事例。

#### VISION（CubeSat 光クロスリンク向け相対航法）

- GPS-based relative navigation for laser crosslink alignment (Aerospace 2025, VISION)  
- 両機の GPS を Sバンドで交換し、相対状態を推定して PAT に供給  
- HW-in-the-loop で baseline 〜1000 km に sub-meter 級、など

→ ISL では「自分の絶対軌道」だけでなく **相対 GNSS** が初期指向の本線になりうる。

### 2.2 解析・提案：TLE vs GNSS を直接比較



#### RF-assisted / hybrid ISL（GNSS交換で uncertainty cone 削減）

- Fernández-Niño et al., IEEE OJ-COMS 2024: *RF-Assisted Uncertainty Cone Reduction in Free-Space Optical Inter-Satellite Links*  
- 続報寄り: RF-assisted compensation for rapid optical acquisition (2026)

要点（論文の主張を要約）:

- 多くの衛星は TLE 伝搬で初期指向するが、誤差がビームより大きくなり捕捉が重い
- RF で GNSS 位置を交換すると、TLE 伝搬より指向精度が大きく改善（当該論文では最大約 99% 改善と報告）
- つまり **光ISLの文献自体が「TLEは不足、GNSSが効く」を主題にしている**

→ 本研究が GPS級ケースを置くことの外的妥当性が高い。

### 2.3 コンステ／規格層（個別GPS論文ではないが文脈）

- SDA Transport Layer / Optical Communications Terminal (OCT) Standard  
  - 狭ビーム光ISLの大量展開が前提。運用コンステは高精度航法を前提にしがち
- Starlink 等の商用光メッシュ  
  - 端末ごとのGPS論文は少ないが、運用光ISLの主流が「高精度航法あり」側であることの文脈



### 2.4 GNSS 軌道精度そのもの（光通信以外だがスケール用）

LEO onboard / near-real-time GNSS OD の文献オーダー:


| 方式                                    | 位置誤差の目安                  | 出典イメージ                            |
| ------------------------------------- | ------------------------ | --------------------------------- |
| GPS broadcast のみ onboard              | dm〜m 級もあり得る              | Montenbruck系・各種 RT OD レビュー        |
| Galileo/BDS + broadcast、または HAS 等     | おおよそ **〜0.1 m** 前後も報告    | NAVIGATION 2021; Sentinel-6 HAS 等 |
| 地上準リアルタイム restituted（Sentinel RESORB） | cm〜dm（要求 2D RMS 10 cm 級） | Copernicus POD 製品仕様               |


800 km 相手への角度換算の感覚:

```text
0.1 m / 800 km ≈ 0.13 µrad
1 m   / 800 km ≈ 1.3 µrad
10 m  / 800 km ≈ 12.5 µrad
```

TLE baseline（〜300 µrad RMS）に対し、**GPS級は実質「軌道項ほぼ無視できる」か「数十µrad以下の床」**。

### 2.5 リポジトリ内の既存整理との対応

`[memo_in_repository.md](memo_in_repository.md)`:

- TLE-only = GNSS非搭載の一般小型向け baseline（研究室体感「小型の〜半分はGNSS無し」）
- GNSS/RESORB = バックアップ、SEIRIOS向け

本メモの更新:

- **光通信に限ると GNSS ありが多い**（§2.1–2.3）
- だから論文に GPS級ケースを入れるのは「特例の楽な仮定」ではなく **運用寄りシナリオ**
- TLE-only は依然として「非搭載・粗い軌道情報」の一般性／厳しい側として残す

---



## 3. 論文での置き方（推奨）



### 3.1 二シナリオ


| ID     | 名前        | 軌道誤差                                | 役割                |
| ------ | --------- | ----------------------------------- | ----------------- |
| S-TLE  | TLE-only  | Sentinel-1 TLE vs POEORB → 〜数百 µrad | 主シナリオ・五十里指摘への応答   |
| S-GNSS | GPS/GNSS級 | §5 で生成（小）                           | 運用寄り・熱補正が相対的に目立つ側 |


共通:

- 熱LOS・`b_case` FF・PAT指標は同じ
- 非熱の姿勢・アライメントは両シナリオで残してよい（軌道だけ落としてもよい）



### 3.2 言えること / 言わないこと

言える:

- 光通信実証・ISL文献では GNSS 利用が一般的／推奨される
- GNSS級では軌道由来の scan-center 不確かさが熱LOSより十分小さい
- その条件下でも熱 hierarchical FF が捕捉時間を改善しうる（結果次第）

言わない:

- 「すべてのLEO小型がGPS必須」
- 「GPSがあれば熱補正は不要」（逆に熱が相対的に残る）
- 「RESORB = onboard GPSそのもの」（RESORBは地上処理込みの準リアルタイム精密軌道）



### 3.3 Adaptive との接続

`[260808_adaptive_two_layer_b_update.md](260808_adaptive_two_layer_b_update.md)` の Clean/Stress:

- S-GNSS ≈ Clean → `w_orbit_small` が大きく、遅い `b_case` 吸い上げのデモ向き
- S-TLE ≈ Stress → age ゲート・誤学習チェック向き

---



## 4. 文献リスト（メモ用）

必須寄り（論文 Related Work / 妥当性）:

1. TBIRD operations / PAT（Schieler SmallSat 2023; Riesing SPIE 2023）— onboard GPS ephemeris と捕捉
2. Fernández-Niño et al., IEEE OJ-COMS 2024 — TLE vs GNSS 交換の指向改善
3. VISION GPS relative nav（Aerospace 2025）— ISL 向け相対GPS
4. 自リポ TLE vs POEORB 結果 — S-TLE の定量

スケール・生成用:

1. Sentinel-1 `AUX_POEORB` / `AUX_RESORB` 公開製品（AWS `s1-orbits`）
2. LEO real-time GNSS OD（例: Montenbruck et al., NAVIGATION 2021; Sentinel-6 HAS 論文）

背景:

1. SDA OCT Standard — 運用光ISLの文脈
2. OSIRIS / Flying Laptop beam bias（Giggenbach）— 軌道以外の open-loop bias

---



## 5. GPS級軌道予測誤差の生成（実装済み）



### 5.0 合意メモ: RESORB / POEORB の役割

現状、公開データだけで「GPS onboard の軌道予測値に近いもの」を取るなら **RESORB がベスト**。POEORB はその真値として使う。

```text
予測（GPS級の代理）: AUX_RESORB   … 準リアルタイム restituted
真値:                 AUX_POEORB  … 最終 precise
誤差:                 RESORB − POEORB → ISL / STT 角度 [µrad]
```


| 製品     | 何か              | レイテンシ目安       | 製品仕様の精度目安          |
| ------ | --------------- | ------------- | ------------------ |
| RESORB | 地上PODが早めに出す復元軌道 | sensing 後〜数時間 | 10 cm 2D RMS（カタログ） |
| POEORB | 地上PODの最終精密軌道    | 〜20日後         | 5 cm 3D RMS（カタログ）  |


但し書き:

- どちらも **onboard GPS 瞬間出力ではない**（地上POD製品）
- 論文では「RESORB級を GNSS 利用時の代理」と書く



### 5.1 採用案と手順

**採用: 案A（RESORB − POEORB）**。TLE と同じ 2026-06-13〜15 窓。

```powershell
# 1) RESORB vs POEORB 時系列
python src/orbit/run_orbit_prediction_error_resorb.py

# 2) STT フレーム射影（bcase 全 orbit）
python src/orbit/run_orbit_error_stt_frame.py `
  --config src/orbit/orbit_prediction_error_resorb_config.yaml `
  --timeseries-csv results/orbit/sentinel1_resorb_vs_pod/orbit_prediction_error_timeseries.csv `
  --all-bcase-orbits

# 3) PAT（出力は pat_resorb、TLE baseline は上書きしない）
python src/pat_acquisition/models/sunface_deltaT_bcase_los/run_pat.py `
  --config src/pat_acquisition/configs/pat_femap_los_config_resorb.yaml
```


| 項目                   | パス / キー                                                              |
| -------------------- | -------------------------------------------------------------------- |
| 軌道設定                 | `src/orbit/orbit_prediction_error_resorb_config.yaml`                |
| 軌道ランナー               | `src/orbit/run_orbit_prediction_error_resorb.py`                     |
| 成果物                  | `results/orbit/sentinel1_resorb_vs_pod/`                             |
| PAT 設定               | `src/pat_acquisition/configs/pat_femap_los_config_resorb.yaml`       |
| PAT 出力               | `results/pat_acquisition/sunface_deltaT_bcase_los_model/pat_resorb/` |
| `orbit_error.source` | `sentinel1_resorb_vs_pod`                                            |


相手距離・幾何は TLE ケースと同一（`isl_range_km: 800`、STT `stt_body`）。

### 5.2 観測スケール（同窓・実装結果）


| シナリオ        | 位置 RMS | ISL angle RMS | 備考               |
| ----------- | ------ | ------------- | ---------------- |
| S-TLE（既存）   | ~821 m | ~309 µrad     | TLE vs POEORB    |
| S-GNSS（本実装） | ~18 m  | ~22 µrad      | RESORB vs POEORB |


- 角度で **約 14× 小さい**（TLE比）
- カタログの「RESORB 〜cm」より大きい。公開 RESORB−POEORB のこの窓・この実装での実測差として扱う
- それでも TLE 同桁の熱LOSに対しては軌道床が十分下がる

図:

- `results/orbit/sentinel1_resorb_vs_pod/orbit_prediction_error.png`
- `.../orbit_prediction_error_3orbits.png`
- STT: `.../orbit_error_stt_*_3orbits.png`



### 5.3 PAT 結果スナップショット（21ケース平均）


| arm                          | S-TLE mean tacq | S-GNSS (RESORB) mean tacq |
| ---------------------------- | --------------- | ------------------------- |
| thermal+nonthermal, no corr. | ~157 s          | ~129 s                    |
| **bcase + nonthermal**       | **~60 s**       | **~2.8 s**                |
| bcase only（熱のみ）              | ~0.12 s         | ~0.12 s                   |


解釈:

- 熱だけなら両シナリオとも bcase でほぼ床（軌道項が無い）
- 非熱込みでは、GPS級だと **bcase 補正後の捕捉時間が桁で下がる**（軌道床が小さくなるため）
- 「運用寄り GNSS ケースでも熱 hierarchical FF が効く／残差非熱が小さい」を示せる



### 5.4 チェックリスト

- [x] 予測=RESORB、真値=POEORB
- [x] 案A実装・TLE同窓
- [x] PAT `sentinel1_resorb_vs_pod` 配線
- [x] 代表スケール表
- [x] 図・PAT summary 生成
- [ ] カタログcm級との差の原因精査（任意・今後）
- [ ] 論文 Methods 二シナリオ段落の英文下書き

---



## 6. 次アクション

1. [x] §5 実装（RESORB pipeline + PAT）
2. **[ ] 論文に結果反映（忘れない）** — Methods 二シナリオ + Results で S-TLE vs S-GNSS の捕捉時間表/図
   - 材料: §5.2 スケール、§5.3 PAT スナップショット、`pat/` vs `pat_resorb/`
   - 関連: `papers/ICSO/` 執筆時に必ず入れる
3. [ ] RESORB−POEORB がカタログcmより大きい理由の任意精査
4. → **次の実装フォーカスは Adaptive 二層 `b` 更新**（[`260808_adaptive_two_layer_b_update.md`](260808_adaptive_two_layer_b_update.md)）

---



## 7. 改訂履歴


| 日付         | 内容                                                      |
| ---------- | ------------------------------------------------------- |
| 2026-08-11 | 初版。文献マップと論文二シナリオ方針。§5 はプレースホルダ                          |
| 2026-08-11 | §5.0: RESORB=GPS級代理、POEORB=真値                           |
| 2026-08-11 | §5 実装完了。RESORB pipeline + PAT `pat_resorb`。スケール〜22 µrad |


