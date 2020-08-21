import numpy as np
import configparser
from pathlib import Path 

# n = self.getValue('Number of flux')
n = 20
#create the config parser for reading the .ini file
file_path = Path('Painter_Z-Crosstalk_Compensation.ini')
config = configparser.ConfigParser()
config.read(file_path)

# #read a value of an item in a section#
# m11 = config.get("M11", 'group')
# print(m11)

#read all sections to a list
sections = config.sections()
print(sections)

general = 'General settings'
if general in sections:
    pass
else:
    config.add_section(general)
    config.set(general, 'name', 'Painter Z-Crosstalk Compensation')
    config.set(general, 'version', '1.0')
    config.set(general, 'driver_path', 'Painter_Z-Crosstalk_Compensation')
    config.set(general, 'signal_generator', 'True')


crosstalkM = 'Crosstalk Matrix'
if crosstalkM in sections:
    pass
else:
    config.add_section(crosstalkM)
    config.set(crosstalkM, 'datatype', 'PATH')
    config.set(crosstalkM, 'tooltip', 'a csv file that contains an NxN crosstalk matrix')
    config.set(crosstalkM, 'group', 'Crosstalk')
    config.set(crosstalkM, 'section', 'Setting')


loadCrosstalkM = 'Load Crosstalk Matrix'
if loadCrosstalkM in sections:
    pass
else:
    config.add_section(loadCrosstalkM)
    config.set(loadCrosstalkM, 'datatype', 'BUTTON')
    config.set(loadCrosstalkM, 'tooltip', 'Load crosstalk matrix from the cvs file to the Input section')
    config.set(loadCrosstalkM, 'group', 'Crosstalk')
    config.set(loadCrosstalkM, 'section', 'Setting')

tuningCurve = 'Tuning Curves'
if tuningCurve in sections:
    pass
else:
    config.add_section(tuningCurve)
    config.set(tuningCurve, 'datatype', 'PATH')
    config.set(tuningCurve, 'tooltip', 'a csv file that contains tuning curves for N qubits, with fmax, fmin, V_0, V_bias, f_bias')
    config.set(tuningCurve, 'group', 'Tuning Curve')
    config.set(tuningCurve, 'section', 'Setting')

loadTuningCurve = 'Load Tuning Curves'
if loadTuningCurve in sections:
    pass
else:
    config.add_section(loadTuningCurve)
    config.set(loadTuningCurve, 'datatype', 'BUTTON')
    config.set(loadTuningCurve, 'tooltip', 'Load tuning curves from the cvs file to the Input section')
    config.set(loadTuningCurve, 'group', 'Tuning Curve')
    config.set(loadTuningCurve, 'section', 'Setting')

Zlines = 'Number of Z-Control Lines'
if Zlines in sections:
    pass
else:
    config.add_section(Zlines)
    config.set(Zlines, 'datatype', 'COMBO')
    config.set(Zlines, 'def_value', str(2))
    for i in range(n - 1):
        config.set(Zlines, 'combo_def_'+str(i+1), str(i+2))
    config.set(Zlines, 'group', 'Setting')
    config.set(Zlines, 'section', 'Setting')



doConversion = 'Do Conversion'
if doConversion in sections:
    pass
else:
    config.add_section(doConversion)
    config.set(doConversion, 'datatype', 'BUTTON')
    config.set(doConversion, 'group', 'Operation')
    config.set(doConversion, 'section', 'Output')
    


#add a section
for i in range(n):
    #populate flux bias
    fmax = 'f max q' + str(i + 1)
    if fmax in sections:
        pass
    else:
        config.add_section(fmax)
        config.set(fmax, 'datatype', 'double')
        config.set(fmax, 'unit', 'GHz')
        config.set(fmax, 'def_value', '0')
        config.set(fmax, 'permission', 'WRITE')
        config.set(fmax, 'tooltip', 'Maximum frequency of qubit '+str(i+1))
        config.set(fmax, 'state_quant', 'Number of Z-Control Lines')
        config.set(fmax, 'group', 'Qubit ' + str(i + 1))
        config.set(fmax, 'section', 'Setting')
        for j in range(n - i):
            config.set(fmax, 'state_value_' + str(j+1), str(i+j+1))


    fmin = 'f min q' + str(i + 1)
    if fmin in sections:
        pass
    else:
        config.add_section(fmin)
        config.set(fmin, 'datatype', 'double')
        config.set(fmin, 'unit', 'GHz')
        config.set(fmin, 'def_value', '0')
        config.set(fmin, 'permission', 'WRITE')
        config.set(fmin, 'tooltip', ' Minimum frequency of qubit ' + str(i+1) + ' (if asymmetric)')
        config.set(fmin, 'state_quant', 'Number of Z-Control Lines')
        config.set(fmin, 'group', 'Qubit ' + str(i + 1))
        config.set(fmin, 'section', 'Setting')
        for j in range(n - i):
            config.set(fmin, 'state_value_' + str(j+1), str(i+j+1))

    V0 = 'V0 q' + str(i + 1)
    if V0 in sections:
        pass
    else:
        config.add_section(V0)
        config.set(V0, 'datatype', 'double')
        config.set(V0, 'unit', 'V')
        config.set(V0, 'def_value', '0')
        config.set(V0, 'permission', 'WRITE')
        config.set(V0, 'state_quant', 'Number of Z-Control Lines')
        config.set(V0, 'group', 'Qubit ' + str(i + 1))
        config.set(V0, 'section', 'Setting')
        
        for j in range(n - i):
            config.set(V0, 'state_value_' + str(j+1), str(i+j+1))

    Vbias = 'V bias q' + str(i + 1)
    if Vbias in sections:
        pass
    else:
        config.add_section(Vbias)
        config.set(Vbias, 'datatype', 'double')
        config.set(Vbias, 'unit', 'V')
        config.set(Vbias, 'def_value', '0')
        config.set(Vbias, 'permission', 'WRITE')
        config.set(Vbias, 'state_quant', 'Number of Z-Control Lines')
        config.set(Vbias, 'group', 'Qubit ' + str(i + 1))
        config.set(Vbias, 'section', 'Setting')
        for j in range(n - i):
            config.set(Vbias, 'state_value_' + str(j+1), str(i+j+1))


    fbias = 'f bias q' + str(i + 1)
    if fbias in sections:
        pass
    else:
        config.add_section(fbias)
        config.set(fbias, 'datatype', 'double')
        config.set(fbias, 'unit', 'GHz')
        config.set(fbias, 'def_value', '0')
        config.set(fbias, 'tooltip', 'frequency of qubit ' + str(i + 1) + ' with only V bias q' + str(i+1) + ' applied and others 0')
        config.set(fbias, 'permission', 'WRITE')
        config.set(fbias, 'state_quant', 'Number of Z-Control Lines')
        config.set(fbias, 'group', 'Qubit ' + str(i + 1))
        config.set(fbias, 'section', 'Setting')
        
        for j in range(n - i):
            config.set(fbias, 'state_value_' + str(j+1), str(i+j+1))


    ftarget = 'f target q' + str(i + 1)
    if ftarget in sections:
        pass
    else:
        config.add_section(ftarget)
        config.set(ftarget, 'datatype', 'double')
        config.set(ftarget, 'unit', 'GHz')
        config.set(ftarget, 'def_value', '0')
        config.set(ftarget, 'tooltip', 'Target frequency of qubit '+ str(i+1))
        config.set(ftarget, 'permission', 'WRITE')
        config.set(ftarget, 'state_quant', 'Number of Z-Control Lines')
        config.set(ftarget, 'group', 'Qubit ' + str(i + 1))
        config.set(ftarget, 'section', 'Setting')
        
        for j in range(n - i):
            config.set(ftarget, 'state_value_' + str(j+1), str(i+j+1))

    slope = 'Slope q' + str(i + 1)
    if slope in sections:
        pass
    else:
        config.add_section(slope)
        config.set(slope, 'datatype', 'COMBO')
        config.set(slope, 'state_quant', 'Number of Z-Control Lines')
        config.set(slope, 'def_value', 'Negative')
        for j in range(n - i):
            config.set(slope, 'state_value_' + str(j+1), str(i+j+1))
        config.set(slope, 'combo_def_1', 'Positive')
        config.set(slope, 'combo_def_2', 'Negative')
        config.set(slope, 'group', 'Qubit ' + str(i + 1))
        config.set(slope, 'section', 'Setting')
    
    Vtarget = 'V target q' + str(i + 1)
    if Vtarget in sections:
        pass
    else:
        config.add_section(Vtarget)
        config.set(Vtarget, 'datatype', 'double')
        config.set(Vtarget, 'unit', 'V')
        config.set(Vtarget, 'tooltip', 'Target Voltage of qubit '+str(i+1))
        config.set(Vtarget, 'def_value', '0')
        config.set(Vtarget, 'permission', 'WRITE')
        config.set(Vtarget, 'state_quant', 'Number of Z-Control Lines')
        config.set(Vtarget, 'group', 'Target Voltage ' + str(i + 1))
        config.set(Vtarget, 'section', 'Setting')
        for j in range(n - i):
            config.set(Vtarget, 'state_value_' + str(j+1), str(i+j+1))

confirm = 'Confirm'
if confirm in sections:
    pass
else:
    config.add_section(confirm)
    config.set(confirm, 'datatype', 'BUTTON')
    config.set(confirm, 'group', 'Confirm')
    config.set(confirm, 'section', 'Setting')

for i in range(n):
    for j in range(n):
        M = 'M' + str(i + 1) + '-' + str(j + 1)
        if M in sections:
            pass
        else:
            config.add_section(M)
            config.set(M, 'datatype', 'double')
            config.set(M, 'unit', 'V')
            if i == j:
                config.set(M, 'def_value', '1')
                config.set(M, 'tooltip', 'Qubit 1 frequency relationship with flux bias '+ str(i+1) +' without any other flux presence')
            else: 
                config.set(M, 'def_value', '0')
                config.set(M, 'tooltip', 'Qubit ' + str(i+1) + ' frequency change in the presence of flux bias ' + str(j+1))

            config.set(M, 'permission', 'BOTH')
            config.set(M, 'state_quant', 'Number of Z-Control Lines')
            config.set(M, 'group', 'Crosstalk Matrix')
            config.set(M, 'section', 'Setting')
            
            if i < j:
                for k in range(n - j):
                    config.set(M, 'state_value_' + str(k+1), str(j+k+1))
            else:
                for k in range(n - i):
                    config.set(M, 'state_value_' + str(k+1), str(i+k+1))


    for j in range(n):
        Minv = 'Minv' + str(i + 1) + '-' + str(j + 1)
        if Minv in sections:
            pass
        else:
            config.add_section(Minv)
            config.set(Minv, 'datatype', 'double')
            config.set(Minv, 'unit', 'V')
            if i == j:
                config.set(Minv, 'def_value', '1')
                config.set(Minv, 'tooltip', 'Qubit 1 frequency relationship with flux bias ' + str(i+1) +' without any other flux presence')
            else: 
                config.set(Minv, 'def_value', '0')
                config.set(Minv, 'tooltip', 'Qubit ' + str(i+1) + ' frequency change in the presence of flux bias ' + str(j+1))

            config.set(Minv, 'permission', 'BOTH')
            config.set(Minv, 'state_quant', 'Number of Z-Control Lines')
            config.set(Minv, 'group', 'Crosstalk Matrix (Inverse)')
            config.set(Minv, 'section', 'Output')
            
            if i < j:
                for k in range(n - j):
                    config.set(Minv, 'state_value_' + str(k+1), str(j+k+1))
            else:
                for k in range(n - i):
                    config.set(Minv, 'state_value_' + str(k+1), str(i+k+1))

    AdjustedV = 'Adjusted Voltage ' + str(i + 1)
    if AdjustedV in sections:
        pass
    else:
        config.add_section(AdjustedV)
        config.set(AdjustedV, 'datatype', 'double')
        config.set(AdjustedV, 'unit', 'V')
        config.set(AdjustedV, 'def_value', '0')
        config.set(AdjustedV, 'permission', 'READ')
        config.set(AdjustedV, 'state_quant', 'Number of Z-Control Lines')
        config.set(AdjustedV, 'group', 'Output')
        config.set(AdjustedV, 'section', 'Output')
        for j in range(n - i):
            config.set(AdjustedV, 'state_value_' + str(j+1), str(i+j+2))
        # write to .ini#
with open(file_path, 'w') as configfile:
    config.write(configfile)