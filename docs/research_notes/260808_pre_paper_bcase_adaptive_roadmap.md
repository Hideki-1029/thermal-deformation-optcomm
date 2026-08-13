# 論文執筆前ロードマップ: `b_case` 進化と Adaptive モデル

- 作成: 2026-08-08
- 目的: 本格的な論文執筆に入る前に進める技術課題を整理する
- 主対象:
  1. `b_case`（Level-2）のさらなる進化
  2. Adaptive モデルの構築
- 前提: 現時点の定量主結果は物理ベース feedforward（`a ΔT + b_case`）。Adaptive は未実装・未評価
- **Adaptive / `b` 二層更新の確定方針:** [`260808_adaptive_two_layer_b_update.md`](260808_adaptive_two_layer_b_update.md)（本ノート §2.4 は要約。詳細はそちらを正とする）

---

## 0. いまの立ち位置（1段落）

```text
LOS_dom(t) ≈ b_case + a(sun_face) · ΔT(t)
b_case    ≈ b0(sun_face) + c_prop · I_prop + c_pcdu · I_pcdu
```

- `a` はケース横断で比較的安定 → 事前固定候補
- `b_case` は発熱・被覆・軌道/熱履歴で変わりうる → 運用テーブルまたは軌道上更新候補
- Adaptive は速い `δb` + 条件付きで遅い `b_case` 吸い上げ（詳細は [`260808_adaptive_two_layer_b_update.md`](260808_adaptive_two_layer_b_update.md)）
- 論文の主軸は当面 feedforward のまま維持し、本ノートの2テーマを「執筆前に厚みを足す作業」とする

---

## 1. テーマA: `b_case` のさらなる進化

### 1.1 なぜまだ進化が必要か

| 現状の限界 | 出典・根拠 |
|---|---|
| `c_prop` / `c_pcdu` が太陽面非依存の共通係数 | 光RG FB・`260722` §B |
| ON/OFF フラグであり、連続電力・途中ON/OFF過渡を未評価 | `260722` §C, `260802` Limitations |
| HOT/COLD・被覆の Level-2 一般化が未完 | `260721`, `260802` |
| 局所温度の軌道平均などを Level-2 入力に入れる案は設計止まり | `260714_sunface_compo_handoff` |

### 1.2 進める候補（優先度イメージ）

#### A1. 面依存・交互作用チェック（最優先候補）

現行:

```text
b_case ≈ b0(sun) + c_prop I_prop + c_pcdu I_pcdu
```

比較案（`260722` より）:

| モデル | 式 | 狙い |
|---|---|---|
| 現行 | `b0(sun)+c_prop I+c_pcdu I` | 最小モデル |
| heat faces 限定 | MY/PY だけ発熱係数有効 | 現行実装の明示 |
| sun×heat | `c_prop(sun)`, `c_pcdu(sun)` | 面依存の必要性 |
| axis×heat | 支配軸ごとに係数 | データ不足を抑えた交互作用 |
| power比例 | `c · P`（連続電力） | ON/OFF からの拡張 |

判断基準:

- LOO `b` RMSE が改善するか
- 係数の符号・大きさが物理的か
- データ数に対して過剰自由度でないか
- PAT で static / bcase の順位が崩れないか

#### A2. コンポ ON/OFF 過渡

- 現状は「十分定常化した発熱状態」の近似
- 瞬時に `b_case` が切り替わるわけではない
- 追加解析案:
  - TD で軌道途中 PROP/PCDU ON を1ケース
  - `b_case(t)` 一次遅れ
  - `I_prop` の代わりに PROP 近傍温度の低周波成分を Level-2 入力にする
  - 過渡残差を Adaptive 層で吸収する（→ テーマBと接続）

#### A3. Level-2 入力の拡張（設計メモ段階）

`260714` の候補:

1. 太陽方位 + PROP/PCDU の 0/1 または W
2. 局所温度の**軌道平均**（時系列ではない）
3. 軌道環境（COLD/HOT）
4. 被覆（b には弱そう、要再確認）

実装するならモデルごとにフォルダ分離（例: `sunface_deltaT_bcase_los` の派生）。

### 1.3 `b_case` 作業の出口条件（執筆前）

最低限そろえたいもの:

- [ ] A1 の比較表（採用/不採用の理由付き）
- [ ] A2 を「解析1ケース」か「今後課題」かに決断
- [ ] 論文本文で使う最終の Level-2 式を1本に固定
- [ ] Limitations に「入れなかった拡張」を明記できる状態にする

---

## 2. テーマB: Adaptive モデルの構築

### 2.1 過去 research note での議論マップ

Adaptive は「構想・動機・更新対象の絞り込み」までは何度も出てくるが、**推定器の実装・定量評価は未着手**。

| 日付・ノート | 何が書かれているか | 実装度 |
|---|---|---|
| `MD/20260525_labseminar_slide` | FF + Adaptive の二層構想。観測残差でモデル更新。熱相関の低周波だけ取り込む、と明記。比較軸に FF+Adaptive を置いている | 構想スライド |
| `MD/ICSO_abstract_submitted` / `google_doc_from260415_...` | アブスト本文に二層補正（physics FF + on-orbit adaptive） | アブストのみ |
| `google_doc/MD/260704_軽量モデル構築`, `memo_in_repository` | 「最後に adaptive を足す。最初に入れると評価軸が混ざるので後回し」 | ToDo |
| `google_doc/MD/260712_LCT配置変更`, `260622_今後の方針` | 軌道上適応更新の二層構造に一言触れる | 構想 |
| **`google_doc/MD/260717_Adaptiveモデル`** | **Adaptive 専用メモ（最重要）**。`a` は事前推定で足りる可能性、`b_case`（と遅いモデル誤差）をオンライン推定する価値、と明記 | 方針メモ（OCR 1p） |
| `260715_icso_paper_outline` | adaptive は第2層の枠。実装は薄くてよい | 予稿方針 |
| `260721_rg_slide_retrospective_and_paper_narrative` §2.10 | Adaptive は結果から必要性を導く。`a` 固定 / `b_case` 更新。残差を全部熱に吸わせない制約が必要 | ナラティブ |
| `260722_optcomm_rg_feedback_response_plan` | 優先度Cに「捕捉後残差から `b_case` を更新する adaptive toy model」。ICSO前は「なぜ必要か」まで | 今後課題 |
| `260802_update_main_typ_to_260721_slides` §1.3, §2.11.3 | Adaptive を主たる定量結果にしない。更新式詳細は今後。帰結は設計指針まで | 執筆方針 |
| `google_doc/MD/260720_光RG発表` | JANUS 側は `b_case` 相当を星校正でキャリブしている可能性、要確認 | 文献メモ |

結論:

- 議論の核はすでに揃っている: **更新するのは主に `b_case`（と未モデル化の遅い DC）であり、`a` ではない**
- 足りないのは **toy model 実装・数値実験・更新制約の具体化**

### 2.2 `260717_Adaptiveモデル` で確定している方針（要約）

出典: `docs/research_notes/google_doc/MD/260717_Adaptiveモデル/content.md`

1. 現行モデルの係数を、運用でどう決めるかが記述不足
2. `a`: 時変感度。ケース間であまり変わらない → 試験等の事前推定で十分な可能性が高い
3. `b_case`: バイアス。ケース間で大きく変わり、消費電力等で最適係数も変わりうる
4. したがって adaptive にオンライン/事後推定する価値があるのは **`b_case` と遅いモデル誤差**

### 2.3 後続ノートで追加された制約（重要）

`260721` / `260802` で強まった注意点:

- 捕捉後残差をすべて熱 DC として吸収すると、軌道予測誤差・アライメント誤差を誤学習しうる
- 熱 LOS と軌道予測誤差は同じ軌道周期帯を持ちうる → 単純な低周波抽出では分離できない
- 更新には制約が必要:
  - 同一運用モードの複数パス平均
  - 軌道誤差の別状態推定（または事前値）
  - 更新量の制約（ゲイン制限）

### 2.4 Adaptive の確定方針（要約）

**正本:** [`260808_adaptive_two_layer_b_update.md`](260808_adaptive_two_layer_b_update.md)

以下は要約。二層更新（`δb` → 条件付き `b_case`）の式・ゲート・新規性の置き場は正本を見ること。

#### 役割分担（最重要）

```text
Feedforward (a·ΔT + b_case_prior)
  → 今この瞬間の初期捕捉を救う
  → 光が QD/CCD に当たる前でも使える唯一の事前情報

Adaptive (δb[mode] の更新)
  → 今この瞬間の初期捕捉を救う仕組みではない
  → 一度リンクが取れたあと、同じモードの次パスを楽にする仕組み
  → より良い b で、次パスの初期捕捉時間をさらに下げる
```

初期捕捉の前半は相手光が QD/CCD に当たりにくいため、Adaptive 用の光観測はほぼ取れない。これは欠点ではなく、**FF が必要な理由そのもの**であり、Adaptive を「成功パスごとの疎な事後更新」と位置づける根拠でもある。

#### 観測量

光通信端末で現実的な候補:

| 観測量 | 位置づけ | 備考 |
|---|---|---|
| QD / FPM スポットオフセット | **主観測** | 捕捉成立〜精追尾開始直後の pointing residual |
| Rx パワー / ファイバ結合 | 補助 | 主更新には使わない（ゲート・参考指標） |
| 広FOV捕捉カメラ | 端末次第 | 今の研究モデルにはほぼ無い。あってもスキャン前の常時観測にはならない |
| STT のみの LOS | 使わない（主観測として） | 五十里先生指摘どおり軌道誤差と分離困難。光通信固有の強みも薄い |

追加の「魔法センサ」は想定しない。本命は QD/FPM residual。

#### 何を更新するか（読み方）

捕捉後に見える残差は、熱だけの `b_case` ではない。

```text
r = θ_obs − θ_ff
  ≈ (b_true − b_case_prior) + e_orbit + e_align + e_other − δb_hat
```

したがって:

- 正直な更新対象は **`δb`（次パスの scan center に載せる経験的 DC）**
- それを Level-2 が説明しきれない遅い成分の穴埋めとして使う
- 「単一 LOS 観測で熱と軌道予測誤差を分離する」とは主張しない（五十里先生指摘を正面から受ける）
- Adaptive の目的は熱成分の同定ではなく、**次の粗捕捉の探索コスト低減**

#### モード制約つき更新（採用）

`b_case` 自体が運用モード依存なので、全残差で1個の `δb` を動かさない。

```text
mode ≈ (sun_face, I_prop, I_pcdu)

θ_ff = b_case_prior(mode) + a(sun_face)·ΔT(t) + δb[mode]

捕捉成功後:
  r = θ_obs − θ_ff
  δb[mode] ← δb[mode] + γ · r     # そのモードの箱だけ更新
```

なぜモード別か:

1. MY+PROP の残差で MX の補正を壊さない
2. 非熱誤差が混ざっても、モードをまたいだ変なグローバルバイアスになりにくい
3. 同じモードの複数パス平均で、「その運用状態で繰り返し出る DC」に寄せられる

追加の制約（誤学習抑制）:

- `a` は固定（動かさない）
- ゲイン `γ` は小さく、または複数パス平均してから投入
- 軌道誤差の事前が大きいときは更新を弱める / 止める（入れられるなら）

#### パス間のストーリー（論文でもこの因果で書く）

```text
Pass n:
  FF で初期捕捉 →（運良く）リンク確立
  → QD/FPM residual から δb[mode] を更新

Pass n+1（同じ mode）:
  θ_ff' = b_case_prior + a·ΔT + δb[mode]
  → より良い scan center で初期捕捉時間がさらに下がる
```

評価で見るべきなのも「同一パス内の瞬間改善」ではなく、**パスをまたいだ捕捉時間・scan area の改善**である。

### 2.5 Adaptive で最初に作るもの（提案）

目標は「論文の第2層として最低限動く toy model」。飛行実証は不要。  
方針は §2.4 に固定済み。以下は実装手順。

#### B1. 問題設定を固定する

```text
観測: 捕捉後の指向残差（QD/FPM 相当の簡易残差）
既知/事前固定: a(sun_face), ΔT(t), mode=(sun_face, I_prop, I_pcdu)
更新対象: δb[mode]
非更新: a
効くタイミング: 次パス以降の初期捕捉（同一 mode）
```

#### B2. 最小更新式（採用案）

**採用: モード別テーブル更新（§2.4）**

```text
δb[mode] ← δb[mode] + γ · (θ_obs − θ_ff)
θ_ff = b_case_prior(mode) + a · ΔT + δb[mode]
```

補助案（必要なら後から）:

- 一次遅れ / 低通: 過渡 ON/OFF や遅いドリフト向け（テーマA2と接続）
- グローバル単一 `δb`: ベースライン比較用。本線にはしない

#### B3. 評価シナリオ（数値実験）

最低限の比較軸（ラボセミ構想と整合）:

1. no correction
2. static
3. FF only（現行 hierarchical）
4. FF + Adaptive（mode-wise `δb`）

見る量:

- **次パス以降**の捕捉成功率 / 捕捉時間 / scan area（同一 mode）
- `δb[mode]` の収束
- 非熱誤差を混ぜたときの誤学習の有無（重要）

#### B4. Adaptive 作業の出口条件（執筆前）

- [ ] 「今の捕捉ではなく次パスを楽にする」という位置づけで図 or 文章が書ける
- [ ] 更新対象が mode-wise `δb` であることの数値デモ
- [ ] `a` を動かさない理由を結果で1つ示せる
- [ ] 非熱誤差混入時に発散/誤学習しない制約を1つ入れる
- [ ] 論文では「設計指針 + toy結果」か「設計指針のみ」かを決断

---

## 3. 2テーマの依存関係

```text
b_case 進化 (A)
  ├─ A1 面依存係数 ...... 論文の Level-2 本体を固める
  ├─ A2 過渡 ON/OFF ..... Adaptive の動機・入力設計に効く
  └─ A3 入力拡張 ........ 必要なら Level-2 を厚くする

Adaptive (B) … 方針は §2.4 で確定
  ├─ 今の初期捕捉は FF、次パス改善が Adaptive
  ├─ 更新対象は mode-wise δb（A の b_case 残差）
  ├─ A2 の過渡残差を吸収する置き場にもなる
  └─ 論文では「FF主結果 → Adaptive帰結」の順序を崩さない
```

推奨順序:

1. **A1**（面依存チェック）で Level-2 式を固定
2. **B1–B2** で §2.4 方針の toy 更新式を実装
3. **B3** でパスまたぎの FF vs FF+Adaptive 比較
4. A2/A3 は結果を見て「入れる / Limitations」を決める

---

## 4. 論文執筆との切り分け

| 項目 | 執筆前にやる | 執筆に回す / 今後課題でよい |
|---|---|---|
| Level-2 最終式の固定（A1） | ○ | |
| Adaptive toy（B） | ○（最低限） | 飛行実証・本格推定器 |
| 過渡ON/OFF 1ケース（A2） | できれば | 間に合わなければ Limitations |
| HOT/被覆の完全一般化 | | ○ |
| Adaptiveを主定量結果にする | | ✗（しない） |
| タイトルの `Adaptive Correction` を残すか | 残さない。正式名称は `260802` §0 | ICSOサイトで題変更できるかは要確認 |

---

## 5. すぐ着手するときの最初の問い

1. A1 の比較は、既存ケースだけで LOO できるか？ 追加 TD/Femap が要るか？
2. Adaptive toy の「観測残差」は、既存 PAT sim のどの出力を使うか？（方針上は捕捉後 QD/FPM 相当）
3. 非熱誤差を混ぜるとき、更新を止める/弱めるルールを最初から入れるか？
4. 論文に載せる Adaptive は「式+パスまたぎ toy図」までか、「§2.4 の設計指針段落」までに留めるか？

---

## 6. 関連ノート（読む順）

Adaptive / 方針:

1. **[`260808_adaptive_two_layer_b_update.md`](260808_adaptive_two_layer_b_update.md)** … `b` 二層更新の正本
2. [`google_doc/MD/260717_Adaptiveモデル/content.md`](google_doc/MD/260717_Adaptiveモデル/content.md) … Adaptive 専用の原点
3. [`260721_rg_slide_retrospective_and_paper_narrative.md`](260721_rg_slide_retrospective_and_paper_narrative.md) §2.10
4. [`260722_optcomm_rg_feedback_response_plan.md`](260722_optcomm_rg_feedback_response_plan.md) §B, §C, 優先度C
5. [`260802_update_main_typ_to_260721_slides.md`](260802_update_main_typ_to_260721_slides.md) §1.3, §2.11.3

`b_case` / Level-2:

5. [`260714_sunface_compo_handoff.md`](260714_sunface_compo_handoff.md)
6. [`260715_icso_paper_outline.md`](260715_icso_paper_outline.md)
7. [`MD/20260525_labseminar_slide/content.md`](MD/20260525_labseminar_slide/content.md) … 初期の FF+Adaptive 構想

---

## 7. 作業チェックリスト（このノートの本体）

### `b_case`

- [ ] A1: sun×heat / heat-faces限定 / 現行 の LOO 比較
- [ ] A1結果で Level-2 式を固定
- [ ] A2: 過渡ON/OFFをやるか決める（やるなら1ケース）
- [ ] A3: 軌道平均局所温度などを入れるか決める

### Adaptive（方針正本: `260808_adaptive_two_layer_b_update.md`）

- [x] 役割: 今の初期捕捉は FF、次パス改善が Adaptive
- [x] 観測: 主は QD/FPM residual、Rxパワーは補助
- [x] 二層: 速い `δb[mode]` + 条件付き遅い `b_case`、`a` は固定
- [x] **Toy-1: mode-wise `δb` のみ**（`adaptive.py` / `run_adaptive_pat.py`）
- [x] Toy-2: `w_orbit_small` で `b_case` 吸い上げ（幾何ゲート第一版）
- [ ] Toy-3: 非熱混入下の誤学習比較
- [ ] 論文への載せ方を決断（toy結果 / 設計指針のみ）

### 論文に入れる項目（忘れ防止・別トラック）

- [ ] S-TLE vs S-GNSS（RESORB）PAT 結果を Methods/Results に反映  
  → [`260811_gnss_optical_comm_orbit_error.md`](260811_gnss_optical_comm_orbit_error.md) §5.3・§6
