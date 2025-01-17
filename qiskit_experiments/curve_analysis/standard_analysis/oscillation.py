# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Analyze oscillating data such as a Rabi amplitude experiment."""

from typing import List, Union

import numpy as np

import qiskit_experiments.curve_analysis as curve


class OscillationAnalysis(curve.CurveAnalysis):
    r"""Oscillation analysis class based on a fit of the data to a cosine function.

    # section: fit_model

        Analyse oscillating data by fitting it to a cosine function

        .. math::

            y = {\rm amp} \cos\left(2 \pi\cdot {\rm freq}\cdot x + {\rm phase}\right) + {\rm base}

    # section: fit_parameters
        defpar \rm amp:
            desc: Amplitude of the oscillation.
            init_guess: Calculated by :func:`~qiskit_experiments.curve_analysis.guess.max_height`.
            bounds: [-2, 2] scaled to the maximum signal value.

        defpar \rm base:
            desc: Base line.
            init_guess: Calculated by :func:`~qiskit_experiments.curve_analysis.\
            guess.constant_sinusoidal_offset`.
            bounds: [-1, 1] scaled to the maximum signal value.

        defpar \rm freq:
            desc: Frequency of the oscillation. This is the fit parameter of interest.
            init_guess: Calculated by :func:`~qiskit_experiments.curve_analysis.\
            guess.frequency`.
            bounds: [0, inf].

        defpar \rm phase:
            desc: Phase of the oscillation.
            init_guess: Zero.
            bounds: [-pi, pi].
    """

    __series__ = [
        curve.SeriesDef(
            fit_func=lambda x, amp, freq, phase, base: curve.fit_function.cos(
                x, amp=amp, freq=freq, phase=phase, baseline=base
            ),
            plot_color="blue",
            model_description=r"{\rm amp} \cos\left(2 \pi\cdot {\rm freq}\cdot x "
            r"+ {\rm phase}\right) + {\rm base}",
        )
    ]

    def _generate_fit_guesses(
        self, user_opt: curve.FitOptions
    ) -> Union[curve.FitOptions, List[curve.FitOptions]]:
        """Compute the initial guesses.

        Args:
            user_opt: Fit options filled with user provided guess and bounds.

        Returns:
            List of fit options that are passed to the fitter function.
        """
        curve_data = self._data()
        max_abs_y, _ = curve.guess.max_height(curve_data.y, absolute=True)

        user_opt.bounds.set_if_empty(
            amp=(-2 * max_abs_y, 2 * max_abs_y),
            freq=(0, np.inf),
            phase=(-np.pi, np.pi),
            base=(-max_abs_y, max_abs_y),
        )
        user_opt.p0.set_if_empty(
            freq=curve.guess.frequency(curve_data.x, curve_data.y),
            base=curve.guess.constant_sinusoidal_offset(curve_data.y),
        )
        user_opt.p0.set_if_empty(
            amp=curve.guess.max_height(curve_data.y - user_opt.p0["base"], absolute=True)[0],
        )

        options = []
        for phase_guess in np.linspace(0, np.pi, 5):
            new_opt = user_opt.copy()
            new_opt.p0.set_if_empty(phase=phase_guess)
            options.append(new_opt)

        return options

    def _evaluate_quality(self, fit_data: curve.FitData) -> Union[str, None]:
        """Algorithmic criteria for whether the fit is good or bad.

        A good fit has:
            - a reduced chi-squared lower than three,
            - more than a quarter of a full period,
            - less than 10 full periods, and
            - an error on the fit frequency lower than the fit frequency.
        """
        fit_freq = fit_data.fitval("freq").value
        fit_freq_err = fit_data.fitval("freq").stderr

        criteria = [
            fit_data.reduced_chisq < 3,
            1.0 / 4.0 < fit_freq < 10.0,
            (fit_freq_err is None or (fit_freq_err < fit_freq)),
        ]

        if all(criteria):
            return "good"

        return "bad"
