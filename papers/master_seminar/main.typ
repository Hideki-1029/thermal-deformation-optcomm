#import "template.typ": *

#show: project.with(
  id: "",
  title-ja: "熱ひずみ予測と適応補正による光通信粗捕捉性能向上の検討",
  authors: (
    (
      name-ja: "船瀬・五十里研究室 修士2年　37-256364 高本英熙（2026/6/21）",
      affiliation-ja: "",
      presenting: true,
    ),
  ),
  abstract: [
    This study investigates an acquisition performance improvement method for free-space optical communication by predicting and compensating line-of-sight (LOS) bias induced by thermal deformation. In optical satellite communication, the beam divergence angle is small, and the success of the pointing, acquisition, and tracking process strongly depends on the initial pointing uncertainty. During coarse acquisition, optical feedback is not yet available, so the terminal must scan an uncertainty region determined by orbit prediction errors, attitude determination errors, alignment errors, and structural deformation. This work focuses on the thermal-deformation component, which can appear as a slowly varying LOS bias caused by orbital thermal cycles, attitude conditions, equipment heat dissipation, and operational modes. The proposed framework combines feedforward correction based on predicted thermal LOS bias with adaptive correction using residual pointing information obtained after acquisition. Thermal Desktop and structural analysis are considered for generating reference LOS-bias time series, while lightweight onboard prediction models such as Fourier, orbital-geometry, and thermal-sensor models are evaluated. A coarse-acquisition simulation will compare no correction, static bias correction, feedforward correction, and feedforward plus adaptive correction in terms of acquisition success rate, acquisition time, initial pointing error, and required scan area.
  ],
  n-columns: 2,
)

= 序論
== 研究背景
衛星光通信は，無線通信に比べて高いアンテナ利得と広い帯域を実現できるため，将来の小型・超小型衛星ミッションにおける大容量通信手段として期待されている@2017-kaushal-survey．一方で，光通信ではビーム拡がり角が小さいため，相手機を視野内に導入するPointing, Acquisition and Tracking（PAT）の成否が通信リンク成立を大きく左右する．特に粗捕捉段階では受信光を用いたフィードバックがまだ利用できないため，軌道予測誤差，姿勢決定誤差，アライメント誤差などを含む初期指向誤差を考慮して不確定領域を走査する必要がある@2023-riesing-tbird．

粗捕捉に要する時間は，走査すべき不確定領域の大きさに強く依存する．不確定領域の代表半径を $theta_U$ とすれば，単純化された走査モデルでは捕捉時間 $T_("acq")$ はおおよそ $theta_U^2$ に比例する．したがって，初期指向誤差のうち予測可能な成分を事前に補正できれば，必要なscan areaを縮小し，捕捉時間および再捕捉時間を低減できる可能性がある．

#figure(
  image("figure/image_modify_scan_area.png", width: 80%),
  caption: [熱ひずみ由来LOSバイアスをscan center補正に用いる概念図],
)<fig_scan_area>

== 熱ひずみによるLOSバイアス
本研究では，初期指向誤差の中でも，衛星構造および光学系の熱ひずみに起因するLine-of-Sight（LOS）バイアスに着目する．低軌道衛星では日照・食の繰返し，姿勢条件，機器発熱，運用モードの変化により温度場が時間変化する．この温度場の変化は構体や光学ベンチの変形を引き起こし，光学基準間の相対変位または相対角として通信光軸に現れる．精追尾段階では受信光フィードバックにより一部を補償できるが，粗捕捉開始時点ではLOSバイアスが初期指向誤差として残る．

#figure(
  image("figure/image_thermal_deformation_from_Shi.png", width: 88%),
  caption: [衛星構体の熱変形解析例@2023-shi-thermal],
)<fig_thermal_deformation_example>

熱変形由来のLOSバイアスは，光通信の粗捕捉問題に対して無視できないオーダーとなり得る．例えば，光学基準間の代表長さを $L$，熱変形による相対変位を $Delta x$ とすれば，微小角近似により

$ Delta theta_("LOS") approx (Delta x) / L $

と表せる．$L = 1$ m，$Delta x = 100$〜$200$ µm程度であれば，$Delta theta_("LOS")$ は $100$〜$200$ µrad程度となる．これは，小型衛星光通信で想定されるビーム拡がり角や捕捉センサ視野，姿勢決定由来のLOS誤差と同程度であり，粗捕捉のuncertainty budgetに対して有意な寄与を持つ．Shiらはレーザ通信機とスターセンサ間の熱変形がuncertainty regionおよびacquisition timeを増加させることを示しており@2023-shi-thermal，Badásらは衛星FSOC端末における熱・構造・光学の連成現象がpointing jitterや波面誤差を通じて通信性能に影響することを整理している@2024-badas．

== 関連研究と本研究の位置づけ
関連研究は大きく，熱ひずみ・opto-thermo-mechanical現象を整理する研究，熱変形に起因するLOS誤差を補正する研究，光通信における捕捉性能への影響を評価する研究に分けられる．これらはいずれも本研究の基盤となるが，熱変形由来LOSバイアスの予測を粗捕捉時のscan center補正に接続し，捕捉時間や必要scan areaの低減効果として評価する枠組みは十分に検討されていない．

- #text(weight: "bold")[熱ひずみ・opto-thermal現象の整理]：Badásらは，衛星FSOC端末における熱・構造・光学の連成現象が，pointing jitter，wavefront error，polarization変化などを通じて通信性能に影響することを整理している@2024-badas．ただし，熱ひずみ由来LOSバイアスを粗捕捉補正に用いる具体的手法は扱っていない．

- #text(weight: "bold")[LOS補正・熱変形補正]：HuらはGEOリモートセンサの熱変形LOS誤差を星観測とFourier級数で日周期モデル化し@2022-hu-thermal-motion，LiらはLEO光学ペイロードのLOS誤差を太陽・衛星・LOS幾何を用いて補正している@2025-li-thermal-los．一方で，これらは主にリモートセンシング・観測ペイロードを対象としており，光通信PATにおける粗捕捉時間やscan areaへの影響は主対象ではない．

- #text(weight: "bold")[光通信捕捉性能への影響評価]：Shiらは，レーザ通信機とスターセンサ間の熱変形がuncertainty regionとacquisition timeを増加させることを示し，共通基準構造や柔軟支持により光軸角変動を低減した@2023-shi-thermal．ただし，構造設計・熱設計による熱変形低減が中心であり，軌道上で予測したLOSバイアスをfeedforward / adaptive補正に用いる枠組みは扱っていない．

以上を踏まえ，本研究では熱変形そのものの低減だけでなく，残存する時間変動LOSバイアスを予測可能な低周波成分として扱う．そして，その予測値を粗捕捉時のscan center補正に用いることで，熱ひずみ補正を光通信の捕捉性能評価へ直接接続する．

= 提案手法
== 基本方針
本研究の目的は，熱ひずみによる時間変動LOSバイアスを予測し，粗捕捉時のscan centerを補正することで，不確定領域と捕捉時間を低減することである．従来の構造設計による熱変形低減は重要であるが，設計段階で全ての運用条件を吸収することは難しい．そこで本研究では，熱ひずみを単なる未知外乱ではなく，軌道位相・熱環境・運用モードから部分的に予測可能な低周波バイアスとして扱う．

なお，本研究では観測された指向残差から熱ひずみ成分のみを完全に分離することを目的とはしない．粗捕捉時の初期指向誤差には，軌道予測誤差，姿勢決定誤差，アライメント誤差，相手機側誤差などが同時に含まれるためである．本研究の主眼は，これらの誤差が共存する条件下でも，熱構造解析や温度・軌道情報から得られる熱ひずみ由来LOSバイアスの事前予測を用いることで，scan center誤差および必要scan areaをどの程度低減できるかを評価する点にある．

提案する補正は，事前予測に基づくfeedforward correctionと，観測残差に基づくadaptive correctionの二層で構成する．まず，Thermal Desktopにより軌道熱環境と衛星温度場を解析し，Femap / Nastran等の構造解析により各時刻の熱変形を求める．得られた光学基準間の相対変位・相対角をLOSバイアス時系列に変換し，補正モデル評価用の高精度参照データとする．次に，この参照時系列を教師データとして，軌道上で扱いやすい軽量なLOSバイアス予測モデルを構築する．

== Feedforward補正
Feedforward補正では，予測されたLOSバイアスを粗捕捉開始時のscan center指令に加える．名目指向方向を $theta_("nom")(t)$，予測LOSバイアスを $hat(Delta theta)_("LOS")(t)$ とすると，scan center指令は

$ theta_("scan")(t) = theta_("nom")(t) + u_("FF")(t), quad u_("FF")(t) = -hat(Delta theta)_("LOS")(t) $

と表される．この補正により，熱ひずみによってずれた実際の相手方向にscan centerを近づけ，残差指向誤差 $e_("scan")$ を低減する．

軽量モデルの候補としては，平均LOSバイアスを用いるstatic bias model，軌道位相に対するFourier model，太陽・衛星・LOS幾何を入力とするorbital geometry model，温度センサ値を用いるthermal sensor modelなどが考えられる．GEOリモートセンサの熱変形LOS誤差に対しては星観測とFourier級数を用いた補正が報告されている@2022-hu-thermal-motion．一方，LEOでは日照条件が不安定であり，Liらは軌道上の星観測データに基づく機械学習モデルで熱変形LOS誤差を補正している@2025-li-thermal-los．本研究では，これらのLOS補正の考え方を光通信粗捕捉のscan center補正に接続する．

== Adaptive補正
Feedforward補正は初期誤差を低減できるが，熱構造解析モデル，軽量モデル，実際の軌道上熱環境には不確かさが残る．そこで，捕捉後に得られるPATセンサ出力，Quadrant Detector（QD），Focal Plane Module（FPM），受信光強度，姿勢センサ情報などを用いて，予測LOSバイアスと観測された指向誤差の残差を推定する．

ただし，観測残差には熱ひずみ以外にも姿勢決定誤差，軌道予測誤差，アライメント残差，機械振動などが含まれる．そのためadaptive correctionでは，残差のうち熱状態や軌道位相と相関する低周波成分を抽出し，補正モデルに取り込むことを目指す．具体的には，捕捉イベントごとに得られる残差を蓄積し，軌道位相，日照・食状態，温度センサ値，運用モードに対するモデルパラメータを逐次更新する．これにより，打上げ後の構造状態変化や長期的な熱特性変化に対するロバスト性を高める．

#figure(
  image("figure/concept_feedforward_adaptive_correctoion.png", width: 88%),
  caption: [Feedforward補正とadaptive補正を組み合わせた二層補正フレームワーク],
)<fig_ff_adaptive>

= 評価計画
== シミュレーション構成
提案手法の有効性は，熱ひずみ由来LOSバイアスを含む粗捕捉シミュレーションにより評価する．評価対象は，補正なし，static bias correction，feedforward correction，feedforward + adaptive correctionの4ケースとする．補正なしは熱ひずみ由来バイアスをそのまま初期指向誤差として扱う基準ケースであり，static bias correctionは時間平均的なLOSオフセットのみを補正する比較対象である．feedforward correctionでは軌道位相や熱状態に応じた予測LOSバイアスを用い，feedforward + adaptive correctionでは観測残差に基づくモデル更新を加える．

評価指標は，捕捉成功率，平均捕捉時間，初期指向誤差，必要scan areaとする．粗捕捉における探索コストは不確定領域の面積に対応するため，補正後残差の分散または上限値を用いて必要scan areaを評価する．評価では，軌道予測誤差や姿勢決定誤差を外乱として残した条件で各補正ケースを比較し，熱ひずみ補正が全誤差を除去するのではなく，予測可能な熱由来成分を低減する効果として評価する．

#figure(
  image("figure/thermal_los_bias_from_mock_analysis.png", width: 100%),
  caption: [Mock thermal LOS biasとfeedforward推定値],
)<fig_mock_los_bias>

#figure(
  image("figure/coarse_acq_time_from_mock_analysis.png", width: 100%),
  caption: [Mock thermal LOS biasを用いた粗捕捉時間の予備解析],
)<fig_mock_acq_time>

予備的なmock thermal LOS biasを用いた数値実験では，補正なしに対してfeedforward補正を加えることで，平均初期誤差が $93.9$ µradから $49.5$ µradに低下し，平均捕捉時間が $2.43$ sから $0.74$ sに低下する傾向が確認されている．今後は，この仮想モデルをThermal Desktop / Femapに基づく参照時系列へ置き換え，モデル化誤差を含めた評価を行う．

#figure(
  table(
    columns: (1.5fr, 2.2fr, 2.0fr),
    align: left,
    [Case], [補正内容], [評価目的],
    [No correction], [熱ひずみ由来LOSバイアスを未補正], [基準性能の把握],
    [Static bias], [固定LOSオフセットのみ補正], [定常補正との比較],
    [Feedforward], [予測LOSバイアスでscan centerを補正], [事前熱モデルの効果評価],
    [FF+Adaptive], [観測残差に基づき補正モデルを更新], [モデル誤差へのロバスト性評価],
  ),
  caption: [比較対象と評価目的],
)<tab_cases>

== 期待される成果と課題
本研究の貢献は，熱ひずみ補正をLOS誤差低減だけでなく，光通信PATの粗捕捉性能向上へ直接接続する点にある．熱ひずみは従来，構造設計や熱設計の対象として扱われることが多かったが，本研究では時間変動するLOSバイアスとしてモデル化し，scan center補正に利用する．これにより，粗捕捉開始時の不確定領域を縮小し，捕捉時間・再捕捉時間を短縮できる可能性がある．

今後の課題は三つある．第一に，Thermal Desktop / Femap解析により，代表的な衛星構造と軌道条件に対するLOSバイアス参照時系列を作成する必要がある．第二に，Fourier model，orbital geometry model，thermal sensor modelなどの軽量補正モデルを比較し，軌道上実装に適した入力とモデル次数を決定する必要がある．第三に，PAT・姿勢・熱センサ情報から熱状態と相関する低周波残差を抽出する手法を設計する必要がある．特に，熱ひずみ以外の誤差源を誤ってモデルに取り込むと補正が不安定化するため，残差分解とモデル更新則の設計が重要である．

= 結論
本稿では，熱ひずみによる時間変動LOSバイアスが光通信粗捕捉に与える影響を整理し，その予測値をscan center補正に用いるfeedforward / adaptive補正フレームワークを提案した．熱変形に起因するLOSバイアスは，ビーム拡がり角や捕捉センサ視野と同程度の数十〜数百 µradとなり得るため，粗捕捉時のuncertainty regionに無視できない寄与を持つ．今後は，熱構造解析に基づく高精度参照時系列を作成し，補正なし，static，feedforward，feedforward + adaptiveの各ケースを粗捕捉シミュレーションで比較することで，提案手法が捕捉成功率，捕捉時間，必要scan areaに与える効果を定量評価する．

#bibliography(
  "bibliography.bib",
  title: [参考文献],
  style: "bibstyle.csl",
)
