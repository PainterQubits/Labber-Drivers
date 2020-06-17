# cloned from https://github.com/Labber-software/Drivers, modified by Eunjong Kim

from VISA_Driver import VISA_Driver
import numpy as np

__version__ = "1.0.0"

class Error(Exception):
    pass

class Driver(VISA_Driver):
    """ This class implements the Rohde&Schwarz FSV Signal and Spectrum Analyzer driver"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # init meas param dict
        self.dMeasParam = {}
        # calling the generic VISA open to make sure we have a connection
        VISA_Driver.performOpen(self, options=options)

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        if quant.name in ('Wait for new trace',):
            # do nothing
            pass
        elif quant.name in ('Marker 1 - Function',):
            m_idx = int(quant.name[8])
            if self.getValue(quant.name) == 'Band Power':
                self.writeAndLog('CALC:MARK%d:FUNC:BPOW:STAT ON' % m_idx)
            elif self.getValue(quant.name) == 'Noise Density':
                self.writeAndLog('CALC:MARK%d:FUNC:NOIS ON' % m_idx)
            else:
                pass
        elif quant.name in ('RBW', 'VBW', 'Detector'):
            # perform manual set value operation on certain quantities only if automatic setting is unchecked in the driver
            if not self.getValue(quant.name + ' - Auto'):
                # run standard VISA case
                value = VISA_Driver.performSetValue(self, quant, value, sweepRate, options)
            else:
                pass
        else:
            # run standard VISA case
            value = VISA_Driver.performSetValue(self, quant, value, sweepRate, options)
        return value

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
        if quant.isFirstCall(options) and quant.name == 'Power':
            # Trig from computer
            bWaitTrace = self.getValue('Acquire new trace')
            bAverage = self.getValue('Average')
            # wait for trace, either in averaging or normal mode
            if bWaitTrace:
                # abort the current measurement and switch to single sweep mode
                self.writeAndLog('ABOR;INIT:CONT OFF')
                if bAverage:
                    # switch on trace averaging mode in the display
                    self.writeAndLog('DISP:TRAC:MODE AVER')
#                 if bAverage:
#                     nAverage = self.getValue('# of averages')
# #                        self.writeAndLog(':SENS:AVER:CLE;:ABOR;:INIT;*WAI')
#                     self.writeAndLog('AVER:COUN %d;:INIT:IMM;*OPC' % nAverage)
#                 else:
#                     self.writeAndLog(':ABOR;:INIT:CONT OFF;:SENS:AVER:COUN 1;:INIT:IMM;*OPC')

                # Start the measurement;
                # initialize the event status register bit to zero (changes to 1 once the job has finished)
                self.writeAndLog(":INIT;*OPC")
                # wait some time before first check
                self.wait(0.03)
                bDone = False
                while (not bDone) and (not self.isStopped()):
                    # check the event status register
                    stb = int(self.askAndLog('*ESR?'))
                    bDone = (stb & 1) > 0
                    if not bDone:
                        # check every 100ms whether the job has finished
                        self.wait(0.1)
                # if stopped, don't get data and leave the instrument in a continuously triggered mode
                if self.isStopped():
                    self.writeAndLog('*CLS;INIT:CONT ON;')
                    return []
            # get data as float32, convert to numpy array
            sData = self.ask(':FORM REAL,32;TRAC1? TRACE1')
            if bWaitTrace and not bAverage:
                self.writeAndLog(':INIT:CONT ON;')
            # strip header to find # of points
            i0 = sData.find(b'#')
            nDig = int(sData[(i0 + 1):(i0 + 2)])
            nByte = int(sData[(i0 + 2):(i0 + 2 + nDig)])
            nData = int(nByte / 4)
            # get data to numpy array
            vData = np.frombuffer(sData[(i0 + 2 + nDig):(i0 + 2 + nDig + nByte)],
                                  dtype='<f', count=nData)

            startFreq = self.readValueFromOther('Start frequency')
            stopFreq = self.readValueFromOther('Stop frequency')

            # create a trace dict
            value = quant.getTraceDict(vData, x0=startFreq, x1=stopFreq)
        elif quant.name in ('Acquire new trace',):
            # do nothing, return local value
            value = quant.getValue()
        elif quant.name in ('Marker 1 - Band Power', 'Marker 1 - Band Power Density'):
            m_idx = int(quant.name[8])
            value = float(self.askAndLog('CALC:MARK%d:FUNC:BPOW:RES?' % m_idx).strip('dBm/Hz'))
        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performGetValue(self, quant, options)
            if quant.isFinalCall(options):
                # put the instrument in continuously triggered mode if data acquisition has finished
                self.writeAndLog(':INIT:CONT ON;')
        return value

if __name__ == '__main__':
    pass
