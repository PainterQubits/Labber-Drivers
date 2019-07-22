import numpy as np
import InstrumentDriver

class Driver(InstrumentDriver.InstrumentWorker):
    """This class implements a waveform adder."""

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation."""
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation."""
        value = quant.getValue()

        if quant.name.startswith('Output Trace'):
            trace_in1 = self.getValue("Input Trace #" + str(1))
            trace_in2 = self.getValue("Input Trace #" + str(2))

            sum=trace_in1['y']+trace_in2['y']
            value = quant.getTraceDict(sum, t0=trace_in1['t0'], dt=trace_in1['dt'])

        return value

if __name__ == '__main__':
    pass
