#!/usr/bin/env python
# Written by EK 12/8/2019

from VISA_Driver import VISA_Driver
import numpy as np

__version__ = "0.0.1"

class Error(Exception):
    pass

class Driver(VISA_Driver):
    """ This class implements the Tektronix RSA3408B Spectrum Analyzer driver"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # calling the generic VISA open to make sure we have a connection
        VISA_Driver.performOpen(self, options=options)
        # do additional initialization code here...
        pass

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # calling the generic VISA class to close communication
        VISA_Driver.performClose(self, bError, options=options)
        # do additional cleaning up code here...
        pass


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # update visa commands for triggers
        if quant.name in (''):
            pass
        else:
            # run standard VISA case
            value = VISA_Driver.performSetValue(self, quant, value, sweepRate, options)
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
        if quant.name in ('Spectrum'):
            # initialize to single mode
            self.writeAndLog(":INIT:CONT OFF")
            self.writeAndLog(":READ:SPEC?", bCheckError=False)
            sData = self.read(ignore_termination=True)
            # strip header to find # of points
            i0 = sData.find(b'#')
            # number of digits in <num_byte>
            nDig = int(sData[(i0 + 1):(i0 + 2)])
            # number of bytes of data that follows
            nByte = int(sData[(i0 + 2):(i0 + 2 + nDig)])
            # number of data points (4-byte IEEE format)
            nData = int(nByte / 4)

            self.log("(nDig, nByte, nData) = (%d, %d, %d)" % (nDig, nByte, nData))
            # restart continous mode
            self.writeAndLog(":INIT:CONT ON")
            # get data to numpy array
            vData = np.frombuffer(sData[(i0 + 2 + nDig):(i0 + 2 + nDig + nByte)],
                                  dtype='<f', count=nData)
            # get start/stop frequencies from instrument
            startFreq = self.readValueFromOther('Start frequency')
            stopFreq = self.readValueFromOther('Stop frequency')
            value = quant.getTraceDict(vData, x0=startFreq, x1=stopFreq)

        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performGetValue(self, quant, options)
        return value



if __name__ == '__main__':
    pass
