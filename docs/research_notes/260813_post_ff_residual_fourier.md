# 熱 FF 後の残差 Fourier（運用補正・後段）

- 作成: 2026-08-13
- 目的: 階層熱 FF の**あと**に残る周期床（主に軌道射影）を、捕捉後残差の Fourier で次周へ回す
- これは **Adaptive `b_case` 更新ではない**（熱テーブルは動かさない）
- 二層 `b` 更新の正本: [`260808_adaptive_two_layer_b_update.md`](260808_adaptive_two_layer_b_update.md)

---

## 0. 身分（Adaptive b と混ぜない）

| | Adaptive `b`（260808） | 本ノート |
|--|------------------------|----------|
| 動かすもの | `δb[mode]`、条件付きで `b_case` | 残差 Fourier 係数（`c0, ak, bk`） |
| 熱モデル | 更新する（遅い層） | **更新しない**（事前の `a·ΔT+b_case` を固定） |
| 主に効く相手 | 熱 DC のずれ | 熱 FF 後の **Torb 族の AC 床** |
| 実装 | `adaptive.py` / `run_adaptive_pat.py` | `residual_fourier.py` / `run_residual_fourier_pat.py` |

Fourier の `c0` は残差 DC を吸収し得るが、Level-2 の `b_case` テーブルとは別物。打上げ後アライメント等の **熱モデル誤差の入れ方** は [`260813_thermal_model_mismatch.md`](260813_thermal_model_mismatch.md)。

### 0.1 「Adaptive」と呼ぶか（2026-08-13）

**無修飾の Adaptive にはしない。** causal は軌道上で係数を更新するが、熱モデル適応ではない。

| 呼び方 | よいか | 理由 |
|--------|--------|------|
| Adaptive `b` / 熱モデル適応 | ✗ | テーブル `a,b` を動かさない |
| Adaptive correction（タイトルの広い意味で、Fourier 単体） | 微妙 | 読者は熱係数のオンライン同定を想像しやすい |
| 運用補正・残差の周期フィードフォワード・harmonic update | ○ | 実態。周 n の `r` → 周 n+1 の同じ `φ` |
| batch Fourier を Adaptive | ✗ | その場の未来サンプルも使う。較正上限 |

causal の `c0,ak,bk` は「パラメータを残差で更新している」ので制御の Adaptive feedforward / repetitive には入る。ただしアブストの Adaptive はもともと **物理 FF のあとの軌道上モデル更新（主に `b`）** だった。Fourier をその枠に入れると、効いている相手が軌道 AC なのに熱適応に読める。

論文では: 主結果は階層 FF。後段は **on-orbit residual correction**（定数 `δb` と周期 Fourier を並べる）。Adaptive と書くなら `δb` 側に寄せ、Fourier は repetitive / harmonic と分ける。

---

## 1. 狙う量

定数 `δb` は遅い DC 用で、熱 FF 後の軌道周期 AC には効きにくい。innovation に軌道位相 Fourier を載せる。

```text
r(t) = (θ_thermal + e_nonthermal) − θ_ff(t)
θ_ff = b_case + a·ΔT (+ 必要なら静的軸)
```

```text
r̂_x(φ) = c0 + Σ_k [ak cos(kφ) + bk sin(kφ)]   (y も同様)
φ = 2π t / Torb
```

- 熱込み Fourier（GEO TMC / 旧 `fourier_los`）とは別物。こちらは **階層 FF で熱を落としたあとの床**
- 「軌道誤差を同定した」ではなく「熱 FF 後 innovation の周期成分を運用補正」

`--fit-mode`:

| 語 | 何をするか | 身分 |
|----|------------|------|
| **causal** | 周 *n* の残差だけで係数を決める → 周 *n+1* の同じ位相 `φ` に `r̂` を載せる。周 0 は `r̂=0` | 軌道上運用に近い（未来の残差を使わない） |
| **batch** | 全時刻の `r(t)` で一度フィットし、同じ区間の全時刻に `r̂` を載せる | 解析上限。その場の未来サンプルも使うので運用ではない |

因果（causal）= 補正に使う情報が、その瞬間より前に取れている、という意味。

---

## 2. 実装

```text
python src/pat_acquisition/models/sunface_deltaT_bcase_los/run_residual_fourier_pat.py \
  --cases 13 --fit-mode causal
# 解析上限: --fit-mode batch
```

| ファイル | 内容 |
|----------|------|
| `.../residual_fourier.py` | `r` への order=2 Fourier、batch / causal |
| `.../run_residual_fourier_pat.py` | PAT 比較（FF / δb 参考アーム / resid Fourier） |

`b_case` はパイプラインの LOO/insample を固定。Toy-2 の遅い `b` 吸い上げはオフ。δb は比較アームのみ。

出力既定: `results/pat_acquisition/sunface_deltaT_bcase_los_model/pat_residual_fourier/`  
スモーク: `.../pat_residual_fourier_smoke_causal/` と `.../pat_residual_fourier_smoke_batch/`  
いつもの時系列図: ケースフォルダの `pat_acquisition_comparison.png`

---

## 3. スモーク結果（2026-08-13、case13 MY、order=2、非熱込み）

ケース: `13_LTAN06_800km_1213COLD_MY_STTLCT_PROP_HEAT_MY_0p5`  
グラフを見ると、1 周期後の誤差・捕捉時間が減っている。

| アーム | mean tacq [s] | p95 tacq [s] | scan-center mean [µrad] |
|--------|---------------|--------------|-------------------------|
| FF only | 22.7 | 65.4 | 312 |
| FF + 定数 `δb` | 21.4 | 56.0 | 303 |
| FF + resid Fourier **causal** | **12.4** | **39.8** | 230 |
| FF + resid Fourier **batch** | **4.8** | **13.1** | 138 |

熱のみはどれも tacq 0.10 s（床）。定数 `δb` では非熱の AC 床がほぼ残るが、残差 Fourier では下がる。

causal の周ごと（非熱込み `r` ノルム平均）:

| 周 | `r_obs` | `r̂` 適用 | 適用後残差 |
|----|---------|-----------|------------|
| 0 | 330 | 0（初周） | 330 |
| 1 | 346 | 329 | 171 |
| 2 | 261 | 339 | 186 |

初周は効かない。2 周目以降で床が約半分。batch は解析上限。

注意（効きを盛っている／割り引く点）:

- 評価刻み 60 s 全点をフィットに使っている。実運用のコンタクトはもっと疎
- 軌道誤差は `cyclic` → 周 n と n+1 がほぼ同波形
- 失敗点の残差もフィットに入っている（真の QD は成功点だけ）
- `mean_thermal_residual` が悪化して見えるのは、`θ_hat` が軌道 AC を含むため熱真値から離れるから（熱を壊したというより指標の定義）

---

## 4. いきなり全誤差 Fourier vs FF→残差 Fourier

同じ order=2・**causal**・非熱込み。`Fourier(total)` は `θ_hat = Fourier(θ_thermal + e_nonthermal)`（熱 FF なし）。

case13 MY（熱ノルム平均 ~147 µrad）:

| | 全区間 tacq | 周 0 | 周 1 以降 |
|--|-------------|------|-----------|
| FF only | 22.7 s | 22.4 s | 22.8 s |
| Fourier(熱+非熱) いきなり | 19.8 s | **44.3 s** | **7.3 s** |
| FF → Fourier(`r`) | **12.5 s** | **22.4 s** | **7.4 s** |

case16 PY（熱ノルム平均 ~1211 µrad）:

| | 全区間 tacq | 周 0 | 周 1 以降 |
|--|-------------|------|-----------|
| FF only | 22.7 s | 21.4 s | 23.3 s |
| Fourier(熱+非熱) いきなり | **113 s** | **365 s** | 7.8 s |
| FF → Fourier(`r`) | **12.2 s** | **21.4 s** | 7.5 s |

読み:

- **周 1 以降**はほぼ同じ。密サンプル＋同じ mode＋`cyclic` なら、order=2 は「前周の熱+軌道の和」を次周に再生できる
- **周 0（学習前）** は全然違う。いきなり Fourier は無補正。FF→Fourier は熱 FF が初回から効く
- 熱が大きい PY では、いきなり Fourier の初回が実質死ぬ（365 s）

周 1 以降が揃うのは「後段が無駄」ではなく、この sim では前周残差が周期床を覚えきれる、という意味。実運用で崩れやすいのは初回・発熱/面の切替・疎なコンタクト。

---

## 5. 運用上の意味

光通信の初期捕捉は 60 s 連続機会ではなく、**ある軌道・ある相手についてほぼ初回**が多い。前周の同じ位相の残差が無い。

```text
初回: 温度は測れる → a·ΔT + b_case が使える（残差学習不要）
後段 Fourier: 捕捉が成功して r が溜まってから、繰り返す床を次機会へ
```

混ぜて一気に Fourier すると、熱 DC が大きい初回が重い。定数 `δb` だけでは軌道 AC の床は残る。

```text
事前の熱階層 FF（主補正・初回）
＋ 捕捉後の残差周期フィット（床・次周以降）
```

論文で残す主張は「Fourier が非熱専用でより上手」ではなく、**階層 FF があるから初回も生き、そのあと周期床を運用補正できる**。

---

## 6. 先行研究との関係

| | 何をフィットするか | 較正 | 本研究との差 |
|--|-------------------|------|--------------|
| FY-4A/AGRI TMC（GEO） | 観測 LOS の日周期（中身は主に熱） | 星 | 熱込みの周期モデル。GEO の規則的熱が前提 |
| Hu ら | LOS misalignment の Fourier | 星など | 同上。熱と軌道を分けない |
| 旧 `fourier_los`（本リポジトリ） | 熱 LOS 時系列 | Femap 真値で学習 | 熱 FF の候補だったが、温度・発熱につながらないので本線を `a·ΔT+b_case` に移した |
| **本後段** | 熱 FF 後の `r(t)` | 捕捉後残差（QD/FPM 相当） | 同じ「LOS に Fourier」でも **熱を先に剥がした床**。軌道上に POD 真値は不要 |

GEO TMC は「繰り返し＝熱」で星真値がある。LEO 光通信は初回が多く、熱と軌道が同帯域。だから **先に物理 FF、Fourier は innovation 専用**に置いた方が、先行の周期フィットと衝突せず差分が書ける。

---

## 7. 関連

- Adaptive `b` 二層: [`260808_adaptive_two_layer_b_update.md`](260808_adaptive_two_layer_b_update.md)
- ロードマップ: [`260808_pre_paper_bcase_adaptive_roadmap.md`](260808_pre_paper_bcase_adaptive_roadmap.md)
- 軌道誤差前提: [`260718_orbit_prediction_error_assumptions.md`](260718_orbit_prediction_error_assumptions.md)
- 熱の真値 vs 事前モデル: [`260813_thermal_model_mismatch.md`](260813_thermal_model_mismatch.md)
- Hu ら: `google_doc/MD/260711_モデル先行研究`
