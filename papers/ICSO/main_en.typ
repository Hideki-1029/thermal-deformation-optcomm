#import "template.typ": spie-paper, spie-table

#let flow-node(title, body, fill: luma(250)) = {
  rect(
    width: 100%,
    stroke: 0.6pt + luma(150),
    fill: fill,
    inset: 6pt,
  )[
    #set text(size: 8.5pt)
    #set par(justify: false, leading: 9.5pt)
    #text(weight: "bold")[#title]
    #v(0.2em)
    #body
  ]
}

#let flow-arrow = align(center + horizon)[#text(size: 13pt)[→]]

#let problem-schematic = {
  grid(
    columns: (1.05fr, auto, 1.1fr, auto, 1.15fr),
    gutter: 6pt,
    flow-node[LEO thermal environment][
      Eclipse cycles, the sun-facing panel, surface optical properties, and internal dissipation produce a time-varying temperature field.
    ],
    flow-arrow,
    flow-node[STT--LCT relative LOS angle][
      Thermoelastic deformation changes the outgoing LCT optical axis relative to the STT attitude reference.
    ],
    flow-arrow,
    flow-node[Coarse acquisition FF][
      The predicted thermal LOS angle is subtracted from the scan center before optical feedback is available.
    ],
  )
}

#let model-schematic = {
  grid(
    columns: (1.05fr, auto, 1.25fr, auto, 1.05fr),
    gutter: 6pt,
    flow-node[Inputs][
      $Delta T(t)$, sun face, and PROP/PCDU ON--OFF states
    ],
    flow-arrow,
    flow-node[Hierarchical sun-face $Delta T$ model][
      Within case: $theta_"dom" approx b_"case" + a("sun") Delta T$ \
      Across cases: $b_"case" approx b_0("sun") + c_"prop"I_"prop" + c_"pcdu"I_"pcdu"$
    ],
    flow-arrow,
    flow-node[LOS angle prediction][
      $hat(theta)_"dom" = b_"pred" + a_"shared" Delta T$ \
      Evaluation with 16 fixed coefficients
    ],
  )
}

#let pat-schematic = {
  grid(
    columns: (1fr, auto, 1fr, auto, 1fr, auto, 1fr),
    gutter: 5pt,
    flow-node[TD/Femap truth][Thermal LOS angle time series],
    flow-arrow,
    flow-node[Reduced-order model][Hierarchical sun-face $Delta T$ model / thermal truth],
    flow-arrow,
    flow-node[Scan center correction][$bold(theta)_"scan" = bold(theta)_"nom" - hat(bold(theta))_"th"$],
    flow-arrow,
    flow-node[Rectangular spiral][Acquisition success and time],
  )
}

#show: spie-paper.with(
  title: [Hierarchical Prediction and Feedforward Correction of Time-Varying Thermal Line-of-Sight Bias for Coarse Acquisition in Satellite Optical Communications],
  authors: [
    Hideki Takamoto#super[\*], Kazuki Takashima, Yuki Kusano, Satoshi Ikari, and Ryu Funase
  ],
  affiliations: [
    Department of Aeronautics and Astronautics, The University of Tokyo, 7-3-1 Hongo, Bunkyo-ku, Tokyo 113-8656, Japan
  ],
  corresponding-email: [Corresponding author: Hideki Takamoto, email: hidekitakamoto\@g.ecc.u-tokyo.ac.jp],
  abstract: [
    Thermal pointing bias can increase coarse acquisition search time in satellite optical communications before optical feedback becomes available. This study predicts the relative line-of-sight (LOS) angle between a star tracker reference and a laser communication terminal using the center temperature difference between the sun-facing and opposite panels and operational information, then applies the prediction as feedforward correction of the scan center. Thermoelastic analysis of a satellite with a box structure in low Earth orbit covered 21 cases spanning sun faces, internal dissipation, surface properties, and orbit conditions. The resulting hierarchical sun-face $Delta T$ model has 16 coefficients. Panel temperature difference represents orbital variation, while biases based on sun face and dissipation state represent the DC terms for both axes. Nested leave-one-case-out evaluation excluded the test case from all coefficient estimates and gave a mean RMSE of 5.5 µrad on the dominant axis over subsequent orbits, compared with a median raw LOS angle RMS of 615 µrad. In rectangular scan simulations for 17 cases under the baseline cold orbit and surface conditions, correction reduced the mean acquisition time from 12.1 to 0.10 s with thermal error only. With synthesized nonthermal errors, it reduced the mean from 16.3 to 4.74 s and increased the success rate from 98.3% to 100%. A preliminary study of two cases further showed that applying the previous orbit's observed residual to the next through a Fourier update reduced the periodic residual after feedforward correction.
  ],
  keywords: (
    "optical communication",
    "pointing, acquisition, and tracking",
    "thermal deformation",
    "line-of-sight angle bias",
    "feedforward correction",
  ),
  language: "en",
)

= INTRODUCTION

Satellite optical communication provides high antenna gain and wide communication bandwidth, but its small beam divergence makes link establishment strongly dependent on pointing, acquisition, and tracking (PAT) performance @2017-kaushal-survey. During coarse acquisition, before stable optical feedback from the counterpart terminal is available, the spacecraft must scan an uncertainty region that includes orbit prediction error, attitude determination and control error, alignment residuals, terminal mounting error, and structural deformation @2023-riesing-tbird. Because the number of search points and acquisition time increase approximately with the uncertainty area, correcting predictable components before coarse acquisition can directly reduce link establishment time.

Initial pointing error sources differ substantially. With TLE orbit information, orbit prediction error can reach several hundred microradians in the link transverse plane @2017-kaushal-survey. Attitude determination and control error and calibrated alignment residuals can be limited to several tens of microradians in a system based on a star tracker @2023-riesing-tbird. By contrast, thermal pointing shifts can be significant for coarse acquisition, depending on the spacecraft bus, optical design, and operating condition @2023-shi-thermal @2024-badas @2025-cheng-isl-thermal. The analyses below likewise produce approximately 150 µrad to more than 1 mrad of thermal shift in LOS angle, depending on the sun face and internal dissipation, making it potentially one of the largest initial pointing error components.

This study focuses on the thermally induced component for two reasons. First, it can be comparable to or larger than other initial error sources. Second, it is governed by known operating conditions, including eclipse cycles, the sun face, surface optical properties, and internal dissipation, and is therefore not a wholly unknown disturbance @2024-badas. The resulting temperature field deforms the spacecraft and changes the relative attitude between the star tracker (STT), which defines the attitude reference, and the laser communication terminal (LCT), which defines the communication optical axis. Before optical feedback is available, this relative change appears as an offset of the coarse acquisition scan center. The model structure is not restricted to a particular orbit class, but low Earth orbit (LEO) is selected for evaluation because its short period and frequent illumination changes create a demanding thermal environment. Under such unstable illumination, periodic time series fitting has been reported to be difficult for LEO remote sensing @2025-li-thermal-los. Demonstrating predictability in this demanding environment also supports the feasibility of applying the approach to more regular thermal environments.

Conventional PAT design absorbs initial pointing uncertainty through the scan range and beacon divergence @2017-kaushal-survey @2023-shi-thermal. The corresponding search burden remains, however, and both thermal deformation and orbit prediction error can contain frequencies near the orbital period of approximately 100 min. Separating the thermal contribution from residuals observed after acquisition by frequency alone is therefore difficult. This motivates feedforward correction based on temperature and operating state before coarse acquisition. The central question is how much of the initial pointing error can be removed using information available before acquisition, rather than by retrospective residual separation.

Optical LOS angle correction using temperature has precedents. For the JUICE/JANUS camera, structural-thermal-optical-performance (STOP) analysis and ground testing established a relationship between a representative structural temperature difference and LOS angle variation @2019-turella-janus-stop @2021-turella-janus. Thermal LOS angle correction based on orbital phase, thermal state, or observation geometry has also been reported for Earth observation satellites @2022-hu-thermal-motion @2025-li-thermal-los. Turella et al. further showed that overall optomechanical deformation, rather than individual optical elements, dominated LOS angle variation @2019-turella-janus-stop. It remains unclear whether spacecraft bus thermal deformation between a separated attitude reference and communication axis can be predicted across orbit, attitude, dissipation, and surface conditions and how such prediction changes coarse acquisition performance.

Accordingly, this paper asks whether (1) the thermally induced STT--LCT LOS angle can be predicted from a small set of temperature and operational variables, (2) model coefficients can be shared across conditions, and (3) scan center correction based on that prediction improves acquisition performance. The study combines thermoelastic analyses of 21 conditions, a hierarchical sun-face $Delta T$ model separating orbital variation from DC differences across conditions, nested leave-one-case-out validation, and PAT acquisition evaluation. The claims are limited to performance across conditions for the same box structure, STT/LCT placement, and LOS angle definition; universality of the numerical coefficients across other structures or flight hardware is not claimed.

#figure(
  problem-schematic,
  caption: [Problem addressed in this study. The thermally induced STT--LCT relative LOS angle is treated as a predictable component of the initial pointing error and is applied as feedforward correction of the scan center before coarse acquisition. Nonthermal errors remain in the residual.],
)<fig_problem>

= RELATED WORK AND POSITIONING OF THIS STUDY

Optical communication PAT studies have addressed pointing error budgets and scan design @2017-kaushal-survey, CubeSat demonstrations in orbit @2023-riesing-tbird, feedforward compensation of attitude and mounting uncertainties @2026-riiddenklau-ff, and beam pointing calibration after acquisition @2019-cierny-calibration. At the spacecraft bus level, Zhang et al. analyzed thermal pointing error between the STT and laser terminal references by finite element analysis @2025-cheng-isl-thermal, while Shi et al. reduced acquisition time by optimizing structural thermal stability and equipment placement @2023-shi-thermal. Those design approaches complement prediction of the residual thermal LOS angle from thermal state before acquisition.

LOS angle correction based on temperature has also been studied for Earth observation satellites and optical systems for deep space. Hu et al. used a diurnal model for a GEO remote sensor @2022-hu-thermal-motion, whereas Li et al. used a neural network with observation geometry as its input under unstable LEO illumination @2025-li-thermal-los. For JANUS, a wall-to-wall temperature difference was related to LOS angle through STOP analysis @2019-turella-janus-stop and the coefficient was validated by ground testing @2021-turella-janus. This paper does not claim novelty for a first-order relationship between temperature and LOS angle itself. Its novelty lies in extending that concept to the relative LOS angle between a separated STT and LCT on a spacecraft bus, hierarchically predicting DC terms that depend on the operating condition, and connecting the prediction to coarse acquisition performance.

#figure(
  spie-table(
    columns: (1.5fr, 1.6fr, 2.2fr, 1.2fr),
    inset: 4pt,
    [Study], [System/domain], [Treatment of thermal deformation error], [Acquisition evaluation],
    [Riesing et al. @2023-riesing-tbird], [CubeSat optical PAT], [Not modeled; absorbed by the attitude system], [Yes; in orbit],
    [Rüddenklau et al. @2026-riiddenklau-ff], [Optical terminal], [Not modeled; FF of attitude/mounting errors], [Yes],
    [Shi et al. @2023-shi-thermal], [Optical communication structural design], [Reduced through structural design], [Yes],
    [Zhang et al. @2025-cheng-isl-thermal], [Inter-satellite optical pointing], [Assessment by finite element analysis and design guidance], [Yes; impact on link establishment],
    [Hu et al. @2022-hu-thermal-motion], [GEO Earth observation], [Compensated by a periodic model], [No],
    [Li et al. @2025-li-thermal-los], [LEO Earth observation], [Learned and corrected by a neural network], [No],
    [Turella et al. @2019-turella-janus-stop @2021-turella-janus], [Camera for deep space], [Proportional model based on temperature difference], [No],
    [*This study*], [*Optical communication spacecraft bus evaluated in LEO*], [*Prediction and correction by a hierarchical sun-face $Delta T$ model*], [*Yes*],
  ),
  caption: [Representative prior studies and the position of this work. Optical communication studies do not predict thermal deformation error, whereas studies of Earth observation and optical instruments do not connect thermal correction to acquisition performance.],
)<tbl_related_overview>

As summarized in @tbl_related_overview, this work lies at the intersection of thermal LOS angle prediction from state and optical communication acquisition evaluation. JANUS addressed the change from a calibrated state within one optical head, whereas this study addresses the STT--LCT relationship across a spacecraft bus, 21 operating conditions, and DC components that are not absorbed by calibration. The present results remain numerical; validation of the coefficients on the ground and in orbit is future work.

= PROBLEM DEFINITION AND LOS ANGLE CONVENTION

For far-field optical communication, the angular error relevant to coarse acquisition is the deviation of the outgoing LCT optical axis in inertial space. When the spacecraft attitude reference is provided by an STT, the STT's own thermal rotation is absorbed into the rotation of the reference frame. The thermally induced communication axis error should therefore be defined as the rotation of the outgoing LCT optical axis relative to the STT attitude reference. Let $bold(theta)_"STT" = (theta_"STT,x", theta_"STT,y")$ and $bold(theta)_"LCT" = (theta_"LCT,x", theta_"LCT,y")$ denote the thermally induced rotations of the STT and LCT about two axes orthogonal to the nominal boresight. The relative rotation is
$
bold(theta)_"th" = bold(theta)_"LCT" - bold(theta)_"STT"
$<eq_los_def>
and is hereafter called the far-field relative LOS angle and used as the primary output.

The centerline tilt obtained from the relative translation between the STT and LCT reference points is not added directly to the outgoing axis error because, for a far-field link, the angular contribution of translation is divided by the target range and is negligible. The far-field pointing error is instead governed by rotation of the local LCT optical axis relative to the STT rotation. Centerline tilt remains useful as a diagnostic measure of structural deformation modes and relative STT/LCT motion and is therefore reported as a secondary quantity.

Let $bold(theta)_"nom"$ be the nominal pointing command and $hat(bold(theta))_"th"$ the predicted relative LOS angle. The coarse acquisition scan center command is applied componentwise as
$
bold(theta)_"scan" = bold(theta)_"nom" - hat(bold(theta))_"th".
$<eq_scan>
The residual after correction is the sum of the nonthermal error and thermal prediction error. The nonthermal term includes orbit prediction error, attitude determination and control error, alignment residuals, counterpart uncertainty, and unmodeled drift. The proposed method does not eliminate all these terms; it first removes the component predictable from thermoelastic analysis and temperature information to reduce the residual region searched during coarse acquisition.

#figure(
  image("figure/fig_los_definition.png", width: 60%),
  caption: [LOS angle convention. The outgoing LCT optical axis rotation relative to the STT attitude frame is used as the thermally induced LOS angle error corresponding directly to the far-field scan center error.],
)<fig_los_def>

= SPACECRAFT MODEL AND THERMOELASTIC ANALYSIS

== Spacecraft model

The analysis uses a bus with a box structure representative of a small satellite (@fig_satellite and @tbl_spacecraft_model). The STT and LCT, providing the attitude reference and communication, respectively, are mounted on the PZ and MZ panels, and PROP and PCDU are included as internally dissipating units. Because the objective is evaluation across conditions rather than design review of a specific spacecraft, the basic structure, equipment placement, and LOS angle convention are fixed across all cases.

#figure(
  image("figure/fig_td_tdall_femap.png", width: 100%),
  caption: [Spacecraft model with a box structure. Left: structural mesh in Femap. Right: Thermal Desktop thermal model showing an example temperature distribution in orbit. The STT is mounted on PZ, the LCT on MZ, and the boresight is approximately along the -Z direction.],
)<fig_satellite>

#figure(
  spie-table(
    columns: (1fr, 2.2fr),
    inset: 4pt,
    [Item], [Setting],
    [Structure], [Bus with a box structure, 0.59 m × 0.60 m × 0.99 m],
    [Panel thickness], [10 mm],
    [Panel material], [A5052 aluminum: Young's modulus 70.3 GPa, Poisson's ratio 0.33, coefficient of thermal expansion $2.38 times 10^(-5)$ /°C, and reference temperature 23.9 °C],
    [Attitude reference (STT)], [Mounted on PZ; 1.5 W dissipation, always ON],
    [Communication terminal (LCT)], [Mounted on MZ; 10 W dissipation, always ON; boresight approximately along -Z],
    [Internal units], [PROP: 25 W on PY; PCDU: 10 W on MY. ON/OFF states vary by case],
  ),
  caption: [Configuration of the spacecraft model with a box structure.],
)<tbl_spacecraft_model>

== Analysis procedure

The thermoelastic analysis consists of thermal analysis, structural response analysis, and LOS angle post-processing. Thermal Desktop first computes a periodic-steady-state temperature field for each case, which is mapped to the structural model through TD Mapper Nastran temperature cards. Femap/Nastran then computes the six components of nodal displacement and rotation due to thermal deformation. The relative LOS angle time series is extracted from the rotations of the representative STT and LCT nodes at their centers. All conditions are managed by a case matrix and a common case identifier. The primary settings are listed in @tbl_analysis_conditions.

#figure(
  spie-table(
    columns: (1fr, 2.2fr),
    inset: 4pt,
    [Item], [Setting],
    [Orbit], [Baseline: COLD case at LTAN06 and 800 km altitude, representing a cold mid-December case with $beta=-58.3°$ and eclipses. Comparisons: HOT, continuously illuminated; and an LTAN18 orbit at 693 km, similar to Sentinel-1],
    [Duration and time step], [18,157 s, approximately three 6,050 s orbits; 60.5 s time step],
    [Thermal environment], [COLD: solar irradiance 1309 W/m², albedo 0.2, and Earth infrared 189 W/m²; HOT/LTAN18: 1414 W/m², 0.4, and 261 W/m²],
    [Surface optical properties], [Baseline: neutral sun face with $alpha=epsilon=0.5$, Black MY panel, and Alodine 1000 on the other panels; comparisons: Black sun face and Alodine on all surfaces],
    [Initial/output thermal condition], [Initial temperature 20 °C. Three orbits are output after Thermal Desktop periodic stabilization; initial transients are excluded from the evaluation],
    [Temperature mapping], [A temperature map is exported by TD Mapper and imported into Femap as Nastran temperature cards],
    [Structural solution and constraints], [Shell elements with a 3--2--1 minimal constraint at reference points near the STT mounting location],
    [LOS angle output], [Relative LOS angle components $(x,y)$ from rotations of the representative STT/LCT nodes at their centers],
  ),
  caption: [Primary Thermal Desktop/Femap thermoelastic analysis settings. A neutral sun face is used in the baseline to compare sun face dependence without conflating coating differences.],
)<tbl_analysis_conditions>

In the deformation budget of a representative case, the mean centerline tilt between the STT and LCT reference points was approximately 206 µrad, the STT rotation contribution approximately 24 µrad, the LCT rotation contribution approximately 475 µrad, and the relative LOS angle approximately 460 µrad. Thus, the relative rotation of several hundred microradians between the STT and LCT is the dominant contribution to the far-field PAT LOS angle.

= CASE MATRIX AND THERMAL LOS ANGLE CHARACTERISTICS

Twenty-one cases span sun faces, internal dissipation, surface optical properties, and orbit conditions (@tbl_case_matrix). The sun face is selected from MX, MY, PX, and PY. PZ and MZ, on which the STT and LCT are mounted, are excluded because they are not illuminated in the attitude family considered. The minimum dissipation configuration includes only the continuously operating STT and LCT; PROP and PCDU are then added separately or together, and one case uses half PROP power, 12.5 W.

#figure(
  spie-table(
    columns: (0.9fr, 1.45fr, 2.5fr),
    inset: 3pt,
    [Case], [Purpose], [Conditions],
    [04--06, 08--09], [Sun face and baseline dissipation], [MX/MY/PX/PY; all units dissipating or STT/LCT only],
    [10], [Orbital thermal environment], [MY, all units dissipating, HOT with continuous illumination],
    [11--12], [Surface optical properties], [MY; Black sun face or Alodine on all surfaces],
    [13--21], [Dissipation mode], [Four sun faces; PROP only, PCDU only, or no additional dissipation],
    [22], [Continuous dissipation level], [MY; PROP at half power, 12.5 W, plus PCDU],
    [23--24], [MX dissipation mode], [MX; PROP only or PCDU only],
    [25], [Orbit condition], [MY, all units dissipating, LTAN18 and 693 km],
  ),
  caption: [Validation matrix of 21 cases. Unless noted otherwise, the COLD orbit and baseline surfaces are used. Additional dissipation excludes the continuously operating STT and LCT.],
)<tbl_case_matrix>

@fig_observation shows the panel temperatures and relative LOS angle for representative Case 04, with MY facing the Sun and all units dissipating. Both temperature and thermal LOS angle vary at the orbital period, and the MY panel temperature follows the y component of the LOS angle closely. This observation motivates the panel temperature difference $Delta T$ used below.

#figure(
  grid(
    columns: (0.92fr, 1.08fr),
    gutter: 8pt,
    image("figure/fig_temp_field_case04.png", width: 100%),
    image("figure/p1_far_field_los_case04.png", width: 93%),
  ),
  caption: [Representative Case 04, with MY facing the Sun and all units dissipating. Left: representative panel temperatures. Right: relative LOS angle components. The temperature field and LOS angle vary at the same orbital period, and the MY panel temperature follows the y component of the LOS angle.],
)<fig_observation>

Three observations summarize the 21 cases. Hereafter, the axis containing most of the orbital variation of the relative LOS angle is termed the dominant axis. First, the raw dominant axis RMS depends strongly on the sun face: approximately 150--265 µrad for MY, 600--670 µrad for PX, 670--730 µrad for MX, and 1180--1280 µrad for PY. Second, the dominant axis switches systematically: it is y for MY/PY and x for PX/MX. Third, surface optical properties affect the variation amplitude and residual floor, with a higher floor for a Black coating, whereas the internal dissipation layout mainly changes the mean bias across cases.

These observations impose two requirements on a reduced-order model. The sun face must be explicit because it changes the dominant axis and sign, and continuous orbital variation must be separated from the offset across cases associated with dissipation mode. The hierarchical sun-face $Delta T$ model below is the smallest model constructed to satisfy both requirements.

= HIERARCHICAL SUN-FACE $Delta T$ MODEL

Running a high-fidelity Thermal Desktop/Femap analysis onboard before every coarse acquisition attempt is impractical. The Thermal Desktop/Femap thermal LOS angle is therefore treated as truth and reduced to a model computable from a small number of temperature and operational inputs. The purpose is not merely to minimize regression error, but to obtain physically interpretable inputs suitable for onboard use.

The most stable decomposition found in the study is as follows. Orbital variation is represented by the difference $Delta T(t)$ between the center temperatures of the sun-facing and opposite panels. Local internal dissipation effects, including PROP and PCDU, are treated as constant case biases rather than additional orbital temperature features. Extensions using mounting point temperatures and local temperature differences were also examined, but their coefficients were unstable because of collinearity with $Delta T(t)$ and low signal-to-noise ratio. The adopted hierarchy therefore assigns orbital variation to $Delta T$ and the remaining dissipation effect to a case bias.

For each case, the panel temperature difference is
$
Delta T(t) = T_"sunface"(t) - T_"opposite"(t).
$<eq_delta_t>
The relative LOS angle $bold(theta)_"th"$ is the vector with two components defined by @eq_los_def. The component containing most orbital variation is denoted $theta_"dom"$; the corresponding component of $hat(bold(theta))_"th"$ is denoted $hat(theta)_"dom"$. Its thermal LOS angle is approximated within a case as
$
theta_"dom"(t) approx b_"case" + a("sun") Delta T(t),
$<eq_level1>
where $a("sun")$ is the sensitivity for each sun face in µrad/°C and $b_"case"$ is the case DC bias in microradians. The bias is required because the LOS angle need not be zero at $Delta T=0$ and because mounting and local dissipation leave residual terms.

The non-dominant axis has only several microradians RMS variation about its case mean and is therefore modeled without a time-varying term; only its constant case DC bias $b_"nd"$ is corrected. That bias nevertheless depends systematically on the sun face and is non-negligible: approximately $-600$ µrad for MX/PX and $+20$ µrad for MY/PY in this model. Setting it to zero severely degrades coarse acquisition performance, so $b_"nd"$ is predicted by the same Level 2 framework as the dominant axis bias.

The dominant and non-dominant axis biases, $b_"case"$ and $b_"nd"$, are modeled across cases using sun face dummy variables and dissipation flags:
$
b_"case" approx b_0("sun") + c_"prop" I_"prop" + c_"pcdu" I_"pcdu".
$<eq_level2>
Here $I_"prop"$ and $I_"pcdu"$ equal one when the corresponding unit is ON and zero otherwise. Additional dissipating units can be incorporated by adding analogous terms, so the parameter count increases linearly with the number of units. The form in @eq_level2 is fitted independently for the two axes. Because PROP and PCDU are mounted on the $plus.minus Y$ panels, their effect appears primarily in the y component of the LOS angle. The flag terms are therefore enabled for the dominant axis bias in MY/PY cases, where y is dominant, and for the non-dominant axis bias in MX/PX cases, where y is non-dominant. For prediction, the median of the independently fitted $a_"emp"$ values for each sun face is used as the shared sensitivity $a_"shared"("sun")$:
$
hat(theta)_"dom"(t) =
b_"pred"("sun", I_"prop", I_"pcdu")
+ a_"shared"("sun") Delta T(t).
$<eq_predict>
The fixed model contains 16 scalar coefficients: four $a$ coefficients, eight $b_0$ coefficients for the two axes, and four dissipation flag coefficients for the two axes.

#figure(
  model-schematic,
  caption: [Structure of the hierarchical sun-face $Delta T$ model. The panel temperature difference $Delta T(t)$ represents orbital variation, while sun face dummy variables and internal dissipation flags predict the DC bias across cases not captured by $Delta T$.],
)<fig_model>

The coefficients are identified in two stages. First, @eq_level1 is fitted to the first orbit of each case to estimate empirical $a_"emp"$ and $b_"emp"$ values; for the non-dominant axis, the training orbit mean is used as the empirical $b_"nd"$. Second, @eq_level2 is fitted by ordinary least squares across cases. Generalization is evaluated by nested leave-one-case-out (nested LOO): the test case is removed from the Level 2 bias fit, from the calculation of $a_"shared"$, and from the non-dominant axis $b_"nd"$ fit. Thus, no coefficient specific to the evaluated case is known in advance.

Across the 21 cases, the shared sensitivities for MX, MY, PX, and PY were $+30.6$, $+28.6$, $-28.1$, and $-28.7$ µrad/°C, respectively (@tbl_coefficients). Their magnitudes cluster at approximately 28--31 µrad/°C, and their signs follow the sun face and dominant axis direction. The coefficients were not forced to agree; the independently estimated values clustered by sun face, supporting their use as shared coefficients for this spacecraft model, LOS angle definition, and case set.

#figure(
  spie-table(
    columns: (1.6fr, 1fr, 1fr, 1fr, 1fr),
    inset: 4pt,
    [Coefficient], [MX], [MY], [PX], [PY],
    [Shared sensitivity $a_"shared"$ [µrad/°C]], [$+30.6$], [$+28.6$], [$-28.1$], [$-28.7$],
    [Baseline bias $b_0$, dominant axis [µrad]], [$+15.7$], [$+2.8$], [$-12.0$], [$-24.0$],
    [Baseline bias $b_0$, non-dominant axis [µrad]], [$-594$], [$+16.6$], [$-596$], [$+25.1$],
  ),
  caption: [Identified coefficients of the hierarchical sun-face $Delta T$ model. The dissipation flag coefficients were $c_"prop"=-22.9$ µrad and $c_"pcdu"=-10.2$ µrad for the dominant axis and $c_"prop"=-131$ µrad and $c_"pcdu"=+22.1$ µrad for the non-dominant axis. The flag terms apply only to MY/PY cases on the dominant axis and MX/PX cases on the non-dominant axis.],
)<tbl_coefficients>

The dissipation coefficients represent the DC residual after the panel temperature difference contribution has been removed; they do not directly indicate the physical deformation direction caused by heating. Level 2 also reproduced the non-dominant axis bias across sun faces, with a nested LOO RMSE of 3.1 µrad and a maximum error of 5.3 µrad.

#figure(
  grid(
    columns: (1fr, 0.86fr),
    gutter: 8pt,
    image("figure/p3_a_emp_by_sunface.png", width: 100%),
    image("figure/p3_b_emp_vs_b_pred.png", width: 100%),
  ),
  caption: [Behavior of the hierarchical sun-face $Delta T$ model across conditions. Left: independently estimated $a_"emp"$ values cluster by sun face and support a shared sensitivity. Right: empirical $b_"emp"$ versus Level 2 $b_"pred"$ on the dominant axis. The dominant axis bias RMSE is approximately 3.1 µrad for the fitted cases and 3.8 µrad under leave-one-case-out; on the non-dominant axis, it is approximately 3.1 µrad.],
)<fig_p3>

#figure(
  image("figure/p2_bcase_true_vs_pred_case08.png", width: 95%),
  caption: [Example prediction for a case with PY facing the Sun. The model follows the large orbital thermal LOS angle variation using $b_"pred" + a_"shared" Delta T(t)$.],
)<fig_ts>

For the standard COLD orbit and baseline surfaces, the dominant axis test RMSE was generally 3--7 µrad. In the PY case with all dissipating units operating, for example, the raw RMS was approximately 1250 µrad and the RMSE after model correction approximately 4 µrad. For MX, a raw RMS of approximately 670--730 µrad was reduced to approximately 3 µrad; for PX, approximately 600--670 µrad was reduced to 5--6 µrad. The MY dissipation series had a smaller raw RMS of approximately 150--260 µrad and an RMSE after model correction of 6--7 µrad, close to the Level 1 time-varying residual floor. Across all 21 cases, the nested LOO dominant axis test RMSE had a median of approximately 4.9 µrad and a mean of approximately 5.5 µrad, one to two orders of magnitude below the median raw RMS of approximately 615 µrad. The LTAN18/693 km case similar to Sentinel-1 also had a small test RMSE of approximately 1.2 µrad, indicating that the model structure remained effective under the different orbit condition.

The limitations are also clear. A Black coating increased the residual variation to approximately 13 µrad, and the HOT orbit left a DC offset of several microradians. In the case with PROP at half power, the ON/OFF flag assigned the same input as PROP at full power and could not represent continuous dissipation, increasing the nested LOO residual to approximately 16 µrad. The main result is therefore the reduction by one to two orders of magnitude obtained with 16 fixed coefficients, centered on the standard COLD conditions. Explicit treatment of coating, orbit, and continuous dissipation remains future work.

= PAT COARSE ACQUISITION EVALUATION

To evaluate communication system effects, the thermal LOS angle prediction is connected to a coarse acquisition simulator using a rectangular spiral. The simulator takes the Thermal Desktop/Femap thermal LOS angle as truth and computes acquisition success and time for each scan center correction method. Acquisition occurs when the true target direction lies within the detection radius of a scan point. Acquisition time is therefore a practical proxy for the residual initial pointing uncertainty after correction.

#figure(
  pat-schematic,
  caption: [PAT evaluation flow. The Thermal Desktop/Femap LOS angle is used as thermal truth, connected to feedforward scan center correction by the reduced-order model, and evaluated through acquisition time in a rectangular spiral scan.],
)<fig_pat_flow>

== Scan conditions

The scan conditions in @tbl_scan_conditions represent coarse acquisition with a beacon instantaneous field of view rather than the narrow communication beam. A detection radius of 150 µrad is half the width of the approximately 0.3 mrad beacon field, and a 120 µrad step provides 60% overlap @2023-shi-thermal. Half the grid diagonal, $120 / sqrt(2) approx 85$ µrad, is smaller than the detection radius, so the scan region has no coverage holes. A range of ±1600 µrad allows margin for the largest thermal LOS angle, approximately 1.2--1.3 mrad for PY, combined with nonthermal error. These times are proxies: a 0.2 s dwell as in Shi et al. would double all times but preserve their relative ordering.

#figure(
  spie-table(
    columns: (1.4fr, 1fr, 1.6fr),
    inset: 4pt,
    [Item], [Value], [Basis],
    [Scan range], [±1600 µrad], [Covers the approximately 1.3 mrad maximum thermal LOS angle plus nonthermal error],
    [Scan step], [120 µrad], [60% overlap for an approximately 0.3 mrad beacon field],
    [Detection radius], [150 µrad], [Beacon coarse field of view @2023-shi-thermal],
    [Dwell time], [0.1 s/point], [Representative beacon integration time],
    [Number of points], [729, or 27×27], [Maximum full scan time of 72.9 s],
  ),
  caption: [Coarse acquisition scan conditions. A rectangular spiral is assumed; slew and settling between scan points and stochastic received power variation are neglected.],
)<tbl_scan_conditions>

== Nonthermal error model

A synthesized nonthermal error represents a more operationally representative condition. The latest Sentinel-1 TLE is propagated with SGP4; its position error relative to a precise orbit ephemeris (POEORB) is projected onto the link transverse plane, converted to angular error in the STT/body x--y frame, and mapped periodically onto the evaluation interval. The model also includes a constant alignment residual with $1 sigma=50$ µrad, random attitude determination and control error with $1 sigma=50$ µrad, and low-frequency drift of 30 µrad amplitude and 900 s period. Rather than reproducing a specific spacecraft error budget, this synthesis represents coexisting errors on a small LEO satellite without GNSS. Both the thermal LOS angle and orbit prediction error vary at frequencies near the orbital period of approximately 100 min, so frequency separation after observation cannot isolate the thermal component. This motivates feedforward correction based on temperature and operational state.

== Results

We compare no correction, correction by the hierarchical sun-face $Delta T$ model in @eq_predict, and thermal truth correction as an ideal upper bound. Nested LOO excludes the evaluated case from the shared sensitivity and both Level 2 axis bias estimates. We evaluate 17 COLD cases with baseline surfaces, Cases 4--6 and 8--21.

#figure(
  spie-table(
    columns: (2.0fr, 1.4fr, 1.4fr, 1.4fr),
    inset: 4pt,
    [Condition], [No correction], [Hierarchical sun-face $Delta T$ model], [Thermal truth],
    [Thermal only: mean acquisition time], [12.1 s], [0.10 s], [0.10 s],
    [Thermal only: success rate], [100%], [100%], [100%],
    [With nonthermal error: mean acquisition time], [16.3 s], [4.74 s], [--],
    [With nonthermal error: success rate], [98.3%], [100%], [--],
  ),
  caption: [Mean coarse acquisition performance over 17 cases. With thermal error only, correction by the hierarchical sun-face $Delta T$ model requires one scan point, one dwell of 0.1 s, and matches the ideal thermal truth upper bound. With nonthermal error, it reduces the mean acquisition time from 16.3 to 4.74 s, approximately 71%, and increases the success rate from 98.3% to 100%.],
)<tbl_pat_results>

With thermal error only, the hierarchical sun-face $Delta T$ model yields a mean acquisition time of 0.10 s, matching thermal truth correction because acquisition occurs at the first scan point. The mean thermal residual across the two axes after correction is 9.0 µrad, well below the 150 µrad detection radius. The model removes the case DC term through $b_"pred"$ and the orbital variation through $a Delta T(t)$.

With nonthermal error, correction reduces the mean acquisition time from 16.3 to 4.74 s. The mean initial error after correction is 421 µrad and is almost entirely dominated by nonthermal error. The role of the method is therefore not to eliminate total pointing error, but to remove the large time-varying thermal bias and reduce the search burden to the nonthermal error level.

The improvement varies by sun face. It is small for MY, whose thermal LOS angle is 150--260 µrad, while the large orbit prediction error for PX/MX, whose thermal LOS angle is 0.6--0.9 mrad, determines the floor after correction. For PY, whose thermal LOS angle is approximately 1.2 mrad, the acquisition time and success rate improve from 37.3--39.5 s and 88--97% to 1.3--1.8 s and 100%, respectively. The benefit is thus largest under the most severe thermal deformation conditions.

== Preliminary residual update

The primary feedforward (FF) method uses only temperature and operational information available before acquisition. As a supplementary study, the residual on the dominant axis after acquisition, $r(t)=theta_"dom"(t)+e_"nth"(t)-hat(theta)_"dom"(t)$, is represented by a Fourier series in orbital phase $phi=2 pi t \/ T_"orb"$, and coefficients identified during orbit $n$ are applied to orbit $n+1$. This is not re-identification of the thermal model, but a preliminary operational correction of periodic error remaining after FF:
$
hat(r)(phi) = c_0 + sum_(k=1)^(K) [ a_k cos(k phi) + b_k sin(k phi) ].
$<eq_resid_fourier>
The $K=2$ coefficients are estimated by ridge regression, with no update applied during the first orbit. Two representative cases are compared against direct Fourier fitting of total error, in which Fourier fitting is applied to the total error without FF (@tbl_residual_update).

#figure(
  spie-table(
    columns: (2.2fr, 1.2fr, 1.2fr, 1.2fr),
    inset: 4pt,
    [Method], [All data], [First orbit, orbit 0], [Orbit 1 onward],
    [*Case 13 (MY)*], [], [], [],
    [FF only], [1.64 s], [1.60 s], [1.66 s],
    [Direct Fourier fitting of total error], [1.39 s], [3.37 s], [0.39 s],
    [FF + residual Fourier], [0.79 s], [1.60 s], [0.38 s],
    [*Case 16 (PY)*], [], [], [],
    [FF only], [1.55 s], [1.47 s], [1.59 s],
    [Direct Fourier fitting of total error], [13.2 s, 98.7% success], [39.5 s], [0.38 s],
    [FF + residual Fourier], [0.76 s], [1.47 s], [0.40 s],
  ),
  caption: [Comparison of residual updates with nonthermal error, causal fitting, and $K=2$. Direct Fourier fitting of total error reaches the floor from orbit 1 onward but is uncorrected in the first orbit; for the large thermal LOS angle of PY, its acquisition time in the first orbit exceeds the requirement of approximately 30 s. FF + residual Fourier preserves FF performance from the first orbit and reduces the floor to approximately 0.4 s from orbit 1 onward.],
)<tbl_residual_update>

From orbit 1 onward, both Fourier approaches reach approximately 0.4 s. Direct Fourier fitting of total error, however, is uncorrected in the first orbit and requires 39.5 s for Case 16, whose thermal LOS angle is approximately 1 mrad. Combining FF with the residual update preserves FF performance in the first orbit and reduces the periodic floor in subsequent orbits. A separate update of only the constant residual component reduced the DC residual but left the AC floor at the orbital period, improving Case 13 from 1.66 to 1.35 s from orbit 1 onward, compared with 0.38 s for residual Fourier. This difference provides the quantitative basis for using a periodic model in the second layer. Nevertheless, this evaluation uses only two cases, with all samples at intervals of 60.5 s, residuals at failed acquisition points, and periodically mapped orbit error. Performance with sparse observations available only after successful acquisitions has not been demonstrated.

Operationally, coarse acquisition for a particular counterpart and orbit is often effectively a first encounter. The FF prediction by the hierarchical sun-face $Delta T$ model can be applied immediately from temperature and operating state without residual learning. After successful acquisitions have accumulated residual observations, recurrent components can be carried to later opportunities. This ordering avoids a burdensome first acquisition while permitting a lower recurrent residual floor.

= DISCUSSION AND CONCLUSION

The temperature difference between the panel facing the Sun and the opposite panel represents structural bending during an orbit, while the bias that remains constant within each case represents DC differences among conditions caused by local dissipation and related effects. This separation represents the thermal LOS angle across multiple sun faces and dissipation modes with 16 coefficients. The contribution is not the first-order temperature model itself, but its application to the STT--LCT relative LOS angle at the spacecraft bus level, coefficient sharing across conditions, and connection to coarse acquisition time.

The shared sensitivity is an empirical coefficient specific to the present structure, placement, LOS angle definition, and case set, and must be re-identified for another configuration. In operation, $Delta T$ is assumed to be obtained from temperature sensors at the centers of the panel facing the Sun and the opposite panel. With a sensitivity of approximately 30 µrad/°C, an error of 0.1 °C in the temperature difference corresponds to approximately 3 µrad. Sensor placement, delay, and quantization nevertheless require future error analysis. Orbit, attitude, and alignment errors also leave a floor of several hundred microradians after thermal correction, so the method is intended to reduce the search region in conjunction with treatment of those errors.

The evaluation is limited to numerical analysis of one box structure and includes no ground test. Residuals increase for some coating and orbit conditions, and both the nonthermal error and scan models are simplified. Slew and settling between scan points and probabilistic detection are neglected. The residual Fourier update remains a preliminary evaluation of two cases with dense sampling.

In conclusion, the mean nested LOO RMSE on the dominant axis is 5.5 µrad, compared with a median raw LOS angle RMS of 615 µrad. Across 17 cases, the mean acquisition time is reduced from 12.1 to 0.10 s with thermal error only and from 16.3 to 4.74 s with nonthermal error. Future work will incorporate coating, orbit, and continuous dissipation into Level 2, validate the coefficients by ground testing, and extend the residual update to sparse successful observations and all cases.

#bibliography(
  "bibliography.bib",
  title: [REFERENCES],
  style: "bibstyle.csl",
)
