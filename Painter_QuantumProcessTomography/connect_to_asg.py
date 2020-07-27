""" THIS FILE IS PROVISIONAL - EVENTUALLY IT SHOULD BE USED TO IMPORT GENERAL
    PULSE SEQUENCES FROM AN ARBITRARY SEQUENCE GENERATOR INTO A QPT EXPERIMENT. """
import sys
import numpy as np

sys.path.append('/Applications/Labber/Script')
import Labber

if __name__ == "__main__":
    client = Labber.connectToServer('localhost')
    instr = client.connectToInstrument('Arbitrary Sequence Generator', {'name': 'arbys'})
    x_pulse_ge = instr.getValue('Waveform XY - I')
    y_pulse_ge = instr.getValue('Waveform XY - Q')
    instr2 = client.connectToInstrument('Quantum Process Tomography', {'name': 'queuepeetea'})
    instr2.setValue('Process X - G-E', x_pulse_ge)
    instr2.setValue('Process Y - G-E', y_pulse_ge)
    x_pulse_ef = instr.getValue('Waveform XY - I')
    y_pulse_ef = instr.getValue('Waveform XY - Q')
    print(len(y_pulse_ef))
    z = np.zeros(len(x_pulse_ef['y']))
    instr2.setValue('Process X - E-F', x_pulse_ef)
    instr2.setValue('Process Y - E-F', y_pulse_ef)
    instr2.setValue('Process Z', z)

    client.close()
