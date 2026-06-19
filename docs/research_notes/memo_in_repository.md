# 2026/6/18 memo

## 軌道予測誤差との分離
LOS誤差=軌道予測誤差 + 姿勢決定誤差 + アライメント + 熱ひずみ + 相手機側誤差

に対し、軌道予測誤差は熱ひずみの誤差と同じような動きをする。

研究のテーマとしては、「熱ひずみだけを観測から完全分離できる」ではなく、「軌道予測誤差などが共存する中でも、熱モデル由来の事前情報が粗捕捉の探索領域をどれだけ減らせるか」に置いた方が手堅い議論になりそう。

軌道予測誤差は，TLEのデータを取ってくれば整理できる．


## TD × Femap 解析



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

### Correction Method for Thermal Deformation Line-of-Sight.pdf
題名: Correction Method for Thermal Deformation Line-of-Sight Errors of Low-Orbit Optical Payloads Under Unstable Illumination Conditions  
著者: Yao Li, Xin Chen, Guangsen Liu, Peng Rao

低軌道光学ペイロードにおいて、日照条件が短時間で不規則に変化するため、熱変形由来のLOS誤差が高精度指向・測位を悪化させる問題を扱う。星観測データに基づき、太陽ベクトル、衛星位置ベクトル、カメラLOSベクトルの角度関係を補正パラメータとして使うことで、低軌道の不安定な熱環境を表現する。平均絶対LOS誤差を大きく低減しており、軌道幾何を入力にした軽量補正モデルの先行例として本研究に近い。

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

### 草野さん_熱ひずみ検討_2023_7_31 RG presentation Research theme study.pdf
題名: Research theme study  
著者: Yuki Kusano

光通信の捕捉追尾制御における指向精度劣化要因として、アライメント誤差、振動、熱ひずみ、姿勢外乱、目標方向推定誤差、制御誤差、センサ誤差を整理した研究テーマ検討資料。アライメント誤差と熱ひずみは短時間ではバイアス的に扱えるため、推定して指向精度改善に使える可能性があると位置づける。粗追尾では軌道情報に基づくfeedforward制御も効くため、熱ひずみやアライメント誤差が問題化する。星を通信相手の代替として使う較正案も述べている。

