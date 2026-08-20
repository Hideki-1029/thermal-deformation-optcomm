# ICSO英語稿　五十里先生・高嶋さん・草野さんFB対応チェックリスト

## 対象

- 五十里先生コメント付きPDF: `papers/icso/main_en_ICSO_takamoto_五十里コメント.pdf`
- 高嶋さんコメント追記版PDF: `papers/icso/main_en_ICSO_takamoto_五十里コメント_高嶋コメント.pdf`
- 草野さんコメント追記版PDF: `papers/icso/main_en_ICSO_takamoto_五十里+草野コメント.pdf`
- 対応先原稿: `papers/icso/main_en.typ`
- 確認日: 2026-08-19
- 各PDFの注釈を統合し、合計30件（五十里先生13件、高嶋さん9件、草野さん8件）をページ番号と指摘対象に紐づけて転記した。

## 用語・表現

- [x] p. 1　`line of sight`
  - FB: 「正確には、LOS angleでは？」
  - 対応: Abstractの `relative line of sight (LOS)` を `relative line-of-sight (LOS) angle` に修正し、予測量が角度であることを明示した。

- [x] p. 1　`temperature`
  - FB: 「なんの温度？」
  - 対応: Abstractの入力説明を `temperature` から `the temperature difference between the centers of the sun-facing and opposite panels` に具体化した。

- [x] p. 1　`star-tracker`
  - FB: 「ハイフンつけない」
  - 対応: `star-tracker reference` を `star tracker reference` に修正した。また、本文の `star-tracker-based system` はハイフンを残さない `system based on a star tracker` に書き換えた。

- [x] p. 1　`box-shaped low-Earth-orbit`
  - FB: 「ハイフンつけない」
  - 対応: Abstractを `a satellite with a box structure in low Earth orbit` に書き換えた。本文と図表の `box-shaped` も `with a box structure` に統一した。

- [x] p. 1　`two-axis`
  - FB: 「ハイフンつけない」
  - 対応: `two-axis` を原稿全体で廃止し、文脈に応じて `both axes`、`for the two axes`、`across the two axes` に書き換えた。

- [x] p. 1　`COLD/surface`
  - FB: 「大文字の意味がある？」
  - 対応: Abstractの `17 standard COLD/surface cases` を `17 cases under the baseline cold orbit and surface conditions` に修正した。Abstractでは定義前の大文字ラベルとスラッシュ表現を避け、本文の条件定義では正式なケース名として `COLD` / `HOT` を維持した。

- [x] p. 1　`orbit-prediction`
  - FB: 「普通ハイフンつけない場所にたくさんハイフンがついている。AIっぽさも感じるので、全体的に見直してください。」
  - 対応範囲: 指摘箇所だけでなく、本文・abstract・題名・図表キャプション全体の不自然なハイフンを点検する。
  - → 260819_icso_hypehen....mdに候補記載
  - 

- [x] p. 15　`LOS`
  - FB: 「LOS angle / 他も同様な場所全て見直してください」
  - 対応範囲: `LOS` を角度量の意味で使っている全箇所を確認する。



## レイアウト

- [x] p. 2　`making it potentially one of the largest initial pointing-error components. This study`
  - FB: 「行間が急に小さくなっていて、変に感じる。他にも段落が変わる時に毎回同じことになっていそう。」
  - 対応範囲: 全ページの段落間隔と行送りを点検する。



## 関連研究

- [no-change] p. 4　`Table 1. Representative`
  - FB: 「望月君も似たような研究をしているので、彼の学会発表論文を引用しても良いかもしれません。良いものがないか聞いてみてください。」
  - 要対外確認: 望月氏に引用候補となる学会発表論文を確認する。
  - →（高本）少し時間がかかるので、一旦対応無し



## 数値の有効数字

- [x] p. 6　`0.59 m × 0.60 m × 0.99 m`
  - FB: 「1mじゃなく0.99mという有効数字にしている意味って何かあるのでしょうか？」
  - 対応: 代表寸法として `0.6 m × 0.6 m × 1.0 m` に丸めた。

- [x] p. 6　`23.9 °C`
  - FB: 「これも24度じゃダメなのでしょうか？」
  - 対応: 基準温度を `24 °C` に丸めた。



## 結論の強化

- [x] p. 15　`nonthermal error. Future`
  - FB: 「定量的な結果示した後、最後のまとめとして、『よって、＊＊＊であることが示せた。これは＊＊＊に貢献すると言える』みたいなことを書きたい。」
  - 対応: 定量結果の直後に、評価条件下では予測可能な熱成分を低減し、残る探索負担が主に非熱誤差で決まる状態まで改善できたことを明記した。さらに、光フィードバックが得られる前の衛星光リンク確立の高速化に貢献し得る、という運用上の意義を追加した。



## 最終確認

- [ ] 上記13件の対応後、`main_en.typ` を再ビルドする。
- [ ] 修正後PDFを全ページ目視し、段落間隔、改ページ、図表、参考文献の崩れがないことを確認する。
- [ ] 日本語版と数値・論理・主張の差分を再監査する。



## 高嶋さんコメント（9件）

温度単位は先行実施。Constant-bias only 以外は推奨案で原稿へ反映した。

### Abstractの統計量

- [x] p. 1　`the mean subsequent-orbit RMSE on the dominant axis was 5.5 µrad, compared with a median raw LOS RMS of 615 µrad.`
  - FB: 「mean RMSE と median RMS を並べていて若干不自然？」
  - 対応: Abstract と結論を median RMSE 4.9 µrad vs median raw RMS 615 µrad に揃えた。本文のモデル節では mean 5.5 / median 4.9 の併記を残した。



### 姿勢抽出方法

- [x] p. 6　`The relative LOS time series is extracted from the rotations of the representative STT and LCT nodes at their centers.`
  - FB: 「姿勢を求めるのはこの方式で精度は十分なのでしょうか？メッシュを切っていると思うので、取付インタフェース領域の節点群に対する最小二乗剛体フィットなどで姿勢を求めなくて良いのでしょうか？」
  - 対応: 代表節点回転は機器姿勢の代理であり、取付面の剛体フィットは今後の精度確認、と解析手順に1文追加した。LOS定義自体は変更していない。



### 温度単位

- [x] p. 6　`/°C`
  - FB: 「K ? / 似たような箇所が他にもあれば」
  - 対応範囲: 感度・温度差の単位を原稿全体で確認する。
  - 対応: 線膨張率・感度・温度差の単位を `K` に統一した。絶対温度（初期 20 °C、基準 24 °C）は °C のまま。図 `p3_a_emp_by_sunface.png` の縦軸も再生成した。



### ケース行列とCase ID

- [x] p. 8　`Four sun faces; PROP only, PCDU only, or no additional dissipation`
  - FB: 「理解が違っていたら申し訳ないですが、4 surface × 3電源パターンで12ケースになるのかなと思ったのですが、13–21は9ケースなので、対応がどうなっているか分からず。Case 01–03, 07 が欠番なのも若干気になります。もし列が入るなら、Case ID | Sun face | PROP | PCDU | Orbit (COLD/HOT/LTAN18) | Surface | Raw dominant-axis RMS [µrad] | Nested-LOO test RMSE [µrad] すべてを記載しても良いかもしれない」
  - 対応: 要約表は残し、本文とキャプションで 13–21 が 4×3 の一部（残りは 06 と 23–24）、評価番号は 04–06, 08–25、01–03, 07 は MZ/セットアップで評価外、と明示した。21行の全一覧表は紙面の都合で追加していない。

- [x] p. 13　`COLD/baseline-surface cases, Cases 4–6 and 8–21`
  - FB: 「ケースの番号の対応は合っていますか？」
  - 対応: HOT/被覆違いの 10–12 を外し、COLD・標準表面の 14 ケース（4–6, 8–9, 13–21）で PAT を再集計した。Abstract/本文/結論の捕捉時間は 14.6→0.10 s（熱のみ）、19.2→5.45 s（非熱込み）、成功率 98%→100% に更新した。



### 図と本文の数値整合

- [x] p. 11　`The dominant-axis bias RMSE is approximately 3.1 µrad in-sample and 3.8 µrad`
  - FB: 「図中の記載数値2.1、2.3 µrad と値が食い違っている？」
  - 対応: `p3_b_emp_vs_b_pred.png` を 21ケースの現行 CSV から再生成し、図注釈を 3.1 / 3.8 µrad にした。キャプションでは支配軸と非支配軸の 3.1 µrad を分けて書いた。

- [x] p. 12　`In the PY all-dissipation case, for example, the raw RMS was approximately 1250 µrad and the post-model RMSE approximately 4 µrad.`
  - FB: 「これがFigure 7に対応すると思っているのですが、図中の数値と食い違っている？」
  - 対応: 対象を Case 08 と明記し、本文・キャプション・図タイトルを raw RMS 1250 µrad、test RMSE 3.9 µrad に揃えた。`p2_bcase_true_vs_pred_case08.png` を再生成した。



### PAT評価条件と比較方法

- [x] p. 13　`Table 7.`
  - FB: 「検証の前提条件がどこかに情報があると良そう。
    - 何本のラン（開始エポック）の平均か
    - 非熱誤差の乱数シードを何回振ったか（Monte Carlo回数）
    - 初期の条件
    - Success rate の有効数字も試行回数から決まりそう」
  - 対応: Results と表キャプションに、3軌道・301点、ケース平均の平均、非熱は 1 seed/ケースで MC なし、を追記した。成功率は 98% に丸めた。

- [no-change] p. 13　`No correction`
  - FB: 「得られた改善の大部分はDC項（bias）の除去のようにも思うので、ΔT項を0とした補正の結果を `Constant-bias only` として列を追加して書いておくと、ΔT modelの必要性がわかりやすいのでは？」
  - 対応: 今回は列追加しない。



## 高嶋さんコメントの対応後確認

- [x] 高嶋さんの9件の対応後、ケースID、本文数値、図中数値、PAT試行条件の相互整合を再監査する。
- [x] `main_en.typ` を再ビルドし、修正後PDFの図表と改ページを確認する。



## 草野さんコメント（8件）

英語稿 `main_en.typ` のみ。推奨案で反映済み。

### 改行位置と表のレイアウト

- [x] p. 1　`communications`
  - FB: 「改行位置に気をつかいましょう」
  - 対応: 題名を意味の切れ目で3行にした。`Hierarchical Prediction and Feedforward Correction` / `of Time-Varying Thermal Line-of-Sight Bias` / `for Coarse Acquisition in Satellite Optical Communications`。`Optical / Communications` の切れは解消。

- [x] p. 4　`Acquisition evaluation`
  - FB: 「全体的に、表内文の改行位置をもう少し見やすいように直した方が良さそうです。」
  - 対応: 関連研究表を優先し、見出しと長いセルを意味の切れ目で改行。表全体でハイフン分割を止め、解析条件・PAT・残差表も同じ方針で直した。

- [x] p. 7　`In the deformation budget of a representative case, the mean centerline tilt between the STT and LCT reference points`
  - FB: 「公式フォーマット通りなら問題ないが、表前後の行間が全体的に少ないように感じます。確認してみてください。」
  - 対応: 公式 LaTeX 指示の下限 0.2 in より少し広い 0.28 in を、英語稿の図表ブロック上下に設定した。`template.typ` は触っていない。



### 熱ひずみに注目する論理

- [x] p. 2　`Second, it is governed by known operating conditions, including eclipse cycles, the sun-facing panel, surface optical properties, and internal dissipation, and is therefore not a wholly unknown disturbance.`
  - FB: 「熱ひずみに注目した理由にはなっていないように思います。1つ目の『その他の要因と比較して、影響が大きいから』というのが理由で、そのうえで事前情報からある程度予測することが可能なのでその手法を考えたという流れが適切かと思います。」
  - 対応: `for two reasons` の並列をやめ、大きさで着目し、既知の運用条件に支配されるので予測手法を立てる、という順に書き換えた。



### FFの初出と略語定義

- [x] p. 3　`FF`
  - FB: 「Feed Forwardの略ですかね？見落としていたら申し訳ないですが、どこかに記載有りますか？」

- [x] p. 3　`FF`（上記への追記コメント）
  - FB: 「後半にありましたね。順番的にこちらの図が最初なので分かる表現にするか説明がほしいところです。」
  - 対応: 問題図を `Coarse acquisition feedforward`、関連研究表を `feedforward of attitude and mounting errors` にした。略語 `FF` は残差更新節で `feedforward (FF)` と定義してから使う。



### スキャン軌跡の図

- [x] p. 12　`7.1. Scan conditions`
  - FB: 「紙面に余裕があるならば、scan軌跡の図を入れると分かりやそうです」
  - 対応: Scan conditions の表の直後に、120 µrad ステップと 150 µrad 検出半径が読める矩形スパイラルの局部図を追加した（`figure/fig_rectangular_scan.png`）。全走査は 27×27、±1600 µrad。



### 捕捉後残差の観測可能性

- [x] p. 14　`the post-acquisition dominant-axis residual`
  - FB: 「以前RGで議論したことにも関連しますが、捕捉完了後の熱ひずみによる残差はどのように観測するのでしょうか。本節の目的としては、そこは考えなくて良いんですかね。」
  - 対応: 本節を、捕捉後に残差時系列が得られた場合の数値実験と明示した。想定観測は受信センサ上の全指向残差であり、熱成分の分離ではない、と書いた。ハードウェアと疎サンプルは今後、と限界文につなげた。



## 草野さんコメントの対応後確認

- [x] 草野さんの8件の対応後、題名と表内の改行、表前後の間隔、FFの初出、序論の論理展開を再確認する。
- [x] 残差更新節で、捕捉後残差の観測可能性と本節の評価範囲が明確か確認する。