# 260725 JANUS Ground Test Review

- 作成: 2026-07-25
- 目的: 2026/7/25 JANUS STOP解析に対する答え合わせ的な論文。地上で大気下で試験した場合の式の正しさを評価する。in Mallorcaでの飛行機待ち
- 主な入力:
  - `docs/literature/JANUS_Optical_Head_Line_of_Sight_Temperature_dependence_Characterization_and_Validation_by_on_ground_test.pdf`


---
## 1. 論文読み -Turella, JANUS Ground Test -

### Abstract
- ミッション的にLOSの精度に対する要求が高い
- JANUSのLOSは熱環境で変わりうる
- JANUSの温度場を変えうる要素は、
  - 軌道姿勢の変更
  - 宇宙機のマヌーバ
  - サイエンスペイロードの内部発熱（heat dissipationってなに？★）
- STOP解析を実施し、光学要素の並進移動・回転を出力
- 結果、LOSの値・uncertaintyとOHUの構造の温度勾配の間に線形関係があることを発見
- この関係性を、実際に地上大気試験で示した
- 試験で得た係数を用いることで、OHUの温度センサの値を読むことで、LOSの予測と（不確定さの？）評価をリアルタイムかつindirectに行うことができる。


### 1. INTRODUCTION
- JUICEミッションは、3つのGalelian moonを探査する
- Ganymedeに行くSpace Craftは初めてになる予定
- ミッションの目的：
  - 惑星構成の必要条件
  - 生命の発現
- JANUSはカメラ
- JANUSはJovian 大気調査とGanymedeのLibrationの計測が目的
- OHUのLOSの知識と特徴づけが非常に重要
- STOP解析とそのverificationがこの論文のメイン


### 2. LOS CHARACTERIZATION WITH IN-AIR TEST
- Opto Mechanical Structure；OMS に注目した試験をする
  - → LOSにおいてメインのcontributer。Baffle Wall とOptical Wallの間の温度差
- [2] 論文：JANUS STOP解析 によると、
  - LOS = LOS_Y
- OMS以外の全ての要素のLOSに対する寄与が無視できるほど小さいことは既知とする（これは前回のSTOP解析でわかったこと）
- TESTはOHUのSTMを用いて行われた
  - Focal Plane ModuleとFilter Wheel ModuleのSTMが入っている
  - ハーネスや宇宙機のpurging lineは入ってない←purging lineってなに？★
- FPMのDetectorやPCBのひずみ、FWM Filterの回転・ひずみは考慮しない

#### A.Concept

- 常温に維持した剛なアルミInterface Plate上にOHU STMを固定する
- Optical Wall（OW）を加熱し、Baffle Wall（BW）との間に温度差を作る
  - OWとBWのX方向の熱膨張量に差が生じる
  - その差によってOMS全体が曲がり、Y軸周りに回転する
  - この回転をLOS変化として計測する
- OWとBWの温度差をWall's temperature gradientと呼ぶ
  - ΔT_Walls = T_OW - T_BW


#### B. Assumption

- Primary Mirror（M1）のtiltをOHU全体のLOS変化とみなす
  - TEM（Telescope Module）はOWに剛結合されている
  - OWが回転するとTEMと内部の光学要素も一緒に回転する
  - よって、M1の回転を測ればTEM全体の回転、ひいてはOHUのLOS変化を測ったことになる
  - ただし、実際に光をDetectorまで通してLOSを測るEnd-to-End試験ではなく、「M1 tilt = LoS」という仮定に基づく試験
- 試験は真空ではなく大気中で実施
  - Theodoliteによる反射角計測だけなので、真空である必要がない
  - 大気試験のメリット
    - OHUと試験系へ常時アクセスできる
    - 対流によって温度遷移が早く、試験時間を短縮できる
    - 真空チャンバー窓の変形がTheodolite計測へ入らない
      - 過去の真空試験では、減圧による窓のたわみが60 arcsec以上の不確かさを生み、計測対象そのものより大きくなった
  - 大気試験のデメリット
    - 対流でOHUが冷却されるため、投入熱の多くが失われ、大きなヒーター電力が必要
    - ヒーター近傍のHot Spotが強調され、温度分布の一様性が悪くなる
- 大気試験と軌道上で、温度変化の時間スケールを近づける
  - M1とOWの温度差の変化速度が2°C/h未満になったときだけデータを取得
  - 軌道上のGCO500では約1°C/hと予測されている
  - この条件なら、M1とOW間の相対熱伸びによる回転は、OMS全体の回転に対して無視できると仮定
- 試験用ヒーターの位置は、熱解析で予測された軌道上Hot Spotを十分再現すると仮定
- Interface Plate
  - アルミ板へOHUを剛固定
  - Interface Plate自体の差動熱変形が入らないよう、室温で一定に保って温度監視する
  - 外部Harnessは取り付けない
- Theodolite measurement
  - Theodoliteを実験室床面に恒久的に固定
  - STMのM1は未コーティングで反射計測しにくいため、M1表面にOptical Cubeを接着
  - Optical Cubeの反射方向からM1の回転を測る


#### C. Setup

- PT100温度センサをOW、BW、M1、Aluminum Interface Plateの複数位置に設置
  - 各部材の温度は、その部材に付けた複数PT100の平均値で評価する
- OW下部に4個の50 Wヒーターを設置
  - 軌道上では主にHarnessを通してOHUへ熱が伝わる
  - 今回はHarnessを付けない代わりに、熱解析で得たHot Spotと近い位置をヒーターで加熱する
- M1の回転はTheodolite、各部温度はPT100、加熱量はPower Supplyで取得する


#### D. Test Flow

- 初期状態
  - OHU全体を室温の一様温度分布にする
  - この状態でLOS=0、ΔT_Walls=0を基準とする
- LOSと各部温度を計測
- ヒーター電力を5 Wずつ増加
- 電源上限の85 Wまで加熱し、OW-BW間にできるだけ大きな温度差を作る
  - OMSの変形量を大きくし、Theodoliteの計測不確かさの相対的な影響を小さくする狙い
- M1-OW間の温度差変化が2°C/h未満になるまで待機し、安定条件に入ったらLOSと温度を計測
- 加熱終了後、再び室温の一様温度分布へ戻す


#### E. Test Data

- ヒーター電力を増やすにつれてOW温度とM1のY軸回転が増加
- X軸回転はY軸回転に比べて十分小さいことを確認
  - 前論文の仮定 LoS = LoS_Y と整合する
- 最大加熱時にはY軸回転が約200 μradまで増えている
- 大気対流と局所加熱のため、同じWall上でもセンサ位置によって温度にばらつきがある
  - このばらつきを後段の温度差および比例係数の不確かさに反映する


#### 収束判定についての考察（AIとの議論）

- 気になった点
  - 収束判定は、M1とOWの温度差の変化速度が2°C/h未満になること
  - M1とOWの温度が同じ速度で上昇していれば、それぞれが過渡状態でも温度差の変化は小さくなり、判定を満たしてしまう
  - したがって、この条件は各部温度やOMS全体が熱的定常状態に入ったことを意味しない
- 著者がこの判定量を選んだ意図
  - この試験は「M1 tilt ≈ OMS全体のtilt ≈ OHU LoS」を仮定して、M1の回転をLOSとして測っている
  - M1の温度応答がOWより遅れると、計測されるM1 tiltに以下の2成分が入る
    - OMS全体の回転：測りたい成分
    - M1とOW間の相対熱変形による回転：取り除きたい成分
  - そのため、完全な熱定常よりも「M1がOWへ十分追従し、一体として回転していること」を優先して確認したと考えられる
  - 軌道上でも温度は約1°C/hで変化すると予測されており、各温度の時間変化をほぼ0にする条件では、実際の軌道上過渡状態を除外してしまう
  - 大気中では対流による放熱があり、各5 Wステップで構造全体の完全定常を待つと試験時間も非常に長くなる
- ただし、この判定だけでは不十分な可能性
  - LOSモデルの説明変数は ΔT_Walls = T_OW - T_BW
  - 一方、収束判定に使っているのはT_M1 - T_OW
  - よって、M1とOW間の相対熱遅れは確認できるが、LOSを発生させるOW-BW温度差やWall内温度分布が準定常になったことは保証できない
  - 2°C/hという閾値も、軌道予測値1°C/hの2倍であり、「軌道上と同じ」というより同じオーダーの緩い条件
- Fig. 8の低ΔT_Walls領域でFitとの一致が悪い理由
  - 著者が述べるように、温度場・変形がまだ過渡状態だった可能性
  - 低ΔTではLOS変化量そのものが小さく、Theodolite不確かさ24 μradの相対的影響が大きくなる
  - したがって、未収束の熱過渡と低S/Nの両方が寄与した可能性が高い
- 試験設計上のもう一つの限界
  - ヒーター電力を単調に増加させているため、時間、平均温度、ΔT_Walls、加熱電力が同時に増加する
  - この試験経路だけでは、LOSを決めているのが本当にΔT_Wallsだけなのか、平均温度や熱過渡の影響が残っているのかを完全には分離できない
  - 85 W時のSTOP解析値が試験の不確かさ範囲に入ることは整合性の確認にはなるが、1点だけなので線形性全体を強くValidationするものではない
- より厳密に評価するなら、以下も収束・取得条件に加えるとよい
  - d(T_M1 - T_OW)/dt：M1の相対熱遅れ
  - d(T_OW - T_BW)/dt：LOSを生むWall gradientの安定性
  - dLoS/dt：実際の回転計測の安定性
  - 各部の絶対温度変化率
  - 加熱時と冷却時の両方で同じΔT_Wallsを作り、LOSにHysteresisがないか確認
  - 異なる平均温度・ヒーター配置でも、同じΔT_Wallsに対して同じLOSが得られるか確認
- 総評
  - M1-OW温度差の変化率を使うこと自体は、試験目的に沿った合理性がある
  - ただし、それだけで静的な LoS = K ΔT_Walls 回帰に必要な準定常性が保証されたとは言えない
  - 本試験は比例関係を概ね支持するが、動的影響やHysteresisまで含めた厳密な線形性検証としては限定的


### 3. LOS PROPORTIONALITY FACTOR

- LOSと壁間温度差の比例係数Kを以下で定義
  - K = LoS / ΔT_Walls ± u_K
- OW、BWの代表温度
  - T_OW = OW上の全Thermistorの平均
  - T_BW = BW上の全Thermistorの平均
- Wall表面の温度が一様でないことと、センサ位置の代表性を温度不確かさとして評価
  - u_TOW、u_TBWは、それぞれのWall上にあるセンサ計測値の標準偏差
  - 加熱量が増えるほどHot Spotが強くなり、不確かさも増える
    - 0 W：u_TOW = u_TBW = ±0°C
    - 85 W：u_TOW = ±3.3°C、u_TBW = ±1°C
  - Kline-McClintockの不確かさ伝播を用いる
    - u_ΔTWalls = √(u_TOW² + u_TBW²)
    - OW側のばらつきが支配的なので、ほぼu_ΔTWalls ≈ u_TOW
- PT100単体の計測不確かさ±0.5°Cは、表面温度の非一様性に比べて小さいとして無視
- TheodoliteのLOS計測不確かさ
  - u_LoS = 5 arcsec = 24 μrad
  - 実験室での技術的経験に基づく仮定値

#### A. Proportionality Factor

- 試験データに対してBest Linear Fitを実施し、比例係数Kを同定
- Fitは、室温・一様温度の基準点（ΔT_Walls=0、LoS=0）を必ず通るように拘束
- 得られた比例係数
  - K = 7.2 μrad/°C
  - 1σ uncertainty：+1.1 / -0.8 μrad/°C
- 小さいΔT_Walls領域では、Fitと計測値の一致が一部悪い
  - 構造温度がまだゆっくり上昇中で、過渡状態が完了していなかった可能性
  - Ambient温度に近く、まだ十分な熱変形が発生していなかったと考察
- STOP FEMとの比較
  - 85 W時に実測した温度分布をFEMへ入力し、LOSを再計算
  - OMSバルク材から実測したInvar36のCTE = 2.0×10^-6 1/KでFEMを更新
  - FEMから予測したKは、地上試験から得たKの不確かさ範囲内に入った
  - したがって、前論文のSTOP解析で得た「LOSとΔT_Wallsの比例関係」が地上試験で概ねValidationされた


### 4. LOS & AKE IN-FLIGHT PREDICTION

- 軌道上のLOSを以下の経験式で予測
  - LoS(t) = K ΔT_Walls(t) ± u_LoS(t)
- AKEは、Science観測時とStar Calibration時のLOS差
  - AKE(t) = LoS_Science(t) - LoS_Calibration
  - ≈ K {ΔT_Walls^Science(t) - ΔT_Walls^Calibration} ± u_AKE(t)
- Science時のΔT_Wallsは時刻tによって変化する
- Calibration時のΔT_Wallsは、1回のCalibration時点で得た固定値として扱う

#### A. Walls gradient measurement during flight

- 実機PFMでは、OWとBWの特定位置にPT1000を1個ずつ、合計2個搭載
- 軌道上では、この2センサだけからΔT_Wallsを推定する
- 課題
  - 2点の局所温度がWall全体の平均温度をどこまで代表できるか
- 代表性の不確かさを、STMのThermal Vacuum Cycling（TVC）試験データから評価
  - STMにはWall上の複数位置にPT100が付いている
  - 全センサ平均から求めたΔT_Wallsと、実機PT1000と同位置にあるOW-X・BW-Xの2センサだけから求めたΔT_Wallsを比較
- 真空中では対流がなく、境界条件の変化も遅いため、Wall内の温度は大気試験より一様
  - 2センサによる温度差は、全センサ平均による温度差とよく一致
- Hot/Cold境界条件を急に切り替えた瞬間には差が大きくなる
  - 論文では、この速い切替は実際の軌道・姿勢変化より急であり、飛行中には発生しない非現実的な変化と判断
- TVC全温度履歴における両算出方法の差の標準偏差を1σ不確かさとする
  - u_ΔTWalls = ±0.4°C（1σ）

#### B. LoS empirical functions

- PT1000単体の計測不確かさ±0.1°Cは無視
- LOSの不確かさ
  - u_LoS(t) = √{(ΔT_Walls(t) u_K)² + (K u_ΔTWalls)²}
  - 比例係数Kの不確かさと、2センサによる壁間温度差の不確かさを伝播
- MissionのScience要求に合わせ、不確かさは2σで表示
- 壁間温度差の符号を反転すると、LOSの符号も反転し、同じ比例関係を維持すると仮定
- 経験式の中心値
  - LoS = 7.2 ΔT_Walls [μrad]
  - ΔT_Walls = ±8°Cのとき、LoS = ±58 μrad
  - ΔT_Walls = 0でも、2点温度計測の代表性によってLOS不確かさは約±6 μrad（2σ）残る

#### C. AKE empirical functions

- AKEの中心値
  - AKE = 7.2 {ΔT_Walls^Science - ΔT_Walls^Calibration} [μrad]
- Science時とCalibration時の壁間温度差計測は、同程度の不確かさを持つと保守的に仮定
- AKEの不確かさ
  - Kの不確かさ
  - Science時のΔT_Walls計測不確かさ
  - Calibration時のΔT_Walls計測不確かさ
  - 上記を独立として二乗和平方根で伝播
- 不確かさはMission要求に合わせて2σ表示
- Science時とCalibration時の温度差が同じなら、公称AKEは0
  - ただし2回分の温度差計測不確かさが入るため、ΔT差=0でもu_AKEは約±8 μrad（2σ）
- ΔT_Walls^Science - ΔT_Walls^Calibration = ±8°Cでは、AKE中心値は±58 μrad
  - 2σ不確かさは、おおよそ+19 / -16 μradまで増加


### 5. CONCLUSIONS

- 大気中でのOHU STM試験により、LOSと壁間温度差の比例係数Kを実測し、不確かさとともに同定した
- 実測温度分布を入力したSTOP FEMの予測値は、試験結果の不確かさ範囲内で一致
  - 前論文で得たLOS-ΔT_Walls線形関係を、独立な地上試験で概ねValidationできた
- STMのThermal Balance/Cycling試験データから、2個のPT1000だけでWall平均温度差を代表することによる誤差を評価
- 軌道上では、OWとBWに埋め込んだ2個のPT1000のTelemetryから、LOSとAKEをリアルタイムかつ間接的に推定できる


### この試験のValidation範囲について

- この試験で直接測ったのは、Detector上の像位置や出射光のLOSではなく、M1に接着したOptical Cubeの回転
  - 「M1 tilt ≈ OMS全体のtilt ≈ OHU LoS」という前論文の解析結果を前提としている
- STMを用い、FPM Detector/PCB変形、FWM Filter変形、外部Harness、Purging lineを含めていない
- 大気対流と局所ヒーターによる温度分布は軌道上と完全には同じでない
- したがって、これは完全なFlight ConfigurationのEnd-to-End光学性能試験ではなく、支配メカニズムと比例係数を構造レベルで確認したValidationと捉えるのが適切
- 一方で、
  - 実測した温度分布をFEMへ戻して比較している
  - Invar36の実測CTEでFEMを更新している
  - 実機2センサの代表性を別の真空試験データで評価している
  - という形で、大気試験と軌道上条件の差を補完している点は丁寧
