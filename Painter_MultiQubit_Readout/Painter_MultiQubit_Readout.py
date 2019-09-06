import Labber
import numpy as np
from scipy.interpolate import interp1d
import InstrumentDriver

class Driver(InstrumentDriver.InstrumentWorker):
    """This class implements PulseCorrection."""

    def performOpen(self, options={}):

        # initialize variables
        self.n_record = 0
        self.n_qubit = 0
        self.z0 = None
        self.z1 = None
        self.single_shot_results = None
        pass

    def set_parameters(self, config={}):
        """Set base parameters using config from from Labber driver.

        Parameters
        ----------
        config : dict
            Configuration as defined by Labber driver configuration window

        """
        # sequence parameters
        d = dict(Zero=0, One=1, Two=2, Three=3, Four=4, Five=5, Six=6, Seven=7,
                 Eight=8, Nine=9)
        self.n_qubit = d[config.get('Number of qubits')]
        self.z0 = [config.get('Voltage, QB%d - State 0' % (n + 1)) for n in range(self.n_qubit)]
        self.z1 = [config.get('Voltage, QB%d - State 1' % (n + 1)) for n in range(self.n_qubit)]

        single_shot_voltages = \
            [self.getValue('Single-shot Voltage, QB%d' % (n + 1)) for n in range(self.n_qubit)]

        self.n_record = len(single_shot_voltages[0])

        self.single_shot_results = \
            [self._project_to_state(single_shot_voltages[n], self.z0[n], self.z1[n]) for n in range(self.n_qubit)]

    def _find_point_closest(self, v, a, b):
        """
        Find a point in line y = ax + b closest to the point v = x + 1j* y.
        This performs a projection of the measured voltage onto a line connecting
        that of state 0 and state 1.
        """
        # y = ax + b <==> Ax + By + C = 0 (A = a, B = -1, C = b)
        x, y = v.real, v.imag
        A, B, C = a, -1, b
        xx = (B * (B * x - A * y) - A * C) / (A ** 2 + B ** 2)
        yy = (A * (-B * x + A * y) - B * C) / (A ** 2 + B ** 2)
        return xx + 1j * yy

    def _project_to_line(self, v, v0, v1):
        # projection of complex data to a line v0 + t * v1 (0<t<1)
        I0, Q0 = v0.real, v0.imag
        I1, Q1 = v1.real, v1.imag

        v_rel = v - v0
        # Relative vector between state 0 and state 1
        n = v1 - v0

        # projection and normalization of data to a line connecting |0> and |1>
        p = self._inner_product(v_rel, n) / np.abs(n) ** 2
        return p

    def _inner_product(self, z1, z2):
        """
        Element-wise inner product between complex vectors or between a complex
        vector and a complex number.
        """
        return z1.real * z2.real + z1.imag * z2.imag

    def _project_to_state(self, z, z0, z1):
        """
        Project the point `z = I + jQ` of qubit voltage to state {0, 1}
        """
        # Relative vector between state 0 and state 1
        n = z1 - z0

        # midpoint between two states. this will be refined in future updates
        z_det = (z0 + z1) / 2

        # boolean vector that returns `True` if z is on the side of z1,
        # returns `False` if z is on the side of z0  w.r.t. z_det.
        det = self._inner_product(n, (z - z_det))

        return (det > 0)

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation."""
        return value

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation."""
        value = quant.getValue()

        # check type of quantity
        if quant.name.startswith('Probability'):
            # perform demodulation, check if config is updated
            if self.isConfigUpdated():
                # update sequence object with current driver configuation
                config = self.instrCfg.getValuesDict()
                self.set_parameters(config)

            # get probability index
            idx = quant.name.split(', P(')[1][:-1] - 1

            corr = np.ones(self.n_record, dtype=bool)
            for n in range(self.n_qubit):
                # multiply `True` if the single shot result of qubit is the same
                # as that of corresponding index
                corr *= (bool(int(idx[n])) == self.single_shot_results[n])
            value = np.mean(corr)

        return value
if __name__ == '__main__':
    pass
