#!/usr/bin/env python

from VISA_Driver import VISA_Driver
import numpy as np

__version__ = "0.0.1"

class Error(Exception):
    pass

class Driver(VISA_Driver):
    """ This class implements the Agilent E5071C Network Analyzer driver"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # init meas param dict
        self.dMeasParam = {}
        # calling the generic VISA open to make sure we have a connection
        VISA_Driver.performOpen(self, options=options)
        # do perform get value for acquisition mode


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
#TODO: Lorentzian sweep 
#        if self.isFinalCall(options) and self.getValue('Sweep type') == 'Lorentzian':
#                 # get parameters
#                centerFreq = self.getValue('Center frequency')
#                qEst = self.getValue('Q Value')
#                thetaMax = self.getValue('Maximum Angle')
#                numPoints = self.getValue('# of points')
#                # calculate distribution
#                frequencies = self.calcLorentzianDistr(thetaMax, numPoints, qEst, centerFreq)
#                data = []
#                for freq in frequencies:
#                    data.append('1')
#                    data.append('1')
#                    data.append(str(freq))
#                    data.append(str(freq))
#                dataset = ','.join(data)
#                self.writeAndLog('SENS:SEGM:LIST SSTOP, %s, %s' % (numPoints, dataset))

        # update visa commands for triggers
        if quant.name in ('S11 - Enabled', 'S21 - Enabled', 'S12 - Enabled',
                          'S22 - Enabled'):
            if self.getModel() in ('E5071C',):
                # new trace handling, use trace numbers, set all at once
                lParam = ['S11', 'S21', 'S12', 'S22']
                dParamValue = dict()
                for param in lParam:
                    dParamValue[param] = self.getValue('%s - Enabled' % param)
                dParamValue[quant.name[:3]] = value

                # add parameters, if enabled
                self.dMeasParam = dict()
                for (param, enabled) in dParamValue.items():
                    if enabled:
                        nParam = len(self.dMeasParam)+1
                        self.writeAndLog(":CALC:PAR%d:DEF %s" %
                                         (nParam, param))
                        self.dMeasParam[param] = nParam
                # set number of visible traces
                self.writeAndLog(":CALC:PAR:COUN %d" % len(self.dMeasParam))
        elif quant.name in ('Wait for new trace',):
            # do nothing
            pass
        elif quant.name in ('Sweep type'):
            # if linear:
            if self.getValue('Sweep type') == 'Linear':
                self.writeAndLog(':SENS:SWE:TYPE LIN')
            #if log:
            elif self.getValue('Sweep type') == 'Log':
                self.writeAndLog(':SENS:SWE:TYPE LOG')
# TODO
#            # if Lorentzian:
#            elif self.getValue('Sweep type') == 'Lorentzian':
#                # prepare VNA for segment sweep
#                self.writeAndLog(':SENS:SWE:TYPE SEGM') 
#                self.writeAndLog('DISP:WIND:TABL SEGM') 
        else:
            # run standard VISA case
            value = VISA_Driver.performSetValue(self, quant, value, sweepRate, options)
        return value

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
        if quant.name in ('S11 - Enabled', 'S21 - Enabled', 'S12 - Enabled',
                          'S22 - Enabled'):
            # update list of channels in use
            self.getActiveMeasurements()
            # get selected parameter
            param = quant.name[:3]
            value = (param in self.dMeasParam)
        elif quant.name in ('S11', 'S21', 'S12', 'S22'):
            # check if channel is on
            if quant.name not in self.dMeasParam:
                # get active measurements again, in case they changed
                self.getActiveMeasurements()
            if quant.name in self.dMeasParam:
                if self.getModel() in ('E5071C',):
                    # new trace handling, use trace numbers
                    self.writeAndLog("CALC:PAR%d:SEL" % self.dMeasParam[quant.name])

                # if not in continous mode, trig from computer
                bWaitTrace = self.getValue('Wait for new trace')
                bAverage = self.getValue('Average')
                # wait for trace, either in averaging or normal mode
                if bWaitTrace:
                    # Bus Trigger
                    self.writeAndLog(':TRIG:SOUR BUS')

                    if bAverage:
                        # turn on averaging trigger
                        self.writeAndLog(':TRIG:AVER ON')
                        
                        # restart averaging
                        self.writeAndLog(':SENS:AVER:CLE')
                    
                    # wait for sweep time
                    tWait = float(self.askAndLog('SENS:SWE:TIME?'))
                    if bAverage:
                        nAverage = self.getValue("# of averages")
                        tWait *= nAverage
                    self.wait(tWait)
                    self.writeAndLog('*OPC')
  
                    bDone = False
                    stb = 0
                    while (not bDone) and (not self.isStopped()):
                        # check if done
                        stb = int(self.askAndLog('*ESR?'))
                        bDone = (stb & 1) > 0
                        if not bDone:
                            self.wait(0.1)
                    # if stopped, don't get data
                    if self.isStopped():
                        self.writeAndLog('*CLS;:INIT:CONT ON;')
                        return []
                # get data as float32, convert to numpy array
                self.write(':FORM:DATA REAL32;:CALC:SEL:DATA:SDAT?',
                           bCheckError=False)
                sData = self.read(ignore_termination=True)

                if bWaitTrace and not bAverage:
                    self.writeAndLog(':INIT:CONT ON;')

                # strip header to find # of points
                i0 = sData.find(b'#')
                nDig = int(sData[i0+1:i0+2])
                nByte = int(sData[i0+2:i0+2+nDig])
                nData = int(nByte/4)
                nPts = int(nData/2)
                # get data to numpy array
                vData = np.frombuffer(sData[(i0+2+nDig):(i0+2+nDig+nByte)], 
                                      dtype='>f', count=nData)
                # data is in I0,Q0,I1,Q1,I2,Q2,.. format, convert to complex
                mC = vData.reshape((nPts, 2))
                vComplex = mC[:, 0] + 1j * mC[:, 1]
                # get start/stop frequencies
                centerFreq = self.readValueFromOther('Center frequency')
                sweepType = self.readValueFromOther('Sweep type')
                # if log scale, take log of start/stop frequencies
                logX = (sweepType == 'Log')
                span = self.readValueFromOther('Span')
                startFreq = centerFreq - (span/2)
                stopFreq = centerFreq + (span/2)
                value = quant.getTraceDict(vComplex, x0=startFreq, x1=stopFreq,
                                           logX=logX)

#                lorX = (sweepType == 'Lorentzian')
#                if lorX:
#                    qEst = self.getValue('Q Value')
#                    thetaMax = self.getValue('Maximum Angle')
#                    numPoints = self.getValue('# of points')
#                    value = quant.getTraceDict(vComplex,
#                                               x=self.calcLorentzianDistr(thetaMax, numPoints, qEst, centerFreq))
#                else:
#                    span = self.readValueFromOther('Span')
#                    startFreq = centerFreq - (span/2)
#                    stopFreq = centerFreq + (span/2)
#                    value = quant.getTraceDict(vComplex, x0=startFreq, x1=stopFreq,
#                                               logX=logX)
            else:
                # not enabled, return empty array
                value = quant.getTraceDict([])
        elif quant.name in ('Wait for new trace',):
            # do nothing, return local value
            value = quant.getValue()
        else:
            # for all other cases, call VISA driver
            value = VISA_Driver.performGetValue(self, quant, options)
        return value


    def getActiveMeasurements(self):
        """Retrieve and a list of measurement/parameters currently active"""
        # meas param is just a trace number
        self.dMeasParam = {}
        # get number or traces
        nTrace = int(self.askAndLog(":CALC:PAR:COUN?"))
        # get active trace names, one by one
        for n in range(nTrace):
            sParam = self.askAndLog(":CALC:PAR%d:DEF?" % (n + 1))
            self.dMeasParam[sParam] = (n + 1)

    def calcLorentzianDistr(self, thetaMax, numPoints, qEst, centerFreq):
        """
        Helper function to calculate Lorentzian frequency distribution 
        """
        theta = np.linspace(-thetaMax, thetaMax, numPoints)
        freq = np.multiply(centerFreq,
                           (1 - np.multiply(1 / (2 * qEst),
                                            np.tan(np.divide(theta, 2)))))
        return freq


if __name__ == '__main__':
    pass
