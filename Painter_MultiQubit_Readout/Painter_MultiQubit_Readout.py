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
        self.z_dec = None
        self.n = None
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
        self.z_dec = [config.get('Voltage, QB%d - Decision Point' % (n + 1)) for n in range(self.n_qubit)]
        self.n = [config.get('Voltage, QB%d - Direction' % (n + 1)) for n in range(self.n_qubit)]

        single_shot_voltages = \
            [self.getValue('Single-shot Voltage, QB%d' % (n + 1))['y'] for n in range(self.n_qubit)]

        self.n_record = len(single_shot_voltages[0])

        self.single_shot_results = \
            [self._project_to_state(single_shot_voltages[n], self.z_dec[n], self.n[n]) for n in range(self.n_qubit)]

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

    def _inner_product(self, z1, z2):
        """
        Element-wise inner product between complex vectors or between a complex
        vector and a complex number.
        """
        return z1.real * z2.real + z1.imag * z2.imag

    def _project_to_state(self, z, z_dec, n):
        """
        Project the point `z = I + jQ` of qubit voltage to state {0, 1}
        `z_dec` : a point in the decison boundary between ground state and excited state
        `n` : complex vector normal to the decision boundary and is pointing
            towards the excited state.
        """

        # boolean vector that returns `True` if z is on the side of z1,
        # returns `False` if z is on the side of z0  w.r.t. z_dec.
        det = self._inner_product(n, (z - z_dec))

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
            P_idx = quant.name.split(', P(')[1][:(-1)]

            corr = np.ones(self.n_record, dtype=bool)
            for n in range(self.n_qubit):
                # multiply `True` if the single shot result of qubit is the same
                # as that of corresponding index
                corr *= (bool(int(P_idx[n])) == self.single_shot_results[n])
            value = np.mean(corr)

        return value
if __name__ == '__main__':
    pass
