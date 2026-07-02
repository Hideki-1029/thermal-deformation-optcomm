# 2026/6/18 memo

## 軌道予測誤差との分離

LOS誤差=軌道予測誤差 + 姿勢決定誤差 + アライメント + 熱ひずみ + 相手機側誤差

に対し、軌道予測誤差は熱ひずみの誤差と同じような動きをする。

研究のテーマとしては、「熱ひずみだけを観測から完全分離できる」ではなく、「軌道予測誤差などが共存する中でも、熱モデル由来の事前情報が粗捕捉の探索領域をどれだけ減らせるか」に置いた方が手堅い議論になりそう。

軌道予測誤差は，TLEのデータを取ってくれば整理できる．

## AIに英訳させるときの注意

訳させると単語に一貫性がなくなるので，注意．修正する．

## TD × Femap 解析

## 軽量モデルの候補（特に物理モデル）

修士輪講会予稿より：

軽量モデルの候補としては，衛星筐体・光学系の構造と温度分布から熱変形およびLOSバイアスを近似するphysical thermal deformation modelを中心に，平均LOSバイアスを用いるstatic bias model，軌道位相に対するFourier model，太陽・衛星・LOS幾何を入力とするorbital geometry model，温度センサ値を用いるthermal sensor modelなどが考えられる．物理モデルでは，光学ベンチや取付け構造の熱膨張，光学基準間の相対変位・相対角，および通信光軸への感度を簡略化して表現し，軌道上で扱える次数の補正モデルへ落とし込む

よって，熱ひずみの軽量物理モデルを physical thermal deformation modelとする．

## literature/papers/pdf サマリ

### 20260511_mochizuki_lab_seminar.pdf

題名: Multi-Sensor Relative Navigation for Formation Flying Under Thermo-Mechanical Variations  
著者: Tomoki Mochizuki

編隊飛行ミッションにおける高精度相対航法を対象に、熱機械変動が多センサ計測モデルへ与える影響を整理した研究発表。スターセンサ、QPD、レーザレンジャなどのセンサ融合では、各センサの外部パラメータや取付け関係が軌道上で変化すると、相対位置・姿勢推定に持続的なバイアスが入る。地上較正モデルをそのまま使えない点を問題化しており、本研究の「熱ひずみを未知外乱ではなく推定・補正対象にする」という考え方に近い。

### Analysis and Study on the Impact of Rapid Link Establishment of Interstellar.pdf

題名: Analysis and Study on the Impact of Rapid Link Establishment of Interstellar Laser in External Heat Flux Environment  
著者: Zhang Ping, Cheng Fei, Guan Zhe, He Wenzheng, Han Yidan

星間レーザ通信リンクの高速・安定な建鏈を対象に、外部熱流環境による衛星構体の熱変形がレーザ端末と星センサ基準間の指向誤差を生むことを有限要素解析で評価した論文。軌道高度や熱環境の違いに対して、取付け基準誤差やリンク指向誤差の変化傾向を調べ、端末配置や衛星熱設計への設計指針を与える。熱変形がmrad級の指向誤差になり得る点を示しており、粗捕捉の不確定領域を議論する根拠として有用。

### Beacon_correction_method_for_ISL_Comm.pdf

題名: Beacon correction method for inter-satellite laser communication  
著者: Qiang Wang, Liying Tan, Jing Ma

衛星間レーザ通信において、光学系の熱変形に起因する波面歪みがビーコン像のエネルギー分布を歪ませ、CCD上の重心検出誤差を生む問題を扱う。Zernike多項式で波面歪みを表現し、遠方界の歪んだ光斑モデルから目的関数を構成してビーコン中心を補正する手法を提案している。構体全体のLOSバイアスではなく、受信光斑の画像処理誤差補正に焦点があるが、熱変形がPAT観測量に入る経路を示す先行研究として参考になる。

### Body Pointing, Acquisition and Tracking for Small Satellite.pdf

題名: Body Pointing, Acquisition and Tracking for Small Satellite Laser Communication  
著者: Jesse Chang, Curt M. Schieler, Kerri M. Riesing, Jason W. Burnside, Karen Aquino, Bryan S. Robinson

NASA TBIRDの設計段階に近い論文で、小型衛星のbody pointing能力とquad-cell受信器を使い、専用ジンバルやFSMを増やさずにPATを実現する構成を扱う。初期捕捉ではstar tracker等によるopen-loop body pointingでground beaconをquad sensorのFOV内に入れ、その後payload feedbackを衛星バス制御へ入れて指向を改善する。シミュレーションではpayload feedbackにより指向誤差が62 µrad RMSから22 µrad RMSへ低減し、quad sensorの実験では2軸誤差5.7 µrad RMSで外乱を測れている。STT/LCTミスアライメントや熱LOSそのものを予測補正する論文ではないが、「粗捕捉前は光フィードバックなし」「捕捉後はpayload feedbackで引き込む」というPATの段階分けと、本研究でscan center補正を入れる位置づけを説明する背景として有用。

### Correction Method for Thermal Deformation Line-of-Sight.pdf

題名: Correction Method for Thermal Deformation Line-of-Sight Errors of Low-Orbit Optical Payloads Under Unstable Illumination Conditions  
著者: Yao Li, Xin Chen, Guangsen Liu, Peng Rao

低軌道光学ペイロードにおいて、日照条件が短時間で不規則に変化するため、熱変形由来のLOS誤差が高精度指向・測位を悪化させる問題を扱う。星観測データに基づき、太陽ベクトル、衛星位置ベクトル、カメラLOSベクトルの角度関係を補正パラメータとして使うことで、低軌道の不安定な熱環境を表現する。平均絶対LOS誤差を大きく低減しており、軌道幾何を入力にした軽量補正モデルの先行例として本研究に近い。

### feed-forward-compensation-of-body-pointing-uncertainties-for-laser-communication-terminals.pdf

題名: Feed-Forward Compensation of Body-Pointing Uncertainties for Laser Communication Terminals  
著者: Rene Rüddenklau, Salvatore Barone, Elisa Garbagnati, Simon Spier, Georg Schitter

CubeSat級LCTのacquisition phaseを対象に、ADCSの低レート姿勢情報とLCT内MEMS gyroの高レート測定を統合し、光フィードバックがまだ得られない段階でFSMへfeed-forward補償を入れる手法を提案する。ADCSとLCTセンサの座標系較正、gyroの温度依存バイアスのオンライン推定、quaternion propagation、FSM駆動電圧への変換まで扱っており、search patternに既知のpointing errorを重畳してFOUを実効的に小さくする考え方が本研究に近い。主対象はbody-pointing uncertainty、gyro drift、subsystem間の取付け誤差であり、熱構造解析からSTT-LCT相対LOSバイアスを予測するものではない。そのため、本研究は「feed-forwardでacquisitionを改善する」という同じ制御思想を、熱変形由来の時変LOSバイアスへ拡張する位置づけにできる。

### On-Board_Thermal_Motion_Compensation_Method_for_Pointing_Errors_of_the_Remote_Sensor_Aboard_a_Three-Axis_Stabilized_Geostationary_Satellite.pdf

題名: On-Board Thermal Motion Compensation Method for Pointing Errors of the Remote Sensor Aboard a Three-Axis Stabilized Geostationary Satellite  
著者: Hualong Hu, Xiaochong Tong, Chunping Qiu, He Li, Jiantao Fu, Yanfa Shang, Jingtao Shi

三軸安定GEOリモートセンサの熱変形LOS誤差を、オンボードでリアルタイム補償するThermal Motion Compensation手法を提案する。センサ内部の複雑な熱ミスアライメントをLOS misalignment angleとして集約し、長期の星観測時系列から日周期の再現性をフィットする点が特徴。FY-4A/AGRIで検証されている。GEOの規則的な熱変動が前提だが、Fourier的な周期モデルでLOSバイアスを補正する発想は本研究のfeedforward補正に接続できる。

### On-orbit results of pointing, acquisition, and tracking for the.pdf

題名: On-orbit results of pointing, acquisition, and tracking for the TBIRD CubeSat mission  
著者: Kathleen M. Riesing, Curt M. Schieler, Jesse S. Chang, Noah J. Gilbert, Andrew J. Horvath, Robert S. Reeve, Bryan S. Robinson, Jade P. Wang, Paaras S. Agrawal, Robert A. Goodloe

TBIRD CubeSatの軌道上PAT結果を報告する論文。6U CubeSatで100/200 Gbps級のLEO-地上レーザ通信と1 TB超のデータ転送を実証し、ペイロードのquad cellフィードバックを衛星バス制御に閉じ込むことで20--35 µrad RMS/axisの追尾精度を達成している。初期捕捉ではTLE誤差、地上局指向、ペイロード視野、打上げ後のboresight shiftが重要になる。本研究で扱う粗捕捉不確定性やscan areaの実ミッション上の意味を説明する背景文献になる。

### Optimization_of_mirro_mounting_structure_for_a_reflective_star_tracker.pdf

題名: Optimization of the mirror mounting structure for a reflective star tracker based on integrated analysis of line-of-sight thermal stability error  
著者: Yansong Gao, Zongxuan Li, Jiuxin Ning, Lin Li, Xinyu Yang, Qin Zhao

大口径・長焦点の反射型スターセンサを対象に、軌道上温度変動によるLOS熱ドリフトを低減するミラー支持構造の最適化を行う。光学系の公差解析で各ミラーのLOS感度を評価し、構造変位と像点偏差を結ぶ感度行列を作った上で、主鏡・副鏡・第三鏡の柔軟支持を順次最適化している。熱ドリフト角を約30%低減し、実測とも整合した。光通信端末そのものではないが、光学基準の熱安定性設計とLOS誤差評価の方法論として参考になる。

### Opto-thermo-mechanical phenomena in satellite free-space optical communications survey and challenges.pdf

題名: Opto-thermo-mechanical phenomena in satellite free-space optical communications: survey and challenges  
著者: Mario Badás, Pierre Piron, Jasper Bouwmeester, Jérôme Loicq, Hans Kuiper, Eberhard Gill

衛星FSOC端末で生じる光・熱・構造連成現象を総覧し、それらが光学性能および通信性能へどう伝播するかを整理したレビュー。宇宙環境の熱・機械荷重、端末構成要素、STOP解析、波面誤差やpointing jitterからBERなど通信指標への接続、緩和技術と研究課題を体系化している。個別補正手法を提案する論文ではないが、熱ひずみを通信性能へ接続する議論の上位文脈を与える文献で、本研究の問題設定を位置づけるのに使いやすい。

### Predictive filtering-based fast reacquisition approach for space-borne acquisition, tracking, and pointing systems.pdf

題名: Predictive filtering-based fast reacquisition approach for space-borne acquisition, tracking, and pointing systems  
著者: Shuai Bai, Jianyu Wang, Jia Qiang, Liang Zhang, Juanjuan Wang

宇宙用ATPシステムで光リンクが途切れた後、過去の角度情報から目標軌道を予測して再捕捉時間を短縮する手法を提案する。最適化有限記憶フィルタを用い、曲線形状に応じて事前学習したパラメータを切り替えることで、数秒先の角度を予測する。大気フェージングや遮蔽でリンクが失われるLEO-地上通信では、数十秒の停止でもデータ量に影響するため、再捕捉の高速化が重要になる。熱補正ではないが、捕捉時間を評価指標に置く妥当性を支える文献。

### Thermal Deformation Stability Optimization Design and.pdf

題名: Thermal Deformation Stability Optimization Design and Experiment of the Satellite Bus to Control the Laser Communication Load's Acquisition Time  
著者: Yousheng Shi, Shanbo Chen, Meng Yu, You Wu, Jisong Yu, Lei Zhang

レーザ通信ペイロードと星センサ間の熱変形による光軸角変動を抑え、捕捉時間要求を満たすための衛星バス構造最適化を扱う。軌道上温度場を熱変形解析の境界条件にし、共通基準構造と柔軟絶縁により熱変形結合を低減する。解析では取付け角変動が14.25秒角まで下がり、地上温度偏差・プリズム較正試験では温度変化による最大角変動が117.74秒角から10.72秒角へ低減、軌道上試験で30秒捕捉要求を満たした。熱変形とacquisition timeを直接結ぶ重要文献。

### Transmitter Beam Bias Verification for Optical Satellite Data.pdf

題名: Transmitter Beam Bias Verification for Optical Satellite Data Downlinks with Open-Loop Pointing - the 3-OGS-Experiment  
著者: Dirk Giggenbach, Petro Karafillis, Jonas Rittershofer, Andreas Immerz, Andreas Spoerl, Steffen Gaisser, Sabine Klinkner, Marcus T. Knopp

DLR/University of StuttgartのFlying Laptop + OSIRISv1を対象に、open-loop pointingの光ダウンリンクで送信ビームの動的なpointing biasを地上3局の受信強度から推定する実験。3つのOGSで測った受信強度をガウシアンビームの強度分布と照合し、地上面上のbeam center-of-gravityの移動を推定して、衛星AOCSデータと比較する。結果として、衛星側AOCSで見える残差は最大約300 µrad程度でも、地上で実測されるビーム誤差は低仰角で最大約1 mradになり得ることを示している。熱変形を直接モデル化する研究ではないが、実測ビームバイアスを同定して将来のopen-loop pointing補正へ反映する考え方は、本研究のPAT残差・受信強度を使ったadaptive correctionの根拠として使いやすい。

### 草野さん_熱ひずみ検討_2023_7_31 RG presentation Research theme study.pdf

題名: Research theme study  
著者: Yuki Kusano

光通信の捕捉追尾制御における指向精度劣化要因として、アライメント誤差、振動、熱ひずみ、姿勢外乱、目標方向推定誤差、制御誤差、センサ誤差を整理した研究テーマ検討資料。アライメント誤差と熱ひずみは短時間ではバイアス的に扱えるため、推定して指向精度改善に使える可能性があると位置づける。粗追尾では軌道情報に基づくfeedforward制御も効くため、熱ひずみやアライメント誤差が問題化する。星を通信相手の代替として使う較正案も述べている。

# 2026/6/25 memo

## TD/Femapで最終的に取りたいデータ

PAT性能評価に直接必要なのは、熱ひずみ場そのものではなく、熱変形によってSTT基準系とLCT光軸基準系の間に生じる相対変位・相対回転である。

最低限は、時刻または軌道位相ごとの以下の量が欲しい。

- STT側の基準点または基準座標系の変位・姿勢変化
- LCT側の基準点または光軸基準座標系の変位・姿勢変化
- STT-LCT間の相対変位、相対回転
- それをLOS角度誤差に変換した `theta_x`, `theta_y` [urad]

つまりTD/Femapの出力は、最終的には既存のPATシミュレータ内の熱LOSバイアス真値 `theta_thermal_true` を置き換える時系列データとして使う。

## Python上で衛星構造をどう扱うか

座標データだけだと点群であり、衛星の形や構造は分からない。Python上で構造的に扱うには、節点座標に加えて、節点同士の接続関係と部品グループが必要になる。

最低限欲しいデータ構造は以下。

- `nodes`: `node_id`, `x`, `y`, `z`
- `elements`: `element_id`, `element_type`, `node_id_1`, `node_id_2`, ...
- `groups/components`: `node_id`または`element_id`と、`STT`, `LCT`, `optical_bench`, `panel`, `bus_frame`などの部品名
- `results`: `time`, `node_id`, `dx`, `dy`, `dz`, 必要ならひずみテンソル

PAT補正だけなら、全節点のひずみテンソルを完全に読む必要はない。一方で、衛星の熱ひずみ構造を軽量モデルとしてPython側で近似したい場合は、代表節点群の変位時系列が欲しい。ひずみ情報は、どの部材や面が変形の原因になっているかを理解する用途で有用。

整理すると以下。

- PAT補正のみ: STT-LCTの相対変位・相対回転・LOS角度で十分
- Femap結果の軽量モデル化: 代表節点の変位時系列が欲しい
- 物理的原因の説明: 部材ごとのひずみ、応力、温度分布も欲しい

## 軽量な熱ひずみモデル

熱ひずみの最も基本的なモデルは `epsilon_thermal = alpha * DeltaT` である。ただし、これだけで直接LCTのLOSずれが出るわけではない。実際のLOSずれには、材料ごとの熱膨張率、部材拘束、接合条件、構体剛性、温度分布、STT/LCTの取付位置が効く。

一様な自由膨張なら、

```text
DeltaL = alpha * L * DeltaT
```

だが、構造全体が同じ方向に伸びるだけでは角度誤差になりにくい。LOS誤差になるのは、上下・左右・STT側/LCT側の温度差、異種材料、非対称な取付などによって、差分膨張・曲げ・ねじれが出る場合。

梁の曲げとして近似するなら、

```text
kappa ~= alpha * (T_top - T_bottom) / h
theta ~= kappa * L
```

ここで `kappa` は曲率、`h` は構造高さ、`L` はSTT-LCT間距離。Pythonではまず、代表温度差から `theta_x`, `theta_y` を出す簡易モデルを作り、TD/Femapを高忠実度な真値として比較するのが現実的。

モデルの段階としては以下が考えられる。

- `alpha * DeltaT` に基づく手計算モデル
- 代表温度・代表部材を使った梁/板モデル
- 代表節点変位のPCA、Fourier、回帰モデル
- TD/Femapによる高忠実度モデル

## 先行研究との位置づけ

熱変形によるLOS誤差や、STOP解析、Reduced Order Model、観測衛星のLOS drift補正、光通信での波面・スポット重心補正は先行研究がある。

ただし、今回の狙いである「TD/Femapで得たSTT-LCT相対変形を軽量なLOSバイアス予測モデルに圧縮し、それを光通信PATの粗捕捉scan center補正に使い、さらにPAT残差でオンライン更新する」という一気通貫の形は、まだ研究の隙間がありそう。

新規性の置き方は、「熱ひずみLOS誤差が存在する」ではなく、「熱構造モデル由来の時変LOSバイアスを光通信PATの粗捕捉性能、scan area、acquisition timeに接続し、物理モデルと軌道上観測更新を組み合わせる」ことに置くのが良さそう。

# 2026/7/2 memo

## ベースライン衛星構造モデル

TDおよびFemapのshellモデル寸法:

- X: 590 mm
- Y: 600 mm
- Z: 990 mm

衛星パネル:

- 厚み: 10 mm
- 素材: A5052

構造モデルの正本は `inputs/spacecraft_models/baseline_bus.yaml` に置く。`case_matrix.xlsx` では、寸法や材料を各ケース行へ直接展開せず、`spacecraft_model` でこの構造モデルを参照する。

写真から読み取ったA5052設定:

- Thermal Desktop: `A5052`
  - 熱伝導率: `kx = 0.137 W/mm/C`
  - 比熱: `cp = 900 J/kg/C`
  - 密度: `rho = 2.68e-06 kg/mm^3`
  - 有効放射率: `e-star = 0`
- Femap: `Aluminum 5052 Annealed Wrought`
  - ヤング率: `7.0327e10 Pa`
  - ポアソン比: `0.33`
  - 線膨張率: `2.376e-05 1/C`
  - 熱伝導率: `137.86 W/m/C`
  - 比熱: `921 J/kg/C`
  - 密度: `2685.002 kg/m^3`
  - 基準温度: `23.9 C`