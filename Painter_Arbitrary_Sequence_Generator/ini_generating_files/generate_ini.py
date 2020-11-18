f_gen = open("general_ini.txt", 'r')
f_seq = open("sequence_ini.txt", 'r')
f_rest = open("RO_wavs_ini.txt", 'r')

general_lines = f_gen.readlines(); f_gen.close()
sequence_lines = f_seq.readlines(); f_seq.close()
RO_wav_lines = f_rest.readlines(); f_rest.close()

ini_file = open("generated.ini","w")
ini_file.writelines(general_lines)

num_pulses = 9
num_qubits = 2
num_pulses_lines = ['[Number of Pulses]\n', 'datatype: COMBO\n']
for i in range(1, num_pulses+1):
    num_pulses_lines.append('combo_def_%d: %d\n' %(i,i))
num_pulses_lines.extend(['def_value: 2\n', 'group: Sequence\n', 'section: Sequence\n', '\n'])

ini_file.writelines(num_pulses_lines)
ini_file.writelines(sequence_lines)

pulses_ini = []

for i in range(1, num_pulses+1):
    pulses_ini.extend(['\n', '###############PULSE %d' %i])
    pulses_ini.extend( ['[Pulse %d Type]' % i, 'datatype: COMBO',
                        'combo_def_1: XY', 'combo_def_2: Z', 'combo_def_3: Custom', 'combo_def_4: Delay',
                        'combo_def_5: None', 'def_value: None', 'state_quant: Number of Pulses'] )
    for j in range(1, num_pulses + 2 -i): #
        pulses_ini.append('state_value_%d: '%j +str(i+(j-1)))
    pulses_ini.extend(['group: Pulse %d' %i, 'section:Pulses', 'show_in_measurement_dlg: False'])

    pulses_ini.extend( ['\n', '[#%d Shape]' % i, 'label:Shape', 'datatype: COMBO',
                        'combo_def_1: Square', 'combo_def_2: Gaussian', 'def_value: Square',
                        'state_quant: Pulse %d Type' %i, 'state_value_1: XY', 'state_value_2: Z', 'group: Pulse %d' %i,
                        'section:Pulses',
                       'show_in_measurement_dlg: False'] )
    pulses_ini.extend( ['\n', '[#%d Num Gaussian Sigma]' %i, 'label: # of Std Deviations', 'datatype: DOUBLE',
                         'def_value: 3', 'state_quant: #%d Shape' %i, 'state_value_1: Gaussian',
                         'group: Pulse %d' %i, 'section: Pulses',
                         'tooltip: gaussian pulse is made to fit # of std deviations specified in pulse length'])
    pulses_ini.extend( ['\n', '[#%d Square Rise Time]' %i, 'label: Edge Rise Time', 'datatype: DOUBLE',
                        'unit: ns', 'def_value: 2', 'state_quant: #%d Shape' %i, 'state_value_1: Square',
                        'group: Pulse %d' %i, 'section: Pulses',
                        'tooltip: length of LINEAR rising edge incorporated into sequenced waveform'])
    pulses_ini.extend( ['\n', '[#%d What control line?]' %i, 'label: What control line?', 'datatype: COMBO',
                        'combo_def_1: XY', 'combo_def_2: Z', 'def_value: Z', 'state_quant: Pulse %d Type' %i,
                        'state_value_1: Custom', 'group: Pulse %d' %i, 'section: Pulses', 'show_in_measurement_dlg: False'])
    pulses_ini.extend( ['\n', '[#%d Length]' %i, 'label: Length', 'datatype: DOUBLE', 'unit: ns',
                        'def_value: 30', 'state_quant: Pulse %d Type' %i, 'state_value_1: XY',
                        'state_value_2: Z', 'state_value_3: Delay', 'group: Pulse %d' %i, 'section: Pulses'])
    pulses_ini.extend( ['\n', '[#%d Amplitude]' %i, 'label: Amplitude', 'datatype: DOUBLE', 'unit: V',
                        'def_value: 1', 'state_quant: Pulse %d Type' %i, 'state_value_1: XY',
                        'state_value_2: Z', 'group: Pulse %d' %i, 'section: Pulses'])
    pulses_ini.extend( ['\n', '[#%d Frequency]' %i, 'label: Frequency', 'datatype: DOUBLE', 'unit: MHz',
                    'def_value: 0', 'state_quant: Pulse %d Type' %i, 'state_value_1: XY',
                    'state_value_2: Z', 'state_value_3: Custom', 'group: Pulse %d' %i, 'section: Pulses'])
    pulses_ini.extend( ['\n', '[#%d Z-Bias]' %i, 'label: Z-Bias', 'datatype: DOUBLE', 'unit: V',
                    'def_value: 0', 'state_quant: Pulse %d Type' %i, 'state_value_1: XY',
                    'state_value_2: Z', 'state_value_3: Custom', 'state_value_4: Delay',
                    'group: Pulse %d' %i, 'section: Pulses'])
    pulses_ini.extend( ['\n', '[#%d Phase]' %i, 'label: Phase', 'datatype: DOUBLE', 'unit: degrees',
                        'def_value: 0', 'state_quant: Pulse %d Type' %i, 'state_value_1: XY',
                        'state_value_2: Z', 'group: Pulse %d' %i, 'section: Pulses'])
    pulses_ini.extend( ['\n', '[#%d DRAG]' %i, 'label: Use DRAG', 'datatype: BOOLEAN', 'def_value: 0',
                        'state_quant: Pulse %d Type' %i, 'state_value_1: XY', 'group: Pulse %d' %i, 'section: Pulses'])
    pulses_ini.extend( ['\n', '[#%d DRAG alpha]' %i, 'label: Derivative Strength', 'datatype: DOUBLE', 'def_value: 0',
                        'state_quant: #%d DRAG' %i, 'state_value_1: 1', 'group: Pulse %d' %i, 'section: Pulses'])
    pulses_ini.extend( ['\n', '[#%d DRAG delta]' %i, 'label: Constant Detuning', 'datatype: DOUBLE', 'unit: MHz',
                        'def_value: 0', 'state_quant: #%d DRAG' %i, 'state_value_1: 1', 'group: Pulse %d' %i,
                        'section: Pulses'])
    pulses_ini.extend( ['\n', '[#%d Custom Waveform]' %i, 'datatype: VECTOR', 'permission: WRITE',
                        'state_quant: Pulse %d Type' %i, 'state_value_1: Custom', 'group: Pulse %d' %i, 'section: Pulses'])
    pulses_ini.extend( ['\n', '[#%d Flux Mod?]' %i, 'label: Flux Mod on Top?', 'datatype: BOOLEAN', 'def_value: 0',
                    'state_quant: Pulse %d Type' %i, 'state_value_1: XY',
                    'state_value_2: Z', 'state_value_3: Custom', 'state_value_4: Delay',
                    'group: Pulse %d' %i, 'section: Pulses'])
    pulses_ini.extend( ['\n', '[#%d Flux Mod Amplitude]' %i, 'label: Mod Amplitude', 'datatype: DOUBLE', 'unit: V', 'def_value: 0',
                    'state_quant: #%d Flux Mod?' %i, 'state_value_1: 1', 'group: Pulse %d' %i, 'section: Pulses'])
    pulses_ini.extend( ['\n', '[#%d Flux Mod Frequency]' %i, 'label: Mod Frequency', 'datatype: DOUBLE', 'unit: MHz', 'def_value: 0',
                    'state_quant: #%d Flux Mod?' %i, 'state_value_1: 1', 'group: Pulse %d' %i, 'section: Pulses'])


pulses_ini = [line+'\n' for line in pulses_ini]
ini_file.writelines(pulses_ini)


num_qubits_lines = ['\n','################################# READOUT SECTION\n', '[Number of Qubits]\n', 'datatype: COMBO\n']
for i in range(1, num_qubits+1):
    num_qubits_lines.append('combo_def_%d: %d\n' %(i,i))
num_qubits_lines.extend(['def_value: 1\n', 'state_quant: Do Readout?\n', 'state_value_1: 1\n',
                        'group: Readout\n', 'section: Readout\n', '\n'])
ini_file.writelines(num_qubits_lines)
ini_file.writelines(RO_wav_lines[:28])

readout_ini = []
for i in range(1, num_qubits+1):
    readout_ini.extend( ['\n', '[Readout Frequency #%d]' % i, 'datatype: DOUBLE','unit: MHz',
                        'def_value: 100', 'state_quant: Number of Qubits'] )
    for j in range(1, num_qubits + 2 -i): #
        readout_ini.append('state_value_%d: '%j +str(i+(j-1)))
    readout_ini.extend(['group: Readout', 'section: Readout'])
    
for i in range(1, num_qubits+1):
    readout_ini.extend( ['\n', '[Readout Phase #%d]' % i, 'datatype: DOUBLE','unit: degrees',
                        'def_value: 0', 'state_quant: Number of Qubits'] )
    for j in range(1, num_qubits + 2 -i): #
        readout_ini.append('state_value_%d: '%j +str(i+(j-1)))
    readout_ini.extend(['group: Readout', 'section: Readout'])

readout_ini = [line+'\n' for line in readout_ini]
ini_file.writelines(readout_ini)
ini_file.writelines(RO_wav_lines[29:])

volt_output = []
for i in range(1, num_qubits+1):

    volt_output.extend( ['\n', '[QB%d Voltage]' % i, 'unit: V', 'datatype: VECTOR_COMPLEX',
                        'permission: READ', 'state_quant: Number of Qubits'] )
    for j in range(1, num_qubits + 2 -i): #
        volt_output.append('state_value_%d: '%j +str(i+(j-1)))
    volt_output.extend(['group: Demodulation', 'section : Demodulation'])

    volt_output.extend( ['\n', '[QB%d Voltage Avg]' % i, 'unit: V', 'datatype: COMPLEX',
                        'permission: READ', 'state_quant: Number of Qubits'] )
    for j in range(1, num_qubits + 2 -i): #
        volt_output.append('state_value_%d: '%j +str(i+(j-1)))
    volt_output.extend(['group: Demodulation', 'section: Demodulation'])

volt_output = [line+'\n' for line in volt_output]
ini_file.writelines(volt_output)

ini_file.close()
