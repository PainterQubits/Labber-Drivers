import sys
sys.path.append('C:\\Program Files (x86)\\Labber\\Script')

import Labber
import numpy as np
from scipy.interpolate import interp1d
import InstrumentDriver

class Driver(InstrumentDriver.InstrumentWorker):
    """This class implements PulseCorrection."""


    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        self.is_uniform_transfer_func = self.getValue("Uniform Transfer Function")

        ndict = {'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5, 'Six': 6,
                 'Seven': 7, 'Eight': 8, 'Nine': 9}

        self.nTraces = ndict[self.getValue('Number of Traces to Correct')]
        self.is_test_input_trace = bool(self.getValue("Use Test Input Trace"))
        # store list of input traces
        self.input_traces = []
        if not self.is_test_input_trace:
            for n in range(self.nTraces):
                trace_in = self.getValue("Input Trace #" + str(n + 1))
                self.input_traces.append(trace_in)
        else:
            for n in range(self.nTraces):
                self.input_traces.append(self._test_input())
        # store list of transfer functions. driver needs to be restarted when
        # using a new transfer function settings.
        self.transfer_funcs = []
        if self.is_uniform_transfer_func:
            dpath = self.getValue('Transfer Function - Path')
            self.transfer_funcs.append(self._transfer_func(dpath))
        else:
            for n in range(self.nTraces):
                dpath = self.getValue('Transfer Function #' + str(n + 1) + ' - Path')
                self.transfer_funcs.append(self._transfer_func(dpath))

    def _test_input(self):
        # test pulse settings
        n_pulse = int(round(self.getValue("Test Input Trace - Number of Pulses")))
        spacing = self.getValue("Test Input Trace - Pulse Spacing")

        start_delay = self.getValue("Test Input Trace - Start Delay")
        plateau = self.getValue("Test Input Trace - Plateau")
        end_delay = self.getValue("Test Input Trace - End Delay")
        dt = 1e-9

        test = np.zeros(int(np.round(start_delay / dt)))
        for m in range(n_pulse):
            test = np.append(test, 0.5 * np.ones(int(np.round(plateau / dt))))
            if m < n_pulse - 1:
                test = np.append(test, np.zeros(int(np.round(spacing / dt))))
        test = np.append(test, np.zeros(int(np.round(end_delay / dt))))

        test_in = {'y': test, 't0': 0.0, 'dt': 1.0e-9}
        return test_in

    def _append_balancing_pulse(self, trace_in):
        start_delay = self.getValue("Balancing Pulse - Start Delay")
        plateau = self.getValue("Balancing Pulse - Plateau")
        end_delay = self.getValue("Balancing Pulse - End Delay")

        y_in, t0, dt = trace_in['y'], trace_in['t0'], trace_in['dt']

        # number of points corresponding to sections of balancing pulse
        n_start_delay = int(np.round(start_delay / dt))
        n_plateau = int(np.round(plateau / dt))
        n_end_delay = int(np.round(end_delay / dt))

        area = np.sum(y_in) * dt
        # amplitude of the balancing pulse
        amplitude = - area / (n_plateau * dt)

        # append start delay, balancing pulse, and the end delay
        y_in = np.append(y_in, np.zeros(n_start_delay))
        y_in = np.append(y_in, amplitude * np.ones(n_plateau))
        y_in = np.append(y_in, np.zeros(n_end_delay))

        trace_in_balanced = {'y': y_in, 't0': t0, 'dt': dt}
        return trace_in_balanced

    def _transfer_func(self, path):
        """
        Construct transfer function from interpolation of data specified by path
        """
        f = Labber.LogFile(path)
        d = f.getEntry(0)

        vFreq = d['Frequency']
        vH = d['Signal - Real'] + 1j * d['Signal - Imag']
        return interp1d(2 * np.pi * vFreq, vH)

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation."""
        return value

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation."""
        value = quant.getValue()
        self.log(self.isConfigUpdated())

        if quant.name.startswith('Output Trace'):
            # calculate output trace using the inputs and the transfer functions
            n = int(quant.name.split(' #')[1]) - 1

            H = self.transfer_funcs[0]

            if not self.is_uniform_transfer_func:
                # if not using uniform transfer function, overwrite the function
                H = self.transfer_funcs[n]

            if not self.is_test_input_trace:
                trace_in = self.getValue("Input Trace #" + str(n + 1))
                self.log("Trace In #" + str(n + 1) + " = " + str(value['y']))
                # update the input trace stored in the driver
                self.input_traces[n] = trace_in
            else:
                self.input_traces[n] = self._test_input()

            trace_in = self.input_traces[n]
            if self.getValue("Add Balancing Pulse"):
                trace_in = self._append_balancing_pulse(trace_in)

            y_in = trace_in['y']
            dt = trace_in['dt']
            t_in = np.array([trace_in['t0'] + m * dt for m in range(len(trace_in['y']))])

            # perform deconvolution of the trace if the vector has at least 2 entries
            if len(y_in) > 1:
                # FFT of input trace
                Y_in = np.fft.rfft(y_in, norm='ortho')
                # frequency data for the FFT
                ω = 2 * np.pi * np.fft.rfftfreq(len(y_in), d=dt)

                # deconvolution
                Y_out = Y_in / H(ω)
                y_out = np.fft.irfft(Y_out, n=len(y_in), norm='ortho')

                self.log("Trace Out #" + str(n + 1) + " = " + str(y_out))
                value = quant.getTraceDict(y_out, t0=t_in[0], dt=dt)
        return value

if __name__ == '__main__':
    pass
