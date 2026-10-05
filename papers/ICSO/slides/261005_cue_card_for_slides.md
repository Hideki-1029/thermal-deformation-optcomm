# ICSO 2026 Presentation Script

## Slide 1 — Title

Good afternoon.
My name is Hideki Takamoto from the University of Tokyo.

Today, I will present our work on hierarchical prediction and feedforward correction of time-varying thermal line-of-sight bias for coarse acquisition in satellite optical communications.


## Slide 2 — Background

First, I will briefly explain the background and motivation of this study.


## Slide 3 — Before optical feedback is available

Before acquisition, optical feedback from the other terminal is not yet available.

Therefore, the terminal has to search an uncertainty region that includes thermal LOS error, attitude error, and orbit-prediction error.

In particular, illumination, eclipse, and internal dissipation generate temperature gradients in the spacecraft.
These gradients cause thermal expansion and spacecraft-bus distortion, which can result in thermal LOS errors on the order of hundreds of microradians or even more than one milliradian.

Our approach is to predict this thermal component before acquisition and subtract it from the scan center.

The important point is that this is an operational correction.
It does not require modification of the spacecraft structure or the laser communication terminal.


## Slide 4 — Error sources during coarse acquisition

This table summarizes the main error sources contributing to the scan-center LOS error during coarse acquisition.

Among these components, thermal LOS error can be comparable to, or even larger than, orbit-prediction error.

Another important point is that thermal LOS error and orbit-prediction error vary on similar orbital time scales.

Therefore, after acquisition, we cannot simply identify the thermal component from the pointing residual based on frequency.

Instead, in this study, we use temperature and operating-state information as independent inputs to predict and remove the thermal component before acquisition.


## Slide 5 — Prior work and positioning of this study

I compare previous studies from two main perspectives:
what thermal LOS is modeled, and how that prediction is connected to system-level performance.

Previous optical-communication studies mainly reduce thermal deformation through structural design, or assess its effect on pointing and link establishment.

On the other hand, studies in Earth observation and optical instruments have predicted and corrected thermal LOS variation using temperature, orbital phase, or observation geometry.

Our work differs in three main aspects.

First, we predict the relative LOS between the star tracker and the laser communication terminal across the spacecraft bus.

Second, rather than fitting an independent model for every operating condition, we construct a model whose thermal sensitivities are shared across multiple thermal and operating conditions.

Third, we directly apply the predicted LOS to the coarse-acquisition scan center and evaluate the resulting acquisition time and success rate.

So, the novelty is not the temperature-to-LOS relationship itself, but its application to bus-level STT–LCT relative LOS, its generalization across operating conditions, and its direct connection to coarse-acquisition performance.


## Slide 6 — Research overview

This slide shows the overall workflow of this study.

On the ground, we first define the orbit, attitude, thermal environment, equipment layout, and surface properties.

Thermal Desktop is then used to calculate the spacecraft temperature field.

The temperature field is transferred to Femap and Nastran to calculate thermoelastic deformation and the relative rotation between the star tracker and the laser communication terminal.

From these high-fidelity simulation results, we generate reference thermal-LOS time series and construct a reduced-order prediction model.

On orbit, Thermal Desktop and Femap are not used.

Only temperature measurements and operating-state information are input to the reduced-order model, and the predicted thermal LOS is used to correct the scan center.

Finally, we evaluate not only the LOS prediction error, but also acquisition success rate and acquisition time.


## Slide 7 — Thermoelastic analysis

Next, I will explain the thermoelastic analysis used to generate the reference thermal-LOS data.


## Slide 8 — Spacecraft analysis model

We evaluate a simple box-structure LEO spacecraft, with the star tracker and the laser communication terminal mounted on different panels.

The spacecraft bus is approximately 0.6 by 0.6 by 1 meter and is modeled using A5052 aluminum shell elements.

The star tracker is located on the positive-Z panel, and the laser communication terminal is located on the negative-Z panel.

This model is not intended to reproduce a specific flight spacecraft.

Instead, we keep the structure fixed and vary the thermal and operating conditions in order to investigate the thermal LOS behavior.


## Slide 9 — Thermal analysis

First, Thermal Desktop is used to calculate the time history of the spacecraft temperature field.

The baseline orbit is a sun-synchronous orbit at an altitude of 800 kilometers.

We simulate approximately three orbital periods with about one-minute sampling.

Across the analysis cases, we vary the sun-facing panel, eclipse condition, surface optical properties, internal equipment dissipation, and orbital conditions.

The output of this analysis is the panel temperature field as a function of time.

Again, this analysis is performed only on the ground.


## Slide 10 — Structural analysis

The resulting temperature field is then transferred to Femap for thermoelastic structural analysis.

The spacecraft structure is modeled using A5052 aluminum with the material properties shown here.

From this analysis, we obtain the translations and rotations of the star-tracker and laser-terminal mounting locations.

Thermal Desktop and Femap are therefore used only to generate the high-fidelity reference dataset for model development.


## Slide 11 — Definition of thermal LOS error

For a far-field optical link, the relevant quantity is not simply the translation of the mounting points.

What matters is the relative rotation of the laser communication terminal optical axis with respect to the star-tracker attitude reference.

Therefore, we define the thermal LOS error as the LCT optical-axis rotation minus the STT reference rotation.

The thermal rotation of the star tracker itself is absorbed into the attitude reference.

In this study, translation-induced tilt and the internal thermal deformation of the optical terminals are not included.


## Slide 12 — Analysis cases

With the spacecraft structure and LOS definition fixed, we vary four groups of conditions.

These are the sun-facing panel, internal equipment dissipation, surface properties, and orbital thermal environment.

In total, we analyze 21 cases.

The important point is that these are different thermal and operating conditions within the same spacecraft configuration.

We are not assuming that the numerical coefficients identified here can be transferred unchanged to a completely different spacecraft.


## Slide 13 — Thermoelastic analysis results

This slide shows one representative result.

Both the spacecraft temperature and the thermal LOS vary approximately with the orbital period.

We also found that the dominant LOS axis depends strongly on the sun-facing panel.

For MY and PY sun-facing cases, the dominant variation appears mainly in the y direction, while MX and PX mainly affect the x direction.

Most importantly, the time-varying thermal LOS closely follows the temperature difference between the sun-facing panel and the opposite panel.

Across all cases, the raw thermal LOS ranges from approximately 150 to 1280 microradians.

We also observed that the surface thermal condition mainly affects the time-varying amplitude, while internal dissipation mainly shifts the mean bias.

This observation motivates the reduced-order model shown next.


## Slide 14 — Reduced-order model

Next, I will introduce the reduced-order thermal-LOS prediction model.


## Slide 15 — Reduced-order model selection

For onboard use, the model has to be much simpler than the full Thermal Desktop and Femap analysis.

It should use only a small number of temperature measurements and operating-state flags, with a small fixed set of coefficients.

We examined several candidate models.

A constant bias cannot represent the within-orbit variation.

A Fourier model can represent periodicity, but it becomes dependent on the particular orbit and operating condition.

Using many local temperature measurements gives more flexibility, but we found strong collinearity between those temperatures and the panel temperature difference.

Based on these observations, we selected a hierarchical temperature-difference model.

The basic idea is to separate the time-varying thermal component within an orbit from the mean bias that changes across operating conditions.


## Slide 16 — Reduced-order model formulation

This is the core prediction model.

The coefficients of this model are identified on the ground from the thermo-structural simulation database.

For the dominant LOS axis, the time-varying component is modeled as a linear function of the temperature difference between the sun-facing panel and the opposite panel.

The thermal sensitivity, a, is shared among cases with the same sun-facing panel.

The remaining DC offset, b, is modeled using the sun-facing panel and equipment ON/OFF states.

So, in simple terms, the panel temperature difference explains the variation within an orbit, while the operating state explains the offset between different cases.

For the non-dominant axis, only the bias component is predicted.

The complete model uses only 16 coefficients for this spacecraft structure, STT–LCT placement, and LOS definition.


## Slide 17 — How the coefficients are identified and evaluated

Let me briefly explain how the coefficients a and b are determined.

First, for each analysis case, we use the first orbit to fit the relationship between the panel temperature difference and the thermal LOS.

This gives a case-specific thermal sensitivity, a, and a mean offset, b.

Next, the thermal sensitivity a is shared across cases with the same sun-facing panel.
We use the median sensitivity of those cases as the shared coefficient.

The mean offset b is treated differently.
Instead of assigning an independent offset to every case, we model it using the sun-facing panel and equipment ON/OFF states.

Therefore, the final onboard model does not require independent coefficients for every operating condition.

To evaluate prediction under unseen conditions, we use a nested leave-one-case-out procedure.

The test case is completely excluded from both the shared thermal-sensitivity estimation and the DC-bias model.

Then, using only the fixed coefficients obtained from the remaining cases, we predict the excluded case and evaluate its next two orbits.

So, this evaluates generalization to an unseen operating condition within the same spacecraft configuration.


## Slide 18 — Prediction performance for unseen cases

The prediction results are shown here.

Before correction, the median RMS thermal LOS on the dominant axis is about 615 microradians.

For unseen operating conditions, the median test RMSE decreases to only 4.9 microradians, with a mean value of 5.5 microradians.

The case-dependent DC bias is also predicted with a leave-one-out RMSE of 3.8 microradians.

Therefore, within the evaluated conditions, this relatively simple reduced-order model reduces the dominant thermal LOS error by approximately one to two orders of magnitude.


## Slide 19 — Representative severe thermal case

This slide shows Case 08, which is one of the cases with the largest thermal LOS error.

The raw dominant-axis thermal LOS RMS is about 1250 microradians.

Even though this case is excluded from coefficient estimation, the prediction RMSE is only 3.9 microradians.

As shown in the time series, the panel temperature difference successfully follows the large within-orbit variation of the thermal LOS.

This remaining error is already much smaller than the 150-microradian detection radius used in the coarse-acquisition simulation.


## Slide 20 — Coarse-acquisition evaluation

Finally, I will evaluate how this thermal-LOS prediction affects coarse-acquisition performance.


## Slide 21 — Acquisition simulation

The predicted thermal LOS is used directly to shift the center of the coarse-acquisition scan.

The scan-center error consists of nonthermal pointing errors plus the difference between the true thermal LOS and the predicted thermal LOS.

We use a simplified rectangular spiral scan.

The scan range is plus or minus 1600 microradians, the scan step is 120 microradians, the detection radius is 150 microradians, and the dwell time is 0.1 seconds per point.

Because half of the grid diagonal is smaller than the detection radius, the scan geometry has no coverage holes.

In this numerical evaluation, inter-point motion, settling time, and probabilistic detection are neglected.

Therefore, the absolute acquisition times should be interpreted as comparative values under the same scan conditions.


## Slide 22 — Nonthermal error model

In addition to thermal LOS error, we include several nonthermal pointing-error components.

The largest one is orbit-prediction error.

We generate this error by propagating Sentinel-1 TLE data and comparing the predicted position with precise POEORB ephemeris data, and then projecting the resulting position error onto the link transverse plane.

We also include a constant alignment error, random attitude error, and a low-frequency drift term.

This is not intended to reproduce the exact pointing-error budget of a specific spacecraft.

Instead, it represents a generic small-LEO scenario without high-accuracy GNSS-based onboard orbit knowledge.


## Slide 23 — Acquisition with thermal error only

First, I show the acquisition result when only thermal LOS error is included.

Without correction, the mean acquisition time is 14.6 seconds.

With the hierarchical reduced-order model, the mean acquisition time decreases to 0.10 seconds.

This is the same acquisition time obtained when the true thermal LOS is directly removed.

However, this does not mean that the predicted waveform is perfectly identical to the thermal truth.

It simply means that the remaining thermal residual, about 9 microradians on average, is already well inside the 150-microradian detection radius.


## Slide 24 — Acquisition with nonthermal errors

The more important result is obtained when the nonthermal errors are also included.

Without thermal correction, the mean acquisition time is 19.2 seconds, with a success rate of 98 percent.

With the feedforward thermal correction, the mean acquisition time decreases to 5.45 seconds.

This corresponds to a 72 percent reduction, and the success rate increases to 100 percent.

For the PY sun-facing cases, where the thermal LOS reaches approximately 1.2 milliradians, the acquisition time decreases from around 40 seconds to approximately 1 to 2 seconds.

After correction, the remaining initial pointing error is about 448 microradians and is almost entirely determined by the nonthermal components.

Therefore, the role of this method is not to eliminate every pointing error.

Instead, it removes the predictable thermal component before optical feedback becomes available, shifting the dominant acquisition limitation from thermal error to nonthermal error.


## Slide 25 — Preliminary residual update

Finally, as a preliminary extension, we also examined the use of post-acquisition pointing residuals for repeated links.

For the first acquisition, temperature-based prediction is important because previous optical residuals may not be available.

After successful acquisition, however, periodic information contained in the residual can be used to reduce the remaining error in later orbits.

In the two numerical cases shown here, combining the feedforward thermal model with a Fourier model of the residual reduces later-orbit acquisition time further.

However, this is only a preliminary study.

The thermal-model coefficients themselves are not updated, and the analysis currently uses only two cases with densely sampled residual data.

Therefore, the primary result of this work remains the pre-acquisition feedforward correction based on temperature and operating-state information.


## Slide 26 — Summary

Finally, I will summarize the results and discuss the current limitations.


## Slide 27 — Limitations and future work

There are several limitations to the current study.

First, the validation is entirely numerical and is limited to the same spacecraft structure and LOS definition.

Second, ground-test validation has not yet been performed, so the flight relevance of the thermo-structural model and the identified thermal sensitivities remains to be demonstrated.

Third, the LOS is calculated using representative-node rotations.
A rigid-body fit of the mounting interface and internal thermal deformation of the STT and LCT are not included.

Finally, the acquisition simulation uses one nonthermal-error realization and simplified scan dynamics.

The thermal sensitivity of approximately 30 microradians per Kelvin is therefore specific to this spacecraft configuration.

There are three main directions for future work.

First, we plan to validate the thermo-structural sensitivities through ground thermal testing.

Second, for application to an actual spacecraft, the coefficients must be re-identified for the real structure and mounting configuration, while we investigate whether the same model structure can be retained.

Third, after successful acquisition, optical pointing residuals could be used to adapt or update the prediction for repeated links.


## Slide 28 — Summary

To summarize, we treated thermal deformation as a predictable time-varying LOS bias before coarse acquisition.

First, using panel temperature differences and operating-state information, the median dominant-axis thermal LOS error for unseen operating conditions was reduced from about 615 microradians to 4.9 microradians.

Second, when only thermal error was considered, the mean acquisition time decreased from 14.6 seconds to 0.10 seconds.

Finally, even when nonthermal errors were included, the mean acquisition time decreased from 19.2 seconds to 5.45 seconds, while the success rate increased from 98 percent to 100 percent.

The main contribution of this work is to predict the STT–LCT relative LOS across the spacecraft bus using a model that generalizes across multiple operating conditions, and to directly connect that prediction to coarse-acquisition performance.

By removing the predictable thermal component before optical feedback becomes available, the remaining acquisition problem becomes dominated by nonthermal errors.

Thank you very much for your attention.