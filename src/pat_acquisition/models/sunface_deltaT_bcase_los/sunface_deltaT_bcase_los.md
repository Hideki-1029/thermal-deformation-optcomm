# 階層 sunface ΔT モデル（`sunface_deltaT_bcase_los`）

- 作成: 2026-07-14
- 更新: 2026-07-17（cases 4–6, 8–25 / 21 ケースまで反映）
- 背景: `260714_sunface_compo_handoff.md` までの試行錯誤の結論として実装・検証
- パッケージ: `src/pat_acquisition/models/sunface_deltaT_bcase_los/`
- 結果: `results/pat_acquisition/sunface_deltaT_bcase_los_model/`

---

## 0. 結論（先に読む）

熱ひずみ LOS（支配軸）の主成分は、次の**階層モデル**でケース横断に説明できる。

```text
# Level 1（軌道内・時刻 t）
LOS_dom(t) ≈ b_case + a(sun_face) · ΔT(t)

# Level 2（ケース間・定数）
b_case ≈ b0(sun_face) + c_prop · I_prop + c_pcdu · I_pcdu
```

ここで

- `ΔT(t) = T_sunface_center − T_opposite_center`（計測／シミュレーション温度）
- `sun_face ∈ {MX, MY, PX, PY}`
- `I_prop`, `I_pcdu` ∈ {0,1}（コンポ発熱 ON/OFF）
- `**a`, `b0_*`, `c_prop`, `c_pcdu` はケース横断の固定係数**

生の支配軸はだいたい **100～1000+ µrad**。本モデル後の残りは標準ケースで **数 µrad**、被覆・HOT でも **十数 µrad 以下**。数百 µrad 級の熱バイアスに対し 1～2 桁の低減。

**フィット済みケース集合（現行）:** `--cases 4-6,8-25` → **21 ケース**。  
除外: 01–03・07（MZ 太陽指向など、支配軸モデルの対象外）。  
初回公開フィットは 4–6, 8–21（17 ケース）。22–25 追加後も共有 `a` はほぼ不変、Level-2 も同オーダー。

先行の within-case 拡張（`sunface_compo_los` / `sunface_compo_local_los`）は、取付温度を時系列特徴に入れると共線・低 SNR で係数が壊れる。**コンポ効果は軌道内特徴ではなく、ケース定数 `b` 側に置く**のが正しい分離だった。

### 0.1 本命化の判断（LOS 予測モデルとして）

**支配軸の熱ひずみ LOS 予測としては、本モデルをメインに据えてよい。** 「完成」ではなく、**本命の第一版として十分使える**、という位置づけ。

根拠:

- 時変は共有 `a·ΔT` で床（標準で数 µrad）まで落ちる
- ケース差の DC は Level-2（太陽面 + 発熱 ON/OFF）でだいたい説明できる（LOO `b` RMSE ~数 µrad）
- 21 ケース（4–6, 8–25）でも `a` はほぼ不変、PAT 熱のみでは no → bcase で桁落ち

別扱い・次に足すときに意識する点:

| 対象 | 扱い |
|------|------|
| case22（半電力） | ON/OFF の限界。当面除外 or 後で W 比例 |
| HOT / Black | Level-2 未投入。床や `b` ずれは既知 |
| 非支配軸・非熱込み PAT | 本モデルの外。取得時間の主報告は非熱込み |

論文・運用のメイン LOS（熱ひずみ・支配軸）モデルとして採用してよい。

---

## 1. モデルの形

### 1.1 Level 1 — 軌道内（時変）

支配軸のみを温度で説明する（非支配軸は別扱い／静的寄り）。


| 記号       | 意味                                    |
| -------- | ------------------------------------- |
| `ΔT(t)`  | 太陽面パネル中心 − 反対面パネル中心 [°C]              |
| `a(sun)` | 感度 [µrad/°C]。**太陽面ごとに 1 値**（符号は面で変わる） |
| `b_case` | そのケースの DC バイアス [µrad]（軌道内では定数）        |


物理イメージ: 面間温度差が構造の「曲げ／反り」を駆動し、LOS 支配軸にほぼ線形に載る。切片 `b` は ΔT ゼロ近傍でも残るオフセット（取付・内部発熱の DC 残差など）。

### 1.2 Level 2 — ケース間（`b` の説明）


| 記号                 | 意味                                       |
| ------------------ | ---------------------------------------- |
| `b0(sun)`          | STT+LCT のみ（PROP/PCDU OFF）のときのベースバイアス。面ごと |
| `I_prop`           | PROP 発熱 ON なら 1                          |
| `I_pcdu`           | PCDU 発熱 ON なら 1                          |
| `c_prop`, `c_pcdu` | 各発熱が `b` に足す**残差 DC**（∆T に入りきらない分）[µrad] |


実装の既定: 発熱フラグが効くのは **MY / PY のみ**（PROP/PCDU 取付面）。MX/PX では `I_`* を設計行列上ゼロにする（実測でも PX の発熱モード差は数 µrad 程度）。

`ALL_HEAT` は `I_prop=I_pcdu=1`。効果はほぼ足し算（MY/PY のスクリーニングで確認済み）。

### 1.3 ケースごとに「測る／知る」もの vs 固定値


| 入力（ケース依存）        | 固定パラメータ（横断）            |
| ---------------- | ---------------------- |
| `ΔT(t)` 時系列      | `a(MX/MY/PX/PY)` × 4   |
| 太陽面              | `b0(MX/MY/PX/PY)` × 4  |
| PROP/PCDU ON/OFF | `c_prop`, `c_pcdu` × 2 |


合計 **10 個のスカラー係数**で、複数太陽面・発熱モードの支配軸 LOS をまとめて記述する。

---

## 2. 係数の求め方

### Step A — ケースごと（Level 1）

各ケースの先頭 1 軌道を train に使い、

```text
LOS_dom ≈ b + a · ΔT
```

を Ridge（`λ≈1e-3`、実質ほぼ OLS）で当て、切片を `**b_emp**`、傾きを `**a_emp**` とする。

### Step B — ケース横断（Level 2）

全ケースの `(sun, I_prop, I_pcdu, b_emp)` を 1 行にして OLS:

```text
b_emp ≈ Σ_face b0_face · 1_face + c_prop · I_prop_eff + c_pcdu · I_pcdu_eff
```

グローバル切片は置かない（面ダミー `b0_*` が切片役）。

### Step C — 共有 `a`

面ごとに `a_emp` の中央値を `**a_shared(sun)**` とする。予測時は

```text
LOS_dom_hat(t) = b_pred(sun, I_prop, I_pcdu) + a_shared(sun) · ΔT(t)
```

Leave-one-case-out で Level-2 だけ再フィットし、`b_pred_loo` も評価する。

### 2.1 どのケースで学習するか（実行時）

| 段階 | 何を学習するか | データ分割 |
|------|----------------|------------|
| Level 1 | 各ケース独立に `(a_emp, b_emp)` | **そのケースの先頭 1 軌道**（`train_orbits=1`） |
| Level 2 | 全指定ケースの `b_emp` を 1 行ずつ → 1 セットの `b0_*/c_*` | **ケース横断**（時系列分割なし） |
| `a_shared` | 面ごとの `a_emp` 中央値 | 同上の指定ケース集合 |

- **`--cases` で渡した集合全体**が Level-2 の学習集合になる（毎回その集合で 1 セットの係数を出す）。
- `validate.py` は `--cases` 必須。`run_pat.py` は省略時 lightweight 内の supported 全ケース。
- **部分集合だけ**（例: `--cases 22-25`）で回すと、Level-2 係数も PAT もその 4 ケース用になる。論文・横断比較は常に同じ `--cases 4-6,8-25` を明示する。

---

## 3. フィット結果（cases 4–6, 8–25 / 21 ケース）

実行:

```powershell
python "src/pat_acquisition/models/sunface_deltaT_bcase_los/validate.py" --cases 4-6,8-25
```

対象: 04–06, 08–25（計 21）。**01–03・07（MZ）は含めない。**  
初回（4–6, 8–21）との差分は §3.7。

### 3.1 共有 `a` [µrad/°C]


| sun | a_shared |
| --- | -------- |
| MX  | +30.6    |
| MY  | +28.6    |
| PX  | −28.1    |
| PY  | −28.7    |


絶対値はおおむね **28–31 µrad/°C**。符号は太陽面（支配軸の向き）で決まる。22–25 追加後もほぼ不変。

### 3.2 Level-2 係数 [µrad]


| feature | coef（21 ケース） |
| ------- | ---------------- |
| b0_MX   | +15.7            |
| b0_MY   | +2.8             |
| b0_PX   | −12              |
| b0_PY   | −24              |
| c_prop  | **−22.9**        |
| c_pcdu  | **−10.2**        |


解釈の要点:

- 面ごとのベース `b0` は数十 µrad オーダーで、太陽面によって符号・大きさが違う。
- PROP/PCDU はどちらも **`b` をより負側へ**ずらす（同符号）。MY では概ね  
  `Δb_PROP≈−23`, `Δb_PCDU≈−10`, 両方≈−33 → ALL_HEAT と整合。
- 面加熱の主効果の多くはすでに **`a·ΔT` に吸収**される。Level-2 の `c_*` は「ΔT に入りきらない DC 残差」。

### 3.3 `b_emp` vs `b_pred`（要約）


| 指標                 | 値（21 ケース）   |
| ------------------ | ------------- |
| in-sample `b` RMSE | **3.09 µrad** |
| LOO `b` RMSE       | **3.80 µrad** |
| 最大 \|LOO 残差\|   | **13.2 µrad**（case22 PROP 12.5 W） |


発熱スクリーニング（MY: 15/13/14/04、PY: 16/18/19/08）は Level-2 の足し算でほぼ再現。MX は ALL≈STTLCT≈+PROP/+PCDU（`b≈+15–17`；23/24 で確認）。PX は発熱フラグ無効のためすべて `b0_PX` 近傍。

詳細表: `results/pat_acquisition/sunface_deltaT_bcase_los_model/bcase_case_table_display.csv`

### 3.4 支配軸 LOS 残差（test RMSE）

標準の 1213COLD + 既定被覆（`b_pred` + `a_shared`）:


| 面       | 典型 test RMSE（階層予測） |
| ------- | ------------------ |
| MY 発熱系列 | ~6.5–7 µrad        |
| PY      | ~3 µrad            |
| MX      | ~3–4 µrad          |
| PX      | ~5–6 µrad          |


この **~数 µrad** は、主に Level-1 の時変残差の床（`b_emp + a_emp·ΔT` の oracle と同程度）。Level-2 で `b` を置き換えても、標準ケースではほぼ床を維持する。

### 3.5 生スケールとの比較（オーダー感）


| case              | 生 RMS / peak（支配軸） | モデル後 test RMSE |
| ----------------- | ----------------- | -------------- |
| 04 MY ALL         | 160 / 257         | 6.8            |
| 15 MY STTLCT      | 253 / 358         | 6.7            |
| 08 PY ALL         | 1250 / 1420       | 3.9            |
| 09 MX ALL         | 667 / 838         | 3.0            |
| 11 MY Black       | 265 / 531         | 13.1           |
| 10 MY HOT         | 161 / 163（ほぼ DC） | 1.3（`b` ずれ小）  |
| 22 MY ALL PROP12.5 | 204 / 294        | 14.8（Level-2 `b` ずれ） |
| 23 MX +PROP       | 682 / 848         | 4.2            |
| 24 MX +PCDU       | 709 / 878         | 3.6            |
| 25 MY LTAN18      | 151 / 152（ほぼ DC） | 0.9            |


「ゼロ誤差」ではないが、**数百 µrad 級の熱ひずみ LOS を固定係数 + ΔT + 太陽面 + 発熱フラグで 1～2 桁落とせる**、というのが本モデルの実務的意義。

数値表: `bcase_raw_vs_model_scale_display.csv`  
図: `bcase_raw_vs_model_rmse.png`（P5）

### 3.6 新ケース 22–25 の要点


| case | 何を試したか | 判定 |
|------|-------------|------|
| **22** PROP 12.5 W | 電力連続 | Level-1 は健在（`a≈28.6`, oracle ~7）。`b_emp≈−19` だが ON/OFF Level-2 は ALL 扱い（`b_pred≈−30`）→ LOO 残差 ~13 µrad。**0/1 の限界** |
| **23/24** MX +PROP / +PCDU | MX 発熱スクリーニング | `a≈30.6`, `b≈15–17`（09/17 と同系）。MX で `I_*` 無効の判断を補強 |
| **25** LTAN18 / 693 km SENTINEL | 別軌道・ほぼ全日照 | Level-1 ほぼ完璧（oracle ~0.1）。`b_emp≈−32` は MY ALL と同族。時変振幅が小さく PAT の熱改善幅は相対的に小さい |

**データ注意（2026-07-16）:** case25 の `case_matrix` パス列が case04 を指しており、lightweight の LOS が一時汚染された。パス列を廃止し `case_id` 規則解決に統一済み。古い PAT 図（タイトル `a≈46` 等）は無効。

### 3.7 初回フィット（4–6, 8–21）との比較

| 係数 | 17 ケース | 21 ケース |
|------|----------|----------|
| `a` 各面 | ±28–31 | ほぼ同じ |
| `b0_MY` | +2.8 | +2.8 |
| `c_prop` / `c_pcdu` | −23.8 / −11.1 | −22.9 / −10.2 |
| LOO `b` RMSE | 2.31 µrad | 3.80 µrad（主因は case22） |

共有 `a` と Level-2 の芯は維持。LOO 悪化は半電力ケースが ON/OFF モデルに載らないことが主因。

### 3.8 論文用プロット（ICSO §5）

`validate.py` 実行時に自動生成（`--no-plots` で省略可）:


| ID | ファイル | 中身 |
| ---- | -------- | ---- |
| P3a | `bcase_a_emp_by_sunface.png` | 面ごとの `a_emp` と `a_shared` |
| P3b | `bcase_b_emp_vs_b_pred.png` | `b_emp` vs `b_pred`（in-sample / LOO） |
| P2 | `timeseries/case*_bcase_true_vs_pred.png` | 階層予測の true vs pred（`--plot-cases`） |
| P5 | `bcase_raw_vs_model_rmse.png` | 生 RMS → モデル RMSE |

---

## 3.9 どの結果を重点的に見るか

優先順:

1. **モデル妥当性** — `bcase_a_emp_by_sunface.png` / `bcase_level2_coefficients_display.csv` / `bcase_b_emp_vs_b_pred.png` / `bcase_case_table_display.csv`  
   合格目安: LOO `b` RMSE ~数 µrad、発熱スクリーニングが足し算で再現。
2. **時変予測の床** — `bcase_los_metrics_display.csv` の **`b_pred_loo_a_shared` test RMSE**（運用に近い列）と `timeseries/*`。  
   `oracle_b_emp_a_emp` は上限、`b_pred_insample_*` は楽観側。
3. **オーダー感** — `bcase_raw_vs_model_rmse.png`
4. **PAT** — `pat/summary.csv` と代表ケースの `pat/*/pat_acquisition_comparison.png`  
   熱のみ: `bcase` vs `no`。主報告は非熱込み: `bcase_with_nonthermal` vs `thermal_plus_nonthermal_no_correction`。

論文用の最小セット: **P3b + P5 + LOO 列 + pat/summary（非熱込み）**。

---

## 4. うまくいかない／別扱いのケース


| ケース                 | 現象                                           | 含意                                               |
| ------------------- | -------------------------------------------- | ------------------------------------------------ |
| **11 Black**        | oracle でも支配軸 RMSE ~13 µrad                   | 被覆が時変残差の床を上げる。`a`/`b` の枠は同じだが、残りが大きい             |
| **10 HOT**          | 時変はほぼ完璧、`b` が COLD 用 Level-2 から数 µrad ずれ | 熱環境（HOT/COLD）は現状 Level-2 に未投入。必要なら `b0` や別フラグで拡張 |
| **22 PROP 12.5 W**  | Level-1 OK、Level-2 LOO ~13 µrad               | ON/OFF では半電力を説明できない → W 比例拡張の候補                     |
| **25 全日照**         | モデルは合うが PAT 熱改善幅は小さい                         | 生誤差自体がほぼ DC・振幅小。非熱込みでは非熱が支配                      |
| **被覆 alodine (12)** | `b` は ALL に近い、RMSE は低い                       | 標準系に近い                                           |
| **PX 発熱差**          | Level-2 では意図的に無視                             | 実測でも数 µrad。当面 MY/PY のみで十分                        |


---

## 5. 先行モデルとの位置づけ


| パッケージ                          | 役割                            | 結果                     |
| ------------------------------ | ----------------------------- | ---------------------- |
| `sunface_los`                  | 3 特徴（共線気味）の初期版                | アーカイブ                  |
| `sunface_deltaT_los`           | **核**: `b + a·ΔT` within-case | `a` の安定性を確立            |
| `sunface_compo_los`            | ΔT + `(T_attach−T_ref)`       | 共線で失敗寄り                |
| `sunface_compo_local_los`      | ΔT + 局所差                      | `b` 振れは減るが係数不安定（ほぼ DC） |
| `**sunface_deltaT_bcase_los`** | **本命**: 共有 `a` + Level-2 `b`  | 本ノート                   |


失敗から得た設計原則:

1. 軌道内の時変は **ΔT 一本**で足りる（`a` は面ごと固定でよい）。
2. コンポ発熱の残りは **ケース定数 `b`** に出す。within-case 時系列に足さない。
3. `b` のケース間差は、まず **太陽面 + 発熱 ON/OFF** の線形モデルで足りる。

## 6. 先行研究 JANUS に対する本モデルの差分

JANUS は光学機器で `LoS≈K·ΔT` が使えることを示した（勾配ゼロで LoS≈0 となるよう **原点通過の比例**が自然）。本研究はそれを衛星バス相対 LOS に移し、主説明変数が太陽面−反対面 ΔT であること、および ΔT に入りきらない DC を発熱 ON/OFF で階層的に説明できることを示した。

新規性の置き方（注意）:

| 主張 | 新規性 |
|------|--------|
| `LOS = a·ΔT`（比例） | JANUS そのもの |
| `LOS = b + a·ΔT`（切片付き一次） | 統計・校正では普通。静的バイアス + 温度感度は pointing でもよくある |
| 衛星バス **STT–LCT 相対 LOS**で、主説明変数が**太陽面−反対面 ΔT**、かつ `a` がケース横断で共有可能 | 差分の本体 |
| さらに **`b` を発熱 ON/OFF でケース間モデル化**し、固定少数係数で複数モードを説明 | JANUS 型には無い。本モデル固有の寄与 |

✗「切片付き ΔT モデルは世界初」  
○「JANUS 型の ΔT 一次関係が衛星バス相対 LOS でも成り立ち、感度 `a` はケース横断で共有可能。さらに ΔT に入りきらない DC をコンポ発熱で階層的に説明できる」

---

## 7. Q&A（解釈メモ）

### Q1. `a` はたまたま全ケース同じ値に収束しているのか？

ほぼその理解でよい。

- フィット時に全ケース共通 `a` を**強制してはいない**
- 各ケースで独立に `LOS ≈ b + a·ΔT` → ケースごとの `a_emp`
- それが**太陽面ごとにほぼ同じ値に揃った**（例: MY で 28.3–28.7）
- だから予測では中央値を `a_shared` として使い回せる

「物理的に必ず1つ」と証明したわけではなく、**この衛星・この LOS 定義・このケース群では感度が安定だったので共有してよい**、という実証。ケースを増やして確実性を試す余地はあるが、LOS 予測モデルとしては当面これで十分強い。

### Q2. `b + a·ΔT` や階層 `b` の式自体に先行例は出なさそうか？（新規性）

**式の形だけを新規と言うのは危ない。** 詳細は §6。芯は「式に `b` を書いたこと」ではなく、「どの ΔT か・バス相対 LOS・`a` 共有の実証・発熱による `b` 階層」。

### Q3. PROP/PCDU は対向面なのに、なぜ `b` では和（同符号）で効くのか？

**差で効く主効果は `a·ΔT` 側に入っている。`b` に残るのはパネル中心 ΔT では拾いきれない残差で、それが同符号だった、という分離。**

MY 発熱系列の軌道平均（`a≈28.6`）:

| case | 発熱 | mean ΔT | mean LOS | ≈`a·ΔT` | ≈残り（≈`b`） |
|------|------|---------|----------|---------|---------------|
| 15 | STTLCT | 7.4°C | 215 | 211 | **+4** |
| 13 | +PROP(PY) | **3.7**↓ | 85 | 106 | **−22** |
| 14 | +PCDU(MY) | **8.0**↑ | 222 | 229 | **−7** |
| 04 | ALL | 4.4 | 92 | 125 | **−33** |

位置関係どおり:

- PCDU（MY）→ 太陽面が温まる → **ΔT↑** → `a·ΔT` が LOS を正側へ
- PROP（PY）→ 反対面が温まる → **ΔT↓** → `a·ΔT` が LOS を負側へ

切片は概ね `b ≈ mean(LOS − a·ΔT)`。ΔT に線形射影したあとの DC だけが残り、PROP/PCDU ともより負だったので Level-2 では同符号の足し算。ALL ≈ PROP + PCDU もこの残差 DC 同士の和。

### Q4. 係数は物理的に説明できるか？回帰でないとわからない値か？

**オーダーと符号は物理で語れる。精密な数値は回帰／FEM でないと出ない。**

| 係数 | 物理で言えること | 数値の出自 |
|------|------------------|------------|
| `a` (~±28–30 µrad/°C) | CTE×幾何レバーの感度。符号は太陽面／支配軸で決まる。JANUS ~7 µrad/°C より大きいのは衛星尺度として qualitatively 整合 | 閉形式だけでは ±28.6 までは出にくい |
| `b0(sun)` | 太陽方位ごとの基準熱形状での相対オフセット | ほぼデータ／FEM |
| `c_prop`, `c_pcdu` | ΔT に入りきらない局所発熱の DC。同符号は Q3 の分離の帰結 | 大きさは回帰（または詳細局所 FEM） |

Level-2 の `b0_*`, `c_*` 自体は、各ケースの `b_emp` を目的変数にした**ケース間の単純 OLS**（1ケース=1行、現行 21 ケース）で得ている。`a_shared` は Level-2 の出力ではなく、面ごとの `a_emp` 中央値。

### Q5. in-sample と LOO の違いは？

回帰・機械学習でよくある評価の分け方。本モデルでは **Level-2 の `b` 予測**に使う。

| 用語 | 意味 | 本モデルでのやり方 |
|------|------|-------------------|
| **in-sample** | 学習に使ったデータで当てはまりを見る（training score）。楽観的になりやすい | 全ケースで Level-2 をフィット → 同じケースの `b` を予測（`b_pred_insample`） |
| **LOO**（leave-one-out） | 評価したい点を学習から外す。未知データでの汎化の近似 | 注目ケースを除いて Level-2 をフィット → そのケースの `b` を予測（`b_pred_loo`） |

- 兄弟手法: **k-fold 交差検証**（データを k 分割して持ち回り）。LOO は「1 点ずつ外す」極限に近い。
- ここでは 1 ケース＝1 行なので、時系列の train/test ではなく **ケース単位の LOO**。
- LOO するのは **`b`（Level-2）だけ**。`a_shared` は全ケースの `a_emp` 中央値のまま（完全な入れ子 CV ではない簡略版）。
- **見るべきは LOO。** in-sample が良くても LOO が悪いと、係数が特定ケースに寄りすぎているサイン（例: case22）。
- PAT 既定 `--b-mode loo` もこの LOO の `b_pred` を使う。

---

## 8. 再現手順・成果物

```powershell
# 前提: lightweight_dataset 構築済み（LOS は results/femap_deformation/{case_id}/los_angles.csv）
python scripts/build_lightweight_dataset.py

python "src/pat_acquisition/models/sunface_deltaT_bcase_los/validate.py" --cases 4-6,8-25
# 発熱フラグを全太陽面に広げる場合:
python "src/pat_acquisition/models/sunface_deltaT_bcase_los/validate.py" --cases 4-6,8-25 --heat-faces all
# 時系列図のケース指定例:
python "src/pat_acquisition/models/sunface_deltaT_bcase_los/validate.py" --cases 4-6,8-25 --plot-cases 4,8,15,22,25
```

出力（`results/pat_acquisition/sunface_deltaT_bcase_los_model/`）:


| ファイル                            | 内容                                 |
| ------------------------------- | ---------------------------------- |
| `bcase_a_shared.csv`            | 面ごとの共有 `a`                         |
| `bcase_level2_coefficients.csv` | `b0_*`, `c_prop`, `c_pcdu`         |
| `bcase_case_table.csv`          | `b_emp` / `b_pred` / LOO / `a_emp` |
| `bcase_los_metrics.csv`         | oracle / 階層予測の支配軸 RMSE             |
| `bcase_raw_vs_model_scale.csv`  | 生 RMS/peak vs 階層 test RMSE        |
| `bcase_a_emp_by_sunface.png`    | P3: `a` 横断安定性                      |
| `bcase_b_emp_vs_b_pred.png`     | P3: Level-2 `b` 当てはまり              |
| `bcase_raw_vs_model_rmse.png`   | P5: オーダー感                          |
| `timeseries/*_bcase_true_vs_pred.png` | P2: 階層予測時系列                  |
| `pat/summary.csv`               | PAT: no/static/bcase/truth 比較      |
| `pat/pat_model_comparison.png`  | P4: 捕捉時間の横断棒グラフ               |
| `*_display.csv`                 | 閲覧用（有効数字 3 桁）                      |


実装の入口: `src/pat_acquisition/README.md`（Sunface ΔT + case bias 節）。

---

## 9. 今後の拡張候補（メモ）

優先度は低いが、必要になったら:

- Level-2 に **HOT/COLD** や被覆フラグを追加（case10 / case11 向け）
- `I_prop`/`I_pcdu` を 0/1 ではなく **電力 [W] 比例**にする（case22）
- 軌道平均の局所温度を Level-2 特徴にする（ON/OFF の連続版）
- 別 LTAN / β / 高度をさらに増やして `a` 共有のストレステスト

現時点の本命は、**固定 10 係数 + ΔT(t) + 太陽面 + 発熱フラグ**のまま十分強い（半電力・HOT/被覆は別扱い）。

---

## 10. PAT 接続（粗捕捉評価）

```powershell
python "src/pat_acquisition/models/sunface_deltaT_bcase_los/run_pat.py" --cases 4-6,8-25 --b-mode loo
```

- 既定: Level-2 `b` は **LOO**（`--b-mode loo`）。支配軸は `b_pred + a_shared·ΔT`、非支配軸は train 軌道の静的平均。
- 比較アーム: `no` / `static` / `bcase` / `thermal truth`（＋ nonthermal 付き 2 本）
- 出力: `results/pat_acquisition/sunface_deltaT_bcase_los_model/pat/`
- Level-2 の学習集合は **`--cases` と同じ**（PAT も validate と同じ集合で回す）。

### 10.1 要約（21 ケース平均・熱のみ）

| model | mean tacq [s] | success | mean thermal residual [µrad] |
|-------|---------------|---------|------------------------------|
| no_correction | **125** | 0.96 | 667 |
| static_bias | **4.8** | 0.99 | 108 |
| **bcase (LOO)** | **0.12** | **1.00** | **8.8** |
| thermal truth | 0.10 | 1.00 | 0 |

大 LOS / 新ケース例（mean tacq [s]、熱のみ）:

| case | no | static | bcase | truth |
|------|-----|--------|-------|-------|
| 08 PY ALL | ~384 | ~3 | 0.10 | 0.10 |
| 09 MX ALL | ~138 | ~8 | 0.13 | 0.10 |
| 22 MY PROP12.5 | 9.6 | 3.4 | 0.12 | 0.10 |
| 23 MX +PROP | 141 | 6.8 | 0.13 | 0.10 |
| 25 MY LTAN18 | 5.8 | 0.10 | 0.10 | 0.10 |

case25 はほぼ全日照で熱 LOS が ~151 µrad DC に近く、no でも取得は短い。bcase は residual ~3 µrad まで落とすが、**取得時間の改善幅は小さい**（すでに短い）。非熱込みでは非熱 ~290 µrad が支配し、bcase の有無で取得時間は ~19 s 前後と同程度。

図: `pat/pat_model_comparison.png`（P4）。熱成分だけ見ると bcase は truth 上界にほぼ張り付く。