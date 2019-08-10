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

            # initialize variables
            dt_in = 0
            dt_out = 0

            if self.getValue("Uniform Input Sample Rate"):
                dt_in = 1 / self.getValue("Sample Rate - Input")
            else:
                dt_in = 1 / self.getValue("Sample Rate - Input #" + str(n + 1))

            if self.getValue("Uniform Output Sample Rate"):
                dt_out = 1 / self.getValue("Sample Rate - Output")
            else:
                dt_out = 1 / self.getValue("Sample Rate - Output #" + str(n + 1))

            trace_in = self.getValue("Input Trace #" + str(n + 1))
            self.log("Trace In #" + str(n + 1) + " = " + str(trace_in['y']))

            # perform interpolation of the data if the vector has at least 2 entries
            if len(trace_in['y']) > 1:
                t_in = np.array([trace_in['t0'] + m * dt_in for m in range(len(trace_in['y'])))
                interp_func = interpolate.interp1d(t_in, trace_in['y'])

                t_out = np.arange(t_in[0], t_in[-1], dt_out)
                trace_out = interp_func(t_out)
                self.log("Trace Out #" + str(n + 1) + " = " + str(trace_out))
                value = quant.getTraceDict(trace_out, t0=t_in[0], dt=dt_out)

        return value

if __name__ == '__main__':
    pass
