import numpy as np
import sys
sys.path.append("C:/Program Files/Labber/Script")

seq_labber_name = 'testASG'
import Labber
client = Labber.connectToServer('localhost')
seq_gen = client.connectToInstrument('Arbitrary Sequence Generator', dict(name=seq_labber_name))
custom_waveform = np.exp(-np.linspace(0,3,15) )
seq_gen.setValue('#1 Custom Waveform', custom_waveform)
client.close()
