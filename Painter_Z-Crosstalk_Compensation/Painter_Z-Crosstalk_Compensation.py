#!/usr/bin/env python

import InstrumentDriver
import numpy as np
import configparser
from pathlib import Path
from numpy import genfromtxt

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements Z-Crosstalk Compensation"""
    

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # init variables
    

    def updateMatrix(self):
        """Set matrix elements from the csv file
        """
        # return directly if not in use
        path = self.getValue('Crosstalk Matrix')
        full_matrix = genfromtxt(path, delimiter=',')
        
        n = int(self.getValue('Number of Z-Control Lines'))
        matrix = full_matrix[1:, 1:]
    
        if (matrix.shape[0] != n):
            raise ValueError("Matrix File qubit number does not equal Number of Z-Control Lines")


        for i in range(n):
            for j in range(n): 
                self.setValue('M'+str(i+1)+ '-' +str(j+1),  matrix[i, j])
    
    def updateTuningCurves(self):
        path = self.getValue('Tuning Curves')
        tuning_parameters = genfromtxt(path, delimiter=',')
        
        n = int(self.getValue('Number of Z-Control Lines'))
        fmax = np.zeros(n)
        fmin = np.zeros(n)
        V_0 = np.zeros(n)

        #need to check the input dimension
        if (tuning_parameters.shape[0] != n+1):
            raise ValueError("Tuning Curve File qubit number does not equal Number of Z-Control Lines")

        for i in range(n):
            fmax[i] = tuning_parameters[i+1, 1]
            fmin[i] = tuning_parameters[i+1, 2]
            V_0[i] = tuning_parameters[i+1, 3]

            self.setValue('f max q' + str(i+1), fmax[i])
            self.setValue('f min q' + str(i+1), fmin[i])
            self.setValue('V0 q' + str(i+1), V_0[i])


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # do nothing, just return value
        if (quant.name == 'Load Crosstalk Matrix'):
            self.updateMatrix()
        elif (quant.name == 'Load Tuning Curves'):
            self.updateTuningCurves()
        elif (quant.name == 'Confirm'):
            self.freqToVoltage()
        elif (quant.name == 'Do Conversion'):
            self.doConversion()
        elif ('f target' in quant.name):
            self.freqToVoltage()
            self.doConversion()

        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # check type of quantity
        if quant.isVector():
            pass
        else:
            if (quant.name == 'Confirm'):
                self.freqToVoltage()

            elif 'f target' in quant.name:
                self.freqToVoltage()
                self.doConversion()
            # for all other cases, do nothing
            value = quant.getValue()
        return value


    def freqToVoltage(self):
        """Perform the non linear frequency and voltage conversion, used in the conversion matrix"""
        n = int(self.getValue('Number of Z-Control Lines'))

        f_max = np.zeros(n) # max qubit frequency#
        f_min = np.zeros(n) # min qubit frequency#
        v_0 = np.zeros(n) #period#
        v_bias = np.zeros(n) #applied bias voltage without other biases#
        f_bias = np.zeros(n) # target frequency
        # E_j = np.zeros(n)
        # E_j1 = np.zeros(n)
        # E_j2 = np.zeros(n)

        Em = np.zeros(n)
        d = np.zeros(n)
        Vang = np.zeros(n)
        Voff = np.zeros(n)
        Vang_target = np.zeros(n)


        # E_j_tot = np.zeros(n)
        # phase_offset = np.zeros(n)
        V_target = np.zeros(n)
        f_target = np.zeros(n)

        for i in range(n):
            f_max[i] = self.getValue('f max q' + str(i+1))
            f_min[i] = self.getValue('f min q' + str(i+1))
            v_0[i] = self.getValue('V0 q' + str(i+1))
            v_bias[i] = self.getValue('V bias q' + str(i+1))
            f_bias[i] = self.getValue('f bias q' + str(i+1))
            f_target[i] = self.getValue('f target q' + str(i+1))
            #assume E_j1 >> E_j2
            # E_j1[i] = 0.0625 * (f_max[i]**2 + f_min[i]**2)
            # E_j2[i] = 0.0625 * (f_max[i]**2 - f_min[i]**2)
            #
            # E_j_tot[i] = E_j1[i] + E_j2[i]
            # d[i] = (E_j1[i] - E_j2[i]) / E_j_tot[i]
            #

            Em[i] = f_max[i]**2
            d[i] = (f_min[i] / f_max[i])

            # y = np.arcsin(np.sqrt(np.divide((f_bias[i]**2 / (8 * E_j_tot[i]))**2 - 1, (d[i]**2 - 1))))
            # E_j[i] = E_j_tot[i] * np.cos(np.pi * (v_0[i] - phase_offset[i])) * np.sqrt(1 + d[i]**2 * np.tan(np.pi * (v_0[i] - phase_offset[i])) ** 2)


            if (str(self.getValue('Slope q' + str(i+1))) == 'Negative'):
                Vang[i] = np.arcsin(np.sqrt((f_bias[i]**2 / Em[i] - 1) / (d[i]**2 - 1)))
                Voff[i] = v_bias[i] - v_0[i] * Vang[i] / np.pi
                Vang_target[i] = np.arcsin(np.sqrt((f_target[i]**2 / Em[i] - 1) / (d[i]**2 - 1)))
                V_target[i] = v_0[i] * Vang_target[i] / np.pi + Voff[i]
                # phase_offset[i] = v_bias[i] - (np.arcsin(np.sqrt(np.divide((f_bias[i]**2 / (8 * E_j_tot[i]))**2 - 1, (d[i]**2 - 1)))))/np.pi
                # V_target[i] =  (np.arcsin(np.divide(np.sqrt(abs(f_target[i]**4 - 64 * E_j_tot[i]**2)), (E_j_tot[i] * np.sqrt(abs(64*d[i]**2 - 64))))))/np.pi + phase_offset[i]
                self.setValue('V target q' + str(i+1), V_target[i])
            elif (str(self.getValue('Slope q' + str(i+1))) == 'Positive'):
                Vang[i] = np.arcsin(- np.sqrt((f_bias[i]**2 / Em[i] - 1) / (d[i]**2 - 1)))
                Voff[i] = v_bias[i] - v_0[i] * Vang[i] / np.pi
                Vang_target[i] = np.arcsin(- np.sqrt((f_target[i]**2 / Em[i] - 1) / (d[i]**2 - 1)))
                V_target[i] = v_0[i] * Vang_target[i] / np.pi + Voff[i]
                # phase_offset[i] = v_bias[i] + (np.arcsin(np.sqrt(np.divide((f_bias[i]**2 / (8 * E_j_tot[i]))**2 - 1, (d[i]**2 - 1)))))/np.pi
                # V_target[i] = phase_offset[i] - (np.arcsin(np.divide(np.sqrt(abs(f_target[i]**4 - 64 * E_j_tot[i]**2)), (E_j_tot[i] * np.sqrt(abs(64*d[i]**2 - 64))))))/np.pi
                self.setValue('V target q' + str(i+1), V_target[i])


    def doConversion(self):
        n = int(self.getValue('Number of Z-Control Lines'))
        #self.log("Number of Z-Control Lines: %d "%(n))
        M = np.zeros((n,n))
        M_ideal = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                M[i,j] = self.getValue('M' + str(i+1) + '-' + str(j+1))
                M_ideal[i,i] = self.getValue('M' + str(i+1) + '-' + str(i+1))
        self.log("M: " +str(M))

        M_inv = np.linalg.inv(M)
        M_compensation = np.matmul(M_ideal, M_inv)
        self.log("M_compensation: " + str(M_compensation))

        vecVin = np.zeros((n))
        for i in range(n):
            vecVin[i] = self.getValue('V target q' + str(i+1))

        vecVout = np.matmul(M_compensation, vecVin)
        self.log("vec_Vout: " + str(vecVout))
        for i in range(n):
            self.setValue('Adjusted Voltage '+str(i+1), vecVout[i])

            for j in range(n):
                self.setValue('Minv'+str(i+1)+ '-' +str(j+1), M_compensation[i,j])

if __name__ == '__main__':
    pass
