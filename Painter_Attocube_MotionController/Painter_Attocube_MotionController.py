from PyANC350v2.PyANC350v2 import Positioner
import InstrumentDriver
import numpy as np
import time

class Error(Exception):
    pass

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements the Attocube Motion Controller driver"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        self.positioner = Positioner()

    def performClose(self, bError=False, options={}):
        try:
            self.positioner.close()
        except:
            pass

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""

        # dictionary of axis labels and corresponding indices
        ax = {'Axis 1': 0, 'Axis 2': 1, 'Axis 3': 2, 'Axis 4': 3, 'Axis 5': 4,
            'Axis 6': 5}
        pos = self.positioner
        name = str(quant.name)

        # start with setting current quant value
        quant.setValue(value)

        axis, mthd = str.split(name, ' - ')
        n_axis = ax[axis]

        if mthd == 'Output Enable':
            pos.setOutput(n_axis, value)
        elif mthd == 'DC Level':
            pos.dcLevel(n_axis, value)
        elif mthd == 'Amplitude':
            pos.amplitude(n_axis, value)
        elif mthd == 'Frequency':
            pos.frequency(n_axis, value)

        if mthd == 'Single Step':
            # Here, the stage moves by a single step whenever performSetValue method is called.

            pos.moveSingleStep(n_axis, int(quant.getValueIndex(value)))
            self.wait(0.1)

        return value

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        ax = {'Axis 1': 0, 'Axis 2': 1, 'Axis 3': 2, 'Axis 4': 3, 'Axis 5': 4, 'Axis 6': 5}
        pos = self.positioner
        name = str(quant.name)

        axis, mthd = str.split(name, ' - ')
        n_axis = ax[axis]

        if mthd == 'Position':
            return pos.getPosition(n_axis)
        elif mthd == 'Amplitude':
            return pos.getAmplitude(n_axis)
        elif mthd == 'Capacitance':
            return pos.capMeasure(n_axis)
        elif mthd == 'Frequency':
            return pos.getFrequency(n_axis)
        elif mthd == 'DC Level':
            return pos.getDcLevel(n_axis)
        elif mthd == 'Step Width':
            return pos.getStepwidth(n_axis)
        elif mthd == 'Speed':
            return pos.getSpeed(n_axis)
        else:
            return quant.getValue()

    # def getActiveMeasurements(self):
    #     """Retrieve and a list of measurement/parameters currently active"""
    #

if __name__ == '__main__':
    pass
