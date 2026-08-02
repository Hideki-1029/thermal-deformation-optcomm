# 260724 JANUS STOP Analysis Review

- 作成: 2026-07-24
- 目的: 2026/7/24 最近見つけたJANUSのSTOP解析に関する論文について、reviewを行う。in Barcelonaへの飛行機
- 主な入力:
  - `docs/literature/Structural-Thermal-Optical-Performance (STOP) analysis for the prediction of the Line of Sight stability of JANUS camera on board JUICE ESA mission.pdf`

---

## 1. 論文読み -Turella, STOP analysis for JANUS -

### Abstract

- JANUSのOptical Head UnitのSTOP解析をした
  - ESATAN-TMS で熱解析→FEMモデル構築→NASTRANでひずみ解析
- The resulting LoS and the dominant OHU temperature gradients are finally entangled with a proportionality 
  - 最終的には、LOSと支配的な(dominnantな)OHUの温度勾配の間に比例関係があることがわかった
  - バイアス成分は入れているのか気になる ★AI
    > **AIコメント:** この論文のモデルには、明示的なバイアス項（切片）は入っていない。5.4節の式(3)は
    >
    > LoS \approx \alpha \Delta T_{\mathrm{WALLS}} \pm u_{LoS}
    >
    > であり、著者は「壁間温度差がゼロなら関数は原点を通る」と説明している。考え方としては、地上の一様なクリーンルーム温度環境で光学アライメントを行い、その状態を公称 LoS=0 と定義したうえで、軌道上で生じる公称状態からの変化だけを \alpha\Delta T_{\mathrm{WALLS}} で表している。
    >
    > したがって、製造誤差や初期アライメント誤差による定常オフセットが物理的に存在しないという意味ではなく、それらを校正後のLoS基準に吸収していると考えるのが正確。なお、\pm u_{LoS} はバイアスではなく、熱モデル・構造モデルに由来する標準不確かさである。
    >
    > AKEは AKE=LoS_{\mathrm{sci}}-LoS_{\mathrm{calib}} という差分なので、校正時と観測時に共通する一定バイアスは相殺される。ただし、この論文は自由切片を持つ回帰結果や残差を示していないため、「解析結果から切片がゼロと実証された」というより、物理的・定義的に原点通過を課したモデルと読むべき。



### 1. Introduction

- JUICEミッションの目的
  - 惑星の構成と生命の発現に必要な条件は何か？
- Jupyterの衛星（Ganymede, Callisto and Europa）同士の様子を比較（Ganymede）したり、木星本体とのinteractionを見ることで、その謎に迫る
- Remote Sensing用の機械としてJANUS Cameraが載っている



### 2. JANUS

- JANUSカメラは可視光域の狭視野カメラ
- JANUSカメラの構成
  - Optical Head (OHU), mounted on the S/C(Space Craft) Optical Bench
  - Proximity Electronics (PEU), located close to OHU on S/C Optical Bench
  - Main Electronics (MEU), located in the S/C vault
- JANUSカメラで見たい物
  - Galilean 氷衛星の調査
    - 氷の表層の下には水がある可能性がある
    - ハビタブルの条件がわかるかも
  - 他にも、木星本体や衛星を観測する可能性はある



#### 2.1 Jovian atmosphere

- Jovian atmosphereを調査することで、放射線と水生成のダイナミクスの関係がわかるかも
- 大気の中でも上位3層を観測
- 大気の構造だけでなく、動きも観測することで、風のベクトル場を知る



#### 2.3 Ganymede libration

- Galilean氷衛星はoceanの上の氷の表層で特徴づけられる
- libratonってなに？★
  - この文の意味がよくわからなかった
  - Librations with different periodicities but similar amplitudes are linked in different ways to the body internal structure.
    > **AIコメント:** librationは日本語で「秤動（ひょうどう）」。Ganymedeは木星に対してほぼ同期回転しており、基本的には同じ面を木星へ向けているが、その平均的な姿勢の周りで向きが小さく周期的に揺れる。イメージとしては、同期回転している天体がわずかに「首を振る」運動であり、軌道上の並進運動や自転そのものとは異なる。
    >
    > 木星から受ける周期的な潮汐トルクに対する応答は、氷殻の厚さ・剛性、地下海による氷殻の力学的な分離、内部の密度分布や慣性モーメントなどによって変わる。そのため、秤動の振幅・位相・周期成分を測ることで内部構造を推定できる。引用文は、「振幅が同程度でも、周期の異なる秤動成分は内部構造に対して異なる感度を持つ」という意味。
    >
    > JANUSは、異なる時刻に撮影したGanymede表面の地形位置を比較してこの小さな姿勢変化を測る。そのため、カメラ自身のLoS変化がGanymedeの秤動として混入しないよう、厳しいLoS knowledge／AKE要求が課されている。
    >
    > なお、最初の文は「ガリレオ氷衛星では、地下海の上を氷殻が覆っている可能性があり、天体内部ではそれぞれ異なる程度の分化や内部過程が存在する」くらいの意味。



### 3. Pointing Stability Requirements



#### 3.1 Line of Singht

- OHUのLOSの定義：
  - 外に出ていくビームの角度
  - そしてそれはdetectorのcenter pixelに一致する（はず。ノミナルでは光軸に一致）
- LOSの維持をPoiniting Stabilityと定義
- LOSのcontrolは通常、宇宙機の姿勢系によって行う ~ Body Pointing
  - steller fieldを取るか、single star observationをするか
- ただし、科学撮像ミッションの際には、"none direct monitoring"が取り除かれる可能性もある
  - "none direct monitoring"はつまり通常の姿勢系によるcontrolを意味する
  - というか、撮像の時以外は、特にOHUを動かさないという意味だろう
- なので、軌道の間で熱ひずみによるミスアライメントを小さくする光学設計が重要
- stabilityを得るために必要なこと
  - 正確な材質の選定
  - 特殊な構造コンポのgeometry ← ここのgeometryってどういう意味？★
    > **AIコメント:** ここでのgeometryは、構造部品の具体的な「形状・寸法・配置」を意味する。例えば、壁や鏡筒の厚さ・長さ・断面形状、リブの位置、Optical WallとBaffle Wallの配置、Bipodの長さ・角度・取付位置、支持点・固定点の位置、部材間の接続形状など。
    >
    > 同じ材料でも、これらのgeometryによって剛性や熱膨張時の曲がり方が変わる。この論文ではBaffle WallとOptical Wallの温度差によるOHU全体の曲げとOMSの傾きがLoS変化の支配要因なので、構造部品のgeometryがLoS安定性に直接影響する。
    >
    > 原文の *the specific structural component geometry* は、「特殊な構造コンポーネント」よりも「LoS安定性を考慮した構造部品の適切な形状・寸法・配置」または「用途固有の構造形状」と読むのが自然。
  - 正確なactive thermal control



#### 3.2 Attitude Knowledge Error

- "The instantaneous knowledge of Pointing Error at any time given"
  - ※ Pointing Error = 実際の姿勢系のAttitudeとtargetの方を向くのに必要な姿勢の差分）
  - これを、"Absolute Knowledge Error"=AKE と呼ぶ。   
  - "instantaneous"って逐次的みたいな意味？ ★
    > **AIコメント:** ここでの *instantaneous* は「逐次的」ではなく、「任意のある瞬間における」「その時点での」という意味。時間平均した誤差や、ある観測期間全体の安定度ではなく、各画像を取得した瞬間の指向方向をどの程度正確に把握できているかを表す。
    >
    > したがって、この一文は「任意の時刻における実際の指向と目標指向との差を、どの程度正確に知っているかがAKE」という趣旨。一般にAKEは指向誤差そのものというより、真の指向に対する推定指向のknowledge errorを指すので、「瞬時指向誤差の推定精度」と捉えるのがよい。
  - AKEはまさに俺の論文の中でのLOS誤差かも
- AKEの成因
  - 姿勢系（の誤差）
  - 構造的ひずみ（による誤差）
  - （あとはJANUSのtargetごとの指向のvariation）
- Fig 1. The LoS reference is determined during star calibration
  - まずSTTでcalibrationしてLOS referenceを作る
  - そのあとS/CのmanouverやGanymedeの観測が入ると、AKEが上下する
- iFOV(= instantaneous FOV)ってなに？★
  - 一旦FoVだと思っておこう
  - もしかして1pixelあたりのFoVをFoVと言っている？
    > **AIコメント:** この論文の要求表では、iFOVは明確に「1 pixelが見込む角度」であり、15 μrad/pixel。高度500 kmなら 500000 \times 15\times10^{-6}=7.5 mとなるので、地上画素寸法7.5 m/pixelに対応する。
    >
    > FOVは検出器全体が一度に写す範囲（JANUSでは1.72°×1.29°）、iFOVは通常、1画素または1つの空間サンプルが張る微小角を指す。ただし本文の「iFoVに背景星などの絶対基準がない場合」という箇所では、「その瞬間に取得した画像内の視野」くらいの広い意味でも使われており、用語の使い方は少し緩い。



#### 3.3 Requirements

- 今回のミッションを整理した上で、OHUに対する要求は以下のようになった
  - iFOV 15urad / pixel（= 7.5m/pixel at GCO500） GCO500は高度500kmのどこかの軌道
  - Ground FOV 1.72×1.29deg
  - Spectral range 340-1080nm
  - Optical MTF at Nyquist frequency >= 0.15 ← MTF初見なので、あとで意味確認★
    > **AIコメント:** MTF（Modulation Transfer Function）は、被写体が持つ明暗コントラストを、光学系が空間周波数ごとにどれだけ像へ伝えられるかを表す。MTF=1ならコントラストを完全に維持し、MTF=0ならその細かさの模様を区別できない。
    >
    > Nyquist frequencyは、画素ピッチ p の検出器がエイリアシングなしに標本化できる上限の空間周波数 1/(2p)。したがって「Optical MTF at Nyquist frequency ≥ 0.15」は、検出器で表現可能な最も細かい模様に対しても、光学像が元のコントラストの15%以上を残すという要求である。MTFは解像度と像の鮮明さを評価する指標で、LoSは像全体の位置・方向、MTFは像のぼけやコントラストを表す点が異なる。
  - Pointing Accuracy @ GCO500　8urad
  - Pointing Accuracy @ GCO5000 15urad
- 一番大事なのは、観測中のPointing Accuracyは15uradと、光通信またはそれ以上の指向が求められるということ



### 4. JANUS Optical HEAT UNIT

- JANUS光学系の最終設計を決める上で2つの大きなトレードオフがあった
  - "Three Mirror Anastigmatic" versus "Ritchey-Chrétien optical layouts"
    - "Three Mirror Anastigmatic"→結果、Rithey..の方を修正したa catadioptric telescopeになる
    - よくわからんが、convergent beamになる
  - Invar versus Aluminum alloy and thermal control strategy of the mechanical structure
    - Invarはアルミではない、何かの材質だろう
    - Invarの方がCTE（=thermal expansion coefficient, 熱膨張係数）が低く有利
    - また、single heat control loopを構造に適用する事が検討された
- 結果的に、"Ritchey-Chrétien optical layouts" + Invar36 のセットが採用された
- OHUのコンポーネント(むっちゃ略したがっている)
  - Filter Wheel Mechanism
    - アルミ材質、黒色塗装
    - モーター動かすためのFiler？なにこれ？★
      > **AIコメント:** Filterはモーターを動かすための部品ではない。Filter Wheel Mechanismは、13枚の広帯域・狭帯域光学フィルターを円盤状のホイールに搭載し、モーターでホイールを回して、観測したい波長に対応する1枚を光路へ切り替える機構。フィルターによって、表面組成や大気現象など観測対象に応じた波長帯だけを検出器へ通す。
  - Focal Plane Modeule
    - detectorを守るチタン部材とwindowを守る混合シリカ材で構成
  - Cover Module
    - OHUの望遠鏡を守る壁。デブリや太陽光、分子の侵入を防ぐ
  - Opto-Mechanical Structure
    - Telescope Module
      - Invar製。主鏡副鏡（ハイパーボラ）、3つのcorrector鏡
      - 10th order aspheric coefficient→光学倍率10倍？ 正確な情報★
        > **AIコメント:** 光学倍率10倍という意味ではない。非球面鏡の表面形状を数式で表すとき、基準となる球面・円錐曲面に r^4,r^6,r^8,r^{10} などの補正項を加える。この *10th order aspheric coefficient* は、半径方向座標の10次までの非球面係数を使って鏡面形状を規定している、という意味。
        >
        > これらの係数で球面収差などを補正する。論文だけではZemax上で使用した具体的な面形式や各係数値までは示されていないため、「10次の非球面形状を持つ」とまでは言えるが、形状を再現できる情報はない。
    - Bipods
      - Isostatic, flexible mount in Titanium
    - Baffles
      - アルミ製で黒色塗装のデかtube。
      - 迷光対策（to limit 1st order straylight）
    - Connecting Wall Structure
      - BaffleはBaffle wallに繋げられている
    - MLI
      - OHU全体はMLIで覆われている！！
      - OHUの温度場の変化を最小限にとどめるため。
- JANUS OHUの概要
  - 重量：12kg
  - 体積：60x35x25cm 
    - 俺が今回考えている衛星筐体よりはやはり小さい（m級より小さい）
  - 主鏡の径：12cm
  - 副鏡とdetectotの距離：18cm
- 設計のiteretionの回し方
  - 早めにPointing Stabilityと予測されるModulation Transfer Function (MTF)の質を高める、保証する
  - 設計の流れの図見やすかった。俺の論文も最終的に衛星設計的な方向に結論をもっていきたいなら、こういう図を作ると意図が明確に読者に伝わりそう



### 5. STOP ANALYSIS



#### 5.1. Methodology

- Methodologyって何だっけ？★
  > **AIコメント:** 正しくは *Methodology* で、「方法論」「解析方法」「一連の解析手順」という意味。この節では一般論としての研究方法というより、Thermal → Thermo-Elastic → Optical → Performance AnalysisというSTOP解析のワークフローを示している。なお、ノート見出しの *Methology* はスペルミスで、論文本文は *Methodology* になっている。
- 軌道におけるAKEの予測（prediction）は、"a sequence of multi-disciplinary analysis"で決める
  - このワード、俺の論文で解析の流れ紹介するときも使えそう

ここまでOK

- STOP解析の流れ
  - Thermal Analysis
    - ESATAN-TMSを用いる
    - 温度場の勾配、"ambient to orbital"(これなに★)の観点から、最悪ケースを複数選んだ。
      > **AIコメント:** 原文の *temperature gradient and ambient-to-orbital temperature* は表現がやや不自然だが、2種類の熱的な厳しさを指していると読める。1つはOHU内部の場所ごとの温度差（temperature gradient）、もう1つは地上の室温環境から軌道上のHot/Cold状態へ移ったときの、機器全体の絶対温度レベルまたは温度変化量（ambient-to-orbital temperature）。
      >
      > つまり、部材間の温度差が大きくて曲げを生むケースだけでなく、機器全体が地上組立時より大きく膨張・収縮するケースも含めてworst caseを選び、その温度分布をNASTRANへ渡している。
    - 温度場を出力
  - Thermo-Elastic Analysis
    - NASTRANを用いる
    - FEMAPはCADの名前だから、Solverの名前を書くのが適切ということなのか
    - CTEを適切に設定したOHU Fintite Elementモデル（有限要素モデル）に温度場を適用する
    - OHUのすべてのOpticsとDetectorの重心における、TRANSLATION（並行移動）とTILT=Rotation（回転）を出力する
  - Optical Analysis 
    - Zemaxを用いる
    - ここまでやったのか偉い。
    - NASTRANから出したすべてのコンポ要素のtranslation, rotationを入力としてZEMAX光学モデルに導入
    - 出力として、OHUのLOSのvariationと、Degrading of MTF ← Degrade of MTFってなに？★
      > **AIコメント:** 熱変形によって鏡・レンズ・検出器が並進・回転すると、焦点ずれや偏心、傾きによる収差が増え、像のコントラスト伝達性能であるMTFが公称状態より低下する。この低下が *degradation of MTF*。
      >
      > Zemaxでは、NASTRANから得た各光学要素の変位・傾きを光学モデルへ与え、変形後のMTFを再計算し、公称MTFとの差や要求値0.15を下回らないかを評価する。LoS variationが像全体の位置ずれ・指向ずれを表すのに対し、MTF degradationは像のぼけ・コントラスト低下を表す。
  - Performance Analysis
    - OHUの温度場の関数として、LOS and AKE uncertainty が出力される。



#### 5.2 LOS RESULT

- Table 4. OHU LOS worst0case values
  - GCO500
    - Cold：44urad
    - Hot：34urad
  - GCO5000
    - Cold:44urad
    - Hot:32urad
- Hotの方が若干大きい
- STOP解析において、具体的にLOSをどう計算したかの記述がない のちほどAIにも確認★
  > **AIコメント:** 大まかな計算経路は記載されている。ESATAN-TMSの温度分布をNASTRANへ入力し、各鏡・レンズ・フィルター・検出器の重心位置における並進と傾きを出力し、それらをZemax光学モデルへ与える。Zemaxでは、中央画素を起点とする出射光の角度を、地上の一様温度・公称組立状態の方向と比較してLoS variationを求めたと考えられる。その後、FEMで得たOMS全体のtiltとZemaxのLoSがほぼ一致することから、式(1)の LoS\approx TILT_{\mathrm{OMS}} を得ている。
  >
  > ただし、Zemaxでどのray/operandをLoSとして評価したか、座標変換をどう行ったか、各光学面の変位をどう適用したかは書かれていない。したがって、解析の概略は分かるが、この論文だけでLoS計算を完全に再現することはできない。
- あと俺の研究との違いとして、角度誤差のオーダーが全然違うかも



#### 5.3 LoS and AKE main contributer - Walls gradient

- おそらくこの章が俺にとっても、この論文にとっても重要な章
- 様々な解析のステップの結果を比較したところ、OMS（=Optical Mechanical Structure）の回転要素が全体のLOS誤差の大部分を占めていた。
  - 気づき：実験的に（帰納的に）気づいた事実は、こうやって言えばいいのか。→「様々な解析のステップの結果を比較したところ、、、」
  - 逆にその差は無視できるほどに小さい。
  - つまり、ほぼ同じで、"LOS ~ TILT_OMS"
- ここから言えることは、Optical components(鏡、レンズ、detector)の並進移動や回転が何であっても、結局メインの効果は、OHU全体のGlobalな回転になるということ。
  - そしてその回転を引き起こすのは、Baffle wallとOptical WallのThermal gradient
- したがって、AKEの貢献を実質0（つまり、LOS_calibration = LOS_sceience）にしたければ、温度勾配の変化を時刻軸でみて0にすればいい
  - コンセプトとしては、ΔT=0にするというより、∂ΔT/∂t = 0にすればいい
    - これは、STTによるキャリブレーションを事前に行うから、ΔTは存在していても良くて、それが変化するのが嫌だ、ということなのか？ 後で確認★
      > **AIコメント:** その理解で合っている。星野観測でLoSを校正した時点に壁間温度差 \Delta T_{\mathrm{calib}} が存在していても、それによる一定のLoSオフセットは校正値に含まれる。科学観測時にも同じ温度差が維持されれば、
      >
      > AKE\approx\alpha(\Delta T_{\mathrm{sci}}-\Delta T_{\mathrm{calib}})=0
      >
      > となる。必要なのは必ずしも \Delta T=0 ではなく、校正から科学観測まで \Delta T を変化させないこと。
      >
      > ただし厳密には、論文の1入力・静的線形モデルが成り立つ範囲での議論。温度分布の形が変わる、別の部位の温度勾配が効く、熱的ヒステリシスや時間遅れがある場合には、同じ2点間温度差でもLoSが完全には一致しない可能性がある。
  - "conservation of the Walls gradient"
  - 時間幅としては、キャリブレーションしてから観測開始までの間の時間（観測しない時間は含めない）
    - これは非常に学びになる。ΔTの変化を一定時間抑えればよい、という明確かつ達成可能そうな目標になっている
- ΔTがCold caseとHot Caseで大きく変わることを防ぐため、
  - ad-hoc location of active thermal control was studied (homogeneous distribution of heaters in the middle section of the CWS).
  - "ad-hoc"ってなに？addってこと？★
    > **AIコメント:** *ad hoc* はaddとは無関係なラテン語由来の表現で、「この特定の目的のために」「この問題に合わせて特別に設けた」という意味。ここでは、壁間温度差の変動を抑えるという目的に合わせて、CWS中央部にヒーターを均等配置する専用の配置を検討した、ということ。
    >
    > 「常にヒーターをONにする」とまでは書かれておらず、能動熱制御ループによって必要に応じて加熱し、Cold/Hot条件間でも温度分布と壁間温度差を安定化させる設計と読むのが適切。
  - つまり、あえてactiveにヒーターをONにして、壁間温度差ΔTをcontrolしにいくということか！
  - これは結構賢いな。俺の研究で取り入れるのもあり得そう。



#### 5.4. LoS Prediction

- After having deduced the physical relation between LoS and Walls gradient
  - "deduce"- 推定する。こうやって帰納的に温度とLOSの関係を得たことを述べればいいのか
- LOS = α ΔT_walls +- u_LOS
  - 本関数の切片が0である理由は、関数の基準をnull Walls gradientにとっているから。
  - 地上のクリーンルームで一度校正をしたら、その後は基本的にLOSは0である。
  - ここはLOSの定義の話をしているのか、現象の話をしているのか、気になる。あとでAIに確認★
    > **AIコメント:** 主としてLoS変化量の基準・定義の話であり、一部に物理モデル上の仮定が含まれている。地上の一様温度で光学アライメントを完了した状態を「公称LoS=0」と定義しているので、\Delta T_{\mathrm{WALLS}}=0 で原点を通ること自体は座標の取り方による。
    >
    > 一方、「そこからのLoS変化が壁間温度差に比例する」という部分はSTOP解析から得た物理的・経験的関係。つまり、切片ゼロは校正基準、傾き \alpha は熱弾性変形という現象を表す。ただし、自由切片を含む回帰との比較がないため、壁間温度差以外の影響による残留バイアスが物理的にゼロと証明されたわけではない。
- ここで、STOP解析の過程そのものがLOSの計算結果に与える影響を議論
- 不確定要素としては3つ挙げられる
  - OHU design geometry and material properties
    - → これは無視できる。the OHU design is consolidated（プロトフライトモデルだから設計はある程度固まっていて変更の可能性が少ない）
  - 解析の境界条件
    - → これも変わりにくい。コンダクタンス・熱光学特性や、内部構造配置、軌道、ミッションタイムライン等はもう確定しておりあまり変わらない
    - ここは俺の研究では差分になりそう。この研究は、軌道や内部構造配置を一般化して式をモデル化する研究ではない。
      - やはりその意味でも、俺の研究ではもう少しケースを増やすといいのかもなあ、、。
  - モデリングとconstraints(制約条件)の推定
    - → ここだけがまだ不確定
    - このうち、光学系のモデリングについては、先に記述した「光学系内部でのLOS誤差への寄与は極めて小さい」という事から無視できる
    - したがって、次の2項がuncertain。
      - 非常にロジカルな進行。やはりMECEさを出すのは大事だね、
- 結局不確定な要素：
  - Thermal modeling affects the Walls Temperature gradient value.
    - 熱モデルが壁の温度差ΔTに影響すること
  - Structural (Finite Element) modeling affects the factor α.
    - 構造モデルが係数αに影響すること
- ここで、かなり重要な仮説：
  - *αとΔT_WALLの不確定性はindependentである。*
    - 実際、
      - 熱コンダクタンスの設定→温度場には影響するが、displacement（熱ひずみ）には影響しない 
        - ← これは本当？？？コンダクタンス変えたらひずみは変わる気がするけど、αには影響ないってことなのか？怪しい。熱解析→構造解析の順だから影響はありそう。 解析等で要確認★
          > **AIコメント:** 疑問はもっともで、論文の「conductivity affects the temperature distribution but not the displacement」という書き方は、連成した解析全体について文字どおり読めば不正確。熱コンダクタンスを変えると温度分布が変わり、その温度分布をFEMへ入力すれば、最終的な変位も一般には変わる。
          >
          > 著者が言いたいのは、\Delta T_{\mathrm{WALLS}} と、単位温度差あたりの構造感度 \alpha=LoS/\Delta T_{\mathrm{WALLS}} の不確かさを分けて扱うということ。構造形状・拘束・CTEを固定し、同じ壁間温度差と同じ温度分布形状を与えるなら、熱コンダクタンスはFEMの変換係数 \alpha に直接は入らない。一方、CTEはその温度場に対する変位感度 \alpha を変えるが、熱解析の温度分布には直接入らない。
          >
          > したがって独立性は、熱モデルの不確かさを \Delta T のみに、構造モデルの不確かさを \alpha のみに集約できるという条件付きの近似。コンダクタンス変更によって温度分布の形まで変わる場合、同じ2点間 \Delta T でも変形モードが変わり、見かけの \alpha が変化し得る。また材料変更など共通パラメータがあれば相関も生じる。この独立性は一般則ではなく、本モデルを一次元化するための工学的仮定として扱うべき。
      - 一方で、CTE（熱膨張係数）はFEMのdisplacement（熱ひずみ）には影響するが、温度場には影響しない
        - ← まあこれは合っていそう。解析の順序が、熱解析→構造解析になるからね。
  - 唯一、材料の変更はΔTにもαにも影響するが、今回は設計が固まっていて変更可能性はないので、考慮しなくてよい
- よって、αとΔTは独立のため、以下のような式を立てれる。
  - 式（４）：uLOS = （（LOSをαで偏微分xu_α）^2 + (LOSをΔTで偏微分xu_ΔT)^2）^0.5
- LOS = α ΔT +- u_LOSの式から偏微分係数が出せて、
  - u_LOS = ΔT α √u_α_per ^2 + u_T_per^2



#### 5.5. AKE prediction

- AKE = LOS_sci - LOS_calib に対しても、上のLOSの式と同様の議論ができて、不確定性を以下のように計算できる。
  - 式（5）



### 6. RESULTS

- The proportional factor is obtained with best linear fit of the LoS STOP analysis results.
  - 比例要素が最もSTOP解析のLOSにフィットする。
- ECSS methodを用いて、ΔT_wallのuncertaintyを決定：13％ ← ECSS methodが何か気になる ★
  > **AIコメント:** この論文がいうECSS methodは、熱モデルの入力パラメータを所定の不確かさ幅で変化させ、出力である壁間温度差の感度を調べるパラメータ感度解析。本文では、熱コンダクタンス、熱光学特性、ヒーター電力などを既定の割合だけ変動させ、その影響を合成して u_{\Delta T}=13 としている。
  >
  > したがって「ECSSを使えば常に13%になる」のではなく、JANUSの熱モデル、各入力の許容差、感度係数を用いた結果が13%。論文は各パラメータの変動幅、確率分布、感度係数、合成表を掲載していないため、13%を本文だけから再現することはできない。また本文の引用番号は[10]だが、参考文献[10]はOSIRIS機構の論文であり、ECSS規格そのものは[9]なので、引用の対応はやや不明瞭。
- Engeeneering heritageを用いてαのuncertaintyを決定：20％
- uncertaintyは事前に決めたのだろう。これで不確定要素の差分であるu_LOSが決まれば、Fig 7,8のようにリアルなSTOP解析値に対して、軽量モデルのplotを与えられる
  - とはいえ、結果を見ると、ほとんどu_LOS, u_AKEが無くてもαΔTだけで十分説明できているような気もする。
- AKEはそのものの値とu_AKEの値がともに一桁urad程度。u_AKEの方がAKEの本値よりも大きいケースもあるけどこれはそれでいいのかな？★
  > **AIコメント:** 問題ない。AKEはモデルが予測した符号付きの公称値、u_{AKE} はその推定値の1σ標準不確かさなので、真値がゼロ付近にある場合や不確かさが大きい場合には u_{AKE}>|AKE| になり得る。例えば -4\pm7 μradは、「推定中心は−4 μradだが、1σの範囲は概ね−11～+3 μrad」であり、ゼロも十分あり得るという意味。
  >
  > ただし要求適合性を判定するときは公称値だけを15 μradと比較せず、要求で定められた信頼水準に合わせて |AKE|+ku_{AKE} などの上限を評価する必要がある。この論文のTable 5は1σ表示なので、例えばGCO5000 Hotの -12\pm7 μradは、公称値だけなら15 μrad以内でも、1σ側の絶対値上限は19 μradとなる。論文はこの点の要求マージン判定を詳しく議論していない。
- *ここで気になるのは、そもそもなぜ俺の研究と違って、この研究ではLOS=α ΔTの立式に対してほぼバイアスが出ないのか、ということ。*
  - → はじめに地上で校正して、LOSが0になるという想定だから？なんでバイアス成分が出てこなかったのか、非常に気になる。要確認★
    > **AIコメント:** その理解が中心的な理由。ここでのLoSは絶対的な機械角ではなく、地上の一様温度・光学アライメント状態をゼロとした変化量なので、定常的な組立・アライメントバイアスは基準値へ吸収される。さらにAKEでは科学観測時と校正時の差を取るため、両時刻に共通するバイアスは相殺される。
    >
    > ただし、解析データが自然にほぼゼロ切片だったと実証しているわけではない。著者は原点通過を物理的に課して比例モデルを構成しており、自由切片を含む回帰結果を示していない。あなたの研究で絶対角度、未校正の変位、または基準状態にも残る非対称変形を目的変数にしているなら、切片が現れるのは自然であり、両研究のバイアスは同じ定義で比較する必要がある。

RESULTの章は意外と淡泊に終わった。

### 7. Conclusion

- JANUS OHUは、木星とその氷衛星を調査するための高画像質カメラ
- 軌道において、熱環境が変わる中で、LOSの変化が少なくなるように設計されている
- 観測中は星座等を使ったcalibrationができない
- 指向誤差の知識とuncertaintyを復活させるため、STOP解析を実施し、OHUの光構造における温度勾配とLOSの間に比例関係を見出した
- 成功を収めたSTOP解析は、OHUのハードウェアの向上を促した → 2つの温度センサをバッフル壁と光学壁に貼り付けることになった
- 一度、JANUSで撮った画像の追加情報として、2温度センサの温度差を地上にテレメで流したら、LOSとAKEの方程式は指向誤差の補正を可能にする。



### 8. Acknowledgement

The involvement of Leonardo as JANUS Instrument Prime contractor and OHU design authority is performed in the
frame of Italian Space Agency (ASI) Industrial Contract N. 2018-01-I.0. The Italian Principal Investigator team
acknowledges support from ASI under ASI-INAF agreement N. 2018-25-HH.0.

イタリアにある企業なら、わんちゃんICSO来るのでは？

## ★俺がやること：

- このドキュメントの中で理解・訳が明らかに間違っている部分は何か
- ★を付けた部分について議論を深めたい  
  - 特に、本研究の一般性に関しては大丈夫そう。
- 実際に大気試験した論文も見てみる：次のmdドキュメント

