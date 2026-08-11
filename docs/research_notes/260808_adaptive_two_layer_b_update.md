# Adaptive: `b` の二層更新方針

- 作成: 2026-08-08
- 目的: Adaptive における `b` 更新の設計指針だけを固定する
- 親ノート（ロードマップ全体）: [`260808_pre_paper_bcase_adaptive_roadmap.md`](260808_pre_paper_bcase_adaptive_roadmap.md)
- 状態: **方針合意済み** → **次は Toy-1 実装**（`δb[mode]` のみ）
- 並行メモ（論文に入れる・忘れ防止）: GNSS級 PAT 結果は [`260811_gnss_optical_comm_orbit_error.md`](260811_gnss_optical_comm_orbit_error.md) §5.3・§6

---

## 1. 一言で

```text
速い層 δb[mode]  : 捕捉後残差で毎回更新 → 次パスの初期捕捉を楽にする（目標B）
遅い層 b_case    : 信頼できる残差だけを熱テーブルへ吸い上げる（目標A）
a                : 動かさない（事前固定）
```

Feedforward が今の初期捕捉を担い、Adaptive は成功パスのあとで次パスを改善する。

---

## 2. 二つの目標（混ぜない）

| | 目標A | 目標B |
|---|---|---|
| 更新したいもの | 熱LOSモデルの係数 `b_case` | 次パス用の経験的補正 `δb` |
| 成功の定義 | 熱モデルが良くなる | 捕捉時間・scan area が下がる |
| 他誤差の混入 | 困る | ある程度は仕様 |
| 単独だと弱い点 | 軌道誤差と分離困難 | 一般PATの経験補正に見えやすい |

二層に分けると両方狙える。

- 目標Bだけだと「よくある経験的バイアス更新」に寄りやすい
- 目標Aだけだと、残差をそのまま入れる設計と矛盾する
- **速いδb + 条件付きで遅いb_case** なら身分が分かれる

---

## 3. 役割分担

```text
今この瞬間の初期捕捉
  → FF: θ_ff = b_case + a(sun_face)·ΔT(t) + δb[mode]
  → 光が QD/CCD に当たる前でも使える

一度リンクが取れたあと
  → Adaptive: 残差 r から δb /（条件付きで）b_case を更新
  → 効くのは同じ mode の次パス以降
```

初期捕捉前半は光観測がほぼ取れない。Adaptive のサンプルは成功パスごとに疎、でよい。

---

## 4. 観測量

| 観測 | 役割 |
|---|---|
| 自機 QD / FPM スポット残差 | **主観測**（捕捉成立〜精追尾開始直後） |
| Rx パワー | 補助（ゲート・参考） |
| 軌道予測誤差の事前信頼度（TLE age 等） | `b_case` 吸い上げの重み |
| 地上局 Rx / 相手衛星 PAT | 将来の追加チャネル（本線ではない） |

残差の中身:

```text
r = θ_obs − (b_case + a·ΔT + δb)
  ≈ 熱モデル誤差 + e_orbit + e_align + e_other
```

ただし先に熱FFがあるので、`r` は生LOSではなく **innovation**。  
「単純な経験補正」より熱モデル接続は強い。それでも単観測での完全分離は主張しない。

---

## 5. 二層更新（本線）

### 5.1 記号

```text
mode        ≈ (sun_face, I_prop, I_pcdu)
a           : 事前固定
b_case[mode]: 熱モデル Level-2（遅い更新のみ）
δb[mode]    : 経験的補正（速い更新）
```

### 5.2 Pass ごとの手順

```text
Pass n（mode 既知）:
  1. θ_ff = b_case[mode] + a·ΔT + δb[mode]
     → これで初期捕捉（FF）

  2. 捕捉成功後、r = θ_obs − θ_ff を得る

  3. 速い層（毎回・目標B）:
     δb[mode] ← δb[mode] + γ_fast · r

  4. 遅い層（条件付き・目標A）:
     b_case[mode] ← b_case[mode]
                    + γ_slow · w_orbit_small · w_mode · Proj_thermal(δb[mode])
     （実施したら、吸い上げた分を δb から引いてもよい）

Pass n+1（同じ mode）:
  更新後の θ_ff で初期捕捉時間がさらに下がることを狙う
```

### 5.3 各項の意味

| 項 | 意味 |
|---|---|
| `γ_fast` | 次パス用。大きめでもよいが過学習しない程度 |
| `γ_slow` | 熱テーブル用。小さく、複数パス分たまってから |
| `w_orbit_small` | 軌道予測誤差が小さいと期待できるときの重み |
| `w_mode` | 同一 mode の反復・サンプル数に応じた信頼度 |
| `Proj_thermal` | 温度・発熱モードと繰り返し相関する成分だけ残す操作（最初は「同一mode平均」でも可） |

### 5.4 なぜ mode 別か

1. `b_case` 自体が mode 依存
2. MY+PROP の残差で MX を壊さない
3. 非熱誤差をグローバルバイアスにしない

---

## 6. 軌道予測誤差ゲート（目標Aの鍵）

五十里先生指摘: 軌道予測誤差も軌道周期連動の低周波で、LOS角だけなら熱と分離困難。

こちら側の答えは「完全分離」ではなく **信頼度ゲート**:

```text
軌道誤差が小さいと期待できる区間の残差ほど、
b_case へ吸い上げる重みを上げる
```

使える既存情報（リポジトリ）:

- TLE age ビン別 RMS（`orbit_prediction_error_summary.csv`）
- 時系列 `isl_angle_*`（区間ごとの大小の代理）
- 詳細: [`260718_orbit_prediction_error_assumptions.md`](260718_orbit_prediction_error_assumptions.md)

言えること / 言いすぎ:

| 言える | 言わない |
|---|---|
| 軌道誤差期待値が小さい区間では、残差の軌道成分が平均的に小さい | その区間の残差＝熱そのもの |
| だから `b_case` 更新の信頼度を上げられる | 同周波数帯でも完全識別できた |
| soft weight として有効 | hard な分離器 |

残る汚染: アライメント、姿勢、相手側誤差など。  
なので「小さい期間だけON」より、`w_orbit_small` による重みつきゆっくり更新が安全。

---

## 7. 相手衛星・地上局チャネル（将来）

| 情報源 | 期待 | 今すぐ? |
|---|---|---|
| 地上局受信強度・ビーム位置（OSIRIS型） | 自機送信バイアスの別幾何観測 | 将来。Related Work的にも相性が良い |
| 相手衛星 QD/FPM | 相対ポインティングの向こう側 | 将来。相手熱・相手軌道も混ざる |
| 双方残差の突合 | 共通/固有成分の整理 | 研究拡張向き |

本線はあくまで **自機 residual + 軌道信頼度ゲート**。  
追加チャネルは `w_*` を厚くする材料、と見る。

---

## 8. 新規性の置き場

弱い主張:

```text
✗ 残差にゲインをかけてバイアスを更新した（一般的に見えやすい）
✗ 軌道上で熱係数 b を完全同定・分離した
```

残す主張:

```text
○ 熱階層FF（a·ΔT + b_case(mode)）が初期捕捉の主補正
○ Adaptive はその innovation を
   - 速く δb に入れ（次パス）
   - 信頼できる成分だけ遅く b_case に戻す（熱モデル更新）
○ 軌道誤差は共存するものとしてゲートで扱う
```

経験的補正単体の新規性は主張しない。差分は **熱階層FFとの二層接続**。

---

## 9. 論文・実装での言い方

使う言葉:

- `b_case`: 熱モデル Level-2（事前 + 遅い昇格のみ）
- `δb`: residual correction / 運用補正表
- 「熱と軌道を分離した」ではなく「信頼度の高い残差を熱テーブルへ昇格」

評価で見る量:

1. 同一 mode のパスまたぎ捕捉時間・scan area（目標B）
2. `w_orbit_small` あり/なしで `b_case` 誤学習がどう変わるか（目標A）
3. FF only vs FF+δb vs FF+δb+slow `b_case`

---

## 10. 実装の段階

| 段階 | 内容 | 目標 |
|---|---|---|
| Toy-1 | mode-wise `δb` のみ | B |
| Toy-2 | `w_orbit_small` で `b_case` へ遅い吸い上げ | A+B |
| Toy-3 | 非熱混入下の誤学習比較 | 主張の防御 |
| Later | 地上局/相手PATチャネル | 拡張 |

最初の実装は Toy-1 でよい。理想形は Toy-2。

---

## 11. 関連

- ロードマップ: [`260808_pre_paper_bcase_adaptive_roadmap.md`](260808_pre_paper_bcase_adaptive_roadmap.md)
- Adaptive 原点メモ: [`google_doc/MD/260717_Adaptiveモデル/content.md`](google_doc/MD/260717_Adaptiveモデル/content.md)
- ナラティブ: [`260721_rg_slide_retrospective_and_paper_narrative.md`](260721_rg_slide_retrospective_and_paper_narrative.md) §2.10
- 軌道誤差前提: [`260718_orbit_prediction_error_assumptions.md`](260718_orbit_prediction_error_assumptions.md)
- 五十里指摘メモ: `google_doc/google_doc_from260415_20260618.md`（軌道予測誤差と同帯域・分離困難）
