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

### 3. Pointing Stability Requirements

#### 3.1 Line of Singht
- OHUのLOSの定義：
  - 外に出ていくビームの角度
  - そしてそれはdetectorのcenter pixelに一致する（はず。ノミナルでは光軸に一致）
- LOSの維持をPoiniting Stavilityと定義
- LOSのcontrolは通常、宇宙機の姿勢系によって行う ~ Body Pointing
  - steller fieldを取るか、single star observationをするか
- ただし、科学撮像ミッションの際には、"none direct monitoring"が取り除かれる可能性もある
  - "none direct monitoring"はつまり通常の姿勢系によるcontrolを意味する
  - というか、撮像の時以外は、特にOHUを動かさないという意味だろう
- なので、軌道の間で熱ひずみによるミスアライメントを小さくする光学設計が重要
- stabilityを得るために必要なこと
  - 正確な材質の選定
  - 特殊な構造コンポのgeometry ← ここのgeometryってどういう意味？★
  - 正確なactive thermal control


#### 3.2 Attitude Knowledge Error
- "The instantaneous knowledge of Pointing Error at any time given"
  - ※ Pointing Error = 実際の姿勢系のAttitudeとtargetの方を向くのに必要な姿勢の差分）
  - これを、"Absolute Knowledge Error"=AKE と呼ぶ。   
  - "instantaneous"って逐次的みたいな意味？ ★
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


#### 3.3 Requirements
- 今回のミッションを整理した上で、OHUに対する要求は以下のようになった
  - iFOV 15urad / pixel（= 7.5m/pixel at GCO500） GCO500は高度500kmのどこかの軌道
  - Ground FOV 1.72×1.29deg
  - Spectral range 340-1080nm
  - Optical MTF at Nyquist frequency >= 0.15 ← MTF初見なので、あとで意味確認★
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
  - Focal Plane Modeule
    - detectorを守るチタン部材とwindowを守る混合シリカ材で構成
  - Cover Module
    - OHUの望遠鏡を守る壁。デブリや太陽光、分子の侵入を防ぐ
  - Opto-Mechanical Structure
    - Telescope Module
      - Invar製。主鏡副鏡（ハイパーボラ）、3つのcorrector鏡
      - 10th order aspheric coefficient→光学倍率10倍？ 正確な情報★
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

#### 5.1. Methology
- Methologyって何だっけ？★
- 軌道におけるAKEの予測（prediction）は、"a sequence of multi-disciplinary analysis"で決める
  - このワード、俺の論文で解析の流れ紹介するときも使えそう

ここまでOK

- STOP解析の流れ
  - Thermal Analysis
    - ESATAN-TMSを用いる
    - 温度場の勾配、"ambient to orbital"(これなに★)の観点から、最悪ケースを複数選んだ。
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
  - "conservation of the Walls gradient"
  - 時間幅としては、キャリブレーションしてから観測開始までの間の時間（観測しない時間は含めない）
    - これは非常に学びになる。ΔTの変化を一定時間抑えればよい、という明確かつ達成可能そうな目標になっている
- ΔTがCold caseとHot Caseで大きく変わることを防ぐため、
  - ad-hoc location of active thermal control was studied (homogeneous distribution of heaters in the middle section of the CWS).
  - "ad-hoc"ってなに？addってこと？★
  - つまり、あえてactiveにヒーターをONにして、壁間温度差ΔTをcontrolしにいくということか！
  - これは結構賢いな。俺の研究で取り入れるのもあり得そう。

#### 5.4. LoS Prediction
- After having deduced the physical relation between LoS and Walls gradient
  - "deduce"- 推定する。こうやって帰納的に温度とLOSの関係を得たことを述べればいいのか
- LOS = α ΔT_walls +- u_LOS
  - 本関数の切片が0である理由は、関数の基準をnull Walls gradientにとっているから。
  - 地上のクリーンルームで一度校正をしたら、その後は基本的にLOSは0である。
  - ここはLOSの定義の話をしているのか、現象の話をしているのか、気になる。あとでAIに確認★
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
- Engeeneering heritageを用いてαのuncertaintyを決定：20％
- uncertaintyは事前に決めたのだろう。これで不確定要素の差分であるu_LOSが決まれば、Fig 7,8のようにリアルなSTOP解析値に対して、軽量モデルのplotを与えられる
  - とはいえ、結果を見ると、ほとんどu_LOS, u_AKEが無くてもαΔTだけで十分説明できているような気もする。
- AKEはそのものの値とu_AKEの値がともに一桁urad程度。u_AKEの方がAKEの本値よりも大きいケースもあるけどこれはそれでいいのかな？★

- *ここで気になるのは、そもそもなぜ俺の研究と違って、この研究ではLOS=α ΔTの立式に対してほぼバイアスが出ないのか、ということ。*
  - → はじめに地上で校正して、LOSが0になるという想定だから？なんでバイアス成分が出てこなかったのか、非常に気になる。要確認★

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




