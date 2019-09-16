import numpy as np
from scipy import interpolate
import InstrumentDriver

class Driver(InstrumentDriver.InstrumentWorker):
    """This class implements downsampler."""

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation."""
        return value

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation."""
        value = quant.getValue()

        if quant.name.startswith('Output Trace'):
            n = int(quant.name.split(' #')[1]) - 1

            if self.getValue("Uniform Input Sample Rate"):
                dt = 1 / self.getValue("Sample Rate")

            trace_in = self.getValue("Input Trace #" + str(n + 1))
            self.log("Trace In #" + str(n + 1) + " = " + str(trace_in['y']))

            t_first_delay = self.getValue("First Pulse Delay")
            t_trunc = t_first_delay + self.getValue("Truncation Time")

            n_trunc = int(np.round(t_trunc / dt))

            trace_out = np.copy(trace_in)
            # zero the waveform from (n_trunc + 1)-th point
            trace_out[n_trunc:] = np.zeros(len(trace_in) - n_trunc)
            # perform interpolation of the data if the vector has at least 2 entries

            t_in = np.array([trace_in['t0'] + m * dt for m in range(len(trace_in['y'])))
            value = quant.getTraceDict(trace_out, t0=t_in[0], dt=dt)

        return value

if __name__ == '__main__':
    pass
