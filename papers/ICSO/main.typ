#import "template.typ": spie-paper

#let todo-fig(label-text) = {
  block(
    width: 100%,
    height: 3.2cm,
    stroke: 0.6pt + luma(120),
    fill: luma(245),
    inset: 10pt,
    align(center + horizon)[
      #set text(size: 9pt, fill: luma(60))
      （自作図予定）#label-text
    ],
  )
}

#show: spie-paper.with(
  title: [Feedforward and Adaptive Correction of Time-Varying Thermal Bias for Coarse Acquisition in Optical Communication Systems],
  authors: [
    Hideki Takamoto#super[\*], Kazuki Takashima, Yuki Kusano, Satoshi Ikari, and Ryu Funase
  ],
  affiliations: [
    Department of Aeronautics and Astronautics, The University of Tokyo, Tokyo, Japan
  ],
  corresponding-email: [Corresponding author: Hideki Takamoto, email: TBD],
  abstract: [
    光通信ではビーム拡がり角が小さいため，Pointing, Acquisition, and Tracking (PAT) の粗捕捉における初期指向誤差が捕捉時間を支配する．本研究では，低軌道衛星の熱変形に起因するスターセンサ (STT) と光通信端末 (LCT) 間の時変 Line-of-Sight (LOS) バイアスを，少数の温度・運用情報から予測し，粗捕捉の scan center に feedforward 補正する．Thermal Desktop と Femap による熱構造解析から遠方通信用の相対 LOS 時系列を生成し，太陽指向面と反対面の温度差 $Delta T(t)$ に対する共有感度と，太陽面・内部発熱 ON/OFF で説明するケース定数バイアスからなる階層モデルを構築する．熱LOS予測単体としては，標準ケースで数百〜千 µrad 級の熱成分を数 µrad 程度まで低減できる．粗捕捉性能は軌道予測・姿勢・アライメント等の非熱誤差を含む条件で評価し，熱成分補正により平均捕捉時間を短縮できることを示す．軌道上観測による adaptive 層は枠組みとして位置づけ，本稿では物理ベース予測層を主結果とする．
  ],
  keywords: (
    "optical communication",
    "pointing, acquisition, and tracking",
    "thermal deformation",
    "line-of-sight bias",
    "feedforward correction",
  ),
)

= 序論

衛星光通信は高いアンテナ利得と広い帯域を実現できる一方，ビーム拡がり角が小さいため Pointing, Acquisition, and Tracking (PAT) がリンク確立の鍵となる@2017-kaushal-survey．特に粗捕捉段階では相手機からの光フィードバックが得られないため，軌道予測誤差，姿勢誤差，アライメント誤差，熱変形などを含む初期指向誤差を考慮して探索する必要がある@2023-riesing-tbird．探索コストは不確定領域半径の概ね二乗に比例するため，予測可能な誤差成分を事前に補正できれば捕捉時間を短縮できる．

本研究ではその成分として，衛星構体の熱変形に起因する STT–LCT 相対 LOS バイアスに着目する．低軌道では日照・食サイクルや内部発熱により温度場が時変し，相対 LOS も軌道位相に応じて変化する@2024-badas@2023-shi-thermal．本稿の貢献は次の三点である．(1) 熱構造解析により代表 LEO 条件での STT–LCT 相対 LOS を定量化する．(2) 太陽面−反対面温度差に対する共有感度と，ケース定数バイアスを発熱 ON/OFF で説明する階層 ΔT モデルを提案する．(3) 予測 LOS を粗捕捉の scan center 補正に接続し，補正なし・静的バイアス・理想真値補正と比較する．

= 関連研究

光学機器では，構造の温度勾配と LOS 変動を一次関係で結び，地上試験で係数を得た例がある（JANUS 光学ヘッド）@2021-turella-janus ．観測衛星では軌道位相や観測履歴に基づく LOS 補正も報告されている@2022-hu-thermal-motion @2025-li-thermal-los ．光通信衛星では，STT–LCT 相対角変動を構造最適化で低減する研究@2023-shi-thermal や，姿勢・取付不確かさを FSM で feedforward する研究@2026-riiddenklau-ff がある．後者は熱変形を温度から予測する枠組みではない．

本研究の差分は，衛星バス上の離隔した STT–LCT 相対 LOS を対象に，主説明変数として太陽指向面と反対面の温度差を用い，感度をケース横断で共有しつつ，ΔT に入りきらない DC を内部発熱フラグで階層的に説明し，粗捕捉の scan center 補正へ直結させる点にある．式形そのもの（切片付き一次）を新規と主張するものではない．

= 問題設定とLOS定義

遠方通信の粗捕捉では，衛星姿勢基準が STT に依存する場合，通信光軸の初期ずれは主に STT 基準で見た LCT 外向き光軸の相対回転として現れる．本稿ではこの量を遠方通信用熱 LOS（支配軸成分を $theta_"dom"$）と呼ぶ．名目指向を $theta_"nom"$，予測熱LOSを $hat(theta)_"th"$ とすると，scan center 指令は
$
theta_"scan" = theta_"nom" - hat(theta)_"th"
$<eq_scan>
とする．補正後残差は非熱誤差と熱予測誤差の和であり，本手法は全指向誤差を消去するものではなく，予測可能な熱成分を減らすことで探索負荷を下げる．

#figure(
  todo-fig[S1: 箱型衛星・STT/LCT・太陽光・構体曲げと相対LOS，および scan center 補正式],
  caption: [問題設定の概念図（自作図予定）．],
)<fig_s1>

= 熱構造解析

熱環境は Thermal Desktop，構造応答は Femap/Nastran により解析する．ケース行列で太陽指向面（MX/MY/PX/PY），表面光学特性，PROP/PCDU 等の内部発熱 ON/OFF，COLD/HOT 軌道を振る．温度を構体へマッピングし，STT・LCT 代表節点の変位・回転から遠方通信用相対 LOS 時系列を得る．

#figure(
  image("figure/p1_far_field_los_case04.png", width: 95%),
  caption: [代表ケース（MY 太陽指向，ALL HEAT）の far-field PAT LOS 成分分解．支配軸は軌道内で百〜数百 µrad 級に変動する．],
)<fig_p1>

太陽指向面が変わると支配軸も変わる（例: MY/PY で y，PX/MX で x）．表面光学特性は主に変動幅（ptp）に効き，内部発熱配置は平均バイアスと波形に効く．これらの感度は次節のモデル入力（ΔT，太陽面，発熱フラグ）の物理的根拠となる．

= 階層sunface ΔTモデル

オンボードで TD/Femap を逐次実行することは現実的でないため，解析 LOS を truth として軽量モデルへ圧縮する．軌道内の時変は温度差一本で足り，コンポ発熱の残りはケース定数側に分離するのが安定であった．

== Level 1（軌道内）

支配軸について
$
theta_"dom"(t) approx b_"case" + a("sun") thin Delta T(t),
quad
Delta T(t) = T_"sunface"(t) - T_"opposite"(t)
$<eq_level1>
とする．$a("sun")$ は太陽面ごとの感度 [µrad/°C]，$b_"case"$ はそのケースの DC バイアス [µrad] である．非支配軸は軌道内で変動が小さい場合が多く，本稿の PAT 接続では学習区間の静的平均で扱う．

== Level 2（ケース間）

$b_"case"$ を太陽面ダミーと発熱フラグで説明する．
$
b_"case" approx b_0("sun") + c_"prop" I_"prop" + c_"pcdu" I_"pcdu"
$<eq_level2>
ここで $I_*(in {0,1})$ は PROP/PCDU 発熱の ON/OFF である．実装上，発熱フラグが効くのは取付面に対応する MY/PY 系を主とする．予測時は面ごとの $a_"emp"$ 中央値を共有感度 $a_"shared"$ とし，
$
hat(theta)_"dom"(t) = b_"pred"("sun", I_"prop", I_"pcdu") + a_"shared"("sun") thin Delta T(t)
$
を用いる．固定パラメータは $a$ 4 個，$b_0$ 4 個，$c_"prop"$，$c_"pcdu"$ の計 10 スカラーである．

#figure(
  todo-fig[S2: 上段 ΔT→a·ΔT（時変），下段 太陽面・発熱→b_case，合流して LOS 予測．固定10係数],
  caption: [階層モデルの構成（自作図予定）．],
)<fig_s2>

== 係数と同定結果

各ケースの先頭1軌道で @eq_level1 を当て $a_"emp"$，$b_"emp"$ を得た後，全ケースの $b_"emp"$ に @eq_level2 を OLS フィットする．共有感度は $|a_"shared"| approx 28$–$31$ µrad/°C（MX $+30.6$，MY $+28.6$，PX $-28.1$，PY $-28.7$）となり，符号は太陽面（支配軸の向き）で決まる．Level-2 係数は $c_"prop" approx -23.8$ µrad，$c_"pcdu" approx -11.1$ µrad などである．面加熱の主効果の多くは $a thin Delta T$ に吸収され，$c_*$ はパネル中心 ΔT に入りきらない残差 DC を表す．

#figure(
  image("figure/p3_a_emp_by_sunface.png", width: 88%),
  caption: [ケースごとに独立推定した $a_"emp"$ の太陽面別分布．面内で値が揃うため共有感度として使える．],
)<fig_a>

#figure(
  image("figure/p3_b_emp_vs_b_pred.png", width: 72%),
  caption: [経験バイアス $b_"emp"$ と Level-2 予測 $b_"pred"$．in-sample RMSE 約 1.7 µrad，leave-one-case-out 約 2.3 µrad．],
)<fig_b>

#figure(
  image("figure/p2_bcase_true_vs_pred_case08.png", width: 95%),
  caption: [階層予測の時系列例（PY 太陽指向）．$b_"pred" + a_"shared" Delta T$ が truth の軌道内変動を追従する．],
)<fig_ts>

#figure(
  image("figure/p5_raw_vs_model_rmse.png", width: 90%),
  caption: [支配軸の生 RMS/peak と階層モデル test RMSE．数百〜千 µrad 級を数〜十数 µrad へ低減する．],
)<fig_scale>

標準の 1213COLD・既定被覆では test RMSE が数 µrad 程度である（例: case08 で生 RMS 約 1250 µrad → モデル後約 3 µrad）．Black 被覆では時変残差の床が上がり（約 13 µrad），HOT 軌道では時変は追えるが COLD 用 Level-2 から $b$ が数 µrad ずれる．MZ 太陽指向など ΔT–LOS 関係が弱い条件は本稿の主評価から除外する．

取付点温度を軌道内特徴に足す拡張は共線・低 SNR で係数が不安定であった．コンポ効果は時系列特徴ではなくケース定数 $b$ 側に置く，という分離が本モデルの設計原則である．

= PAT評価

#figure(
  todo-fig[S3: TD/Femap truth → 階層予測 → scan center FF → spiral scan → 捕捉時間．比較: no/static/bcase/truth],
  caption: [PAT 評価の流れ（自作図予定）．],
)<fig_s3>

矩形スパイラル走査を仮定し，検出半径内に入れば捕捉成功とする．熱LOS予測は Level-2 を leave-one-case-out した $b_"pred"$ と共有 $a$ を用いる．評価の切り分けとして，(i) 熱LOSモデルの当てはまりは前節のとおり熱成分のみで語り，(ii) 捕捉時間・scan-center 誤差など粗捕捉性能は，軌道予測・姿勢・アライメント等の非熱誤差を加えた条件を主に報告する．比較アームは補正なし，静的バイアス，階層モデル，および熱真値補正（上界）である．

#figure(
  image("figure/p4_pat_model_comparison.png", width: 92%),
  caption: [17 ケース横断の平均捕捉時間比較．熱のみの参考値に加え，非熱込み条件での改善を本文で主に議論する．],
)<fig_pat>

参考として熱誤差のみでは，17 ケース平均の捕捉時間が補正なし約 137 s，階層モデル約 0.12 s，理想真値 0.10 s となり，モデルが熱成分をほぼ取りきれることを確認できる．一方，非熱誤差を加えた 17 ケース平均では，補正なし約 171 s に対し階層モデル補正で約 22 s まで短縮した．すなわち実運用に近い誤差予算では非熱が床を作り，137 s → 0.12 s のような劇的短縮は期待できないが，熱成分を落とすことでなお捕捉時間を大幅に削減できる．熱LOSがもともと小さいケースでは，非熱込みでの改善幅が相対的に小さくなることにも注意する．

提出アブストで述べた二層枠組みのうち，本稿の主結果は物理ベース予測層である．捕捉後のセンサ残差による adaptive 更新は，モデル誤差や未モデル化ドリフトへの対処として位置づけ，詳細実装と定量比較は今後の課題とする．

= 考察

本稿で示せるのは，代表衛星モデルと複数熱・発熱条件のもとで，固定少数係数と計測可能な ΔT・太陽面・発熱フラグにより熱LOS主成分を 1〜2 桁低減し，粗捕捉時間を理想補正近傍まで短縮し得ることである．一方，飛行実証，全軌道・全被覆への一般化，熱/非熱の完全分離は主張しない．HOT/COLD や被覆を Level-2 に明示的に入れる拡張，配置が 90° 関係の場合の説明変数の整理は今後の課題である．

新規性の芯は「切片付き一次式」ではなく，(i) バス相対 LOS における太陽面−反対面 ΔT の主変数性，(ii) 感度 $a$ のケース横断共有の実証，(iii) ΔT 残差 DC の発熱フラグによる階層説明，(iv) 粗捕捉性能への接続，である@2021-turella-janus．

= 結論

時変熱LOSバイアスを階層 ΔT モデルで予測し，光通信粗捕捉の scan center に feedforward する枠組みを示した．TD/Femap 解析に基づき，共有感度 $a("sun")$ と発熱を含むケースバイアス $b$ の 10 係数モデルで，標準ケースの熱LOSを数 µrad 程度まで低減し，PAT シミュレーションで捕捉時間を大幅に短縮した．今後は HOT/被覆の Level-2 拡張，非熱誤差の現実的モデル化，および adaptive 層の定量評価を進める．

#bibliography(
  "bibliography.bib",
  title: [参考文献],
  style: "bibstyle.csl",
)
