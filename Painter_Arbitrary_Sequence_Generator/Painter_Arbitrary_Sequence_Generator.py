import InstrumentDriver
import importlib
import os
import sys
import copy

import numpy as np

#labber mumbo-jumbo
from BaseDriver import LabberDriver
import logging
log = logging.getLogger('LabberDriver')

from pulses import *

class Driver(InstrumentDriver.InstrumentWorker): #labber mumbo-jumbo
    """ This class implements an arbitrary pulse sequence signal generator driver"""

    def performOpen(self, options={}): #options argument is labber mumbo-jumbo
        """Perform the operation of opening the instrument connection"""
        #initialize waveform objects
        self.XY_waveform = []
        self.Z_waveform = []
        self.Readout_waveform = []
        self.Readout_trig = []
        self.multiplexed_demod_signals = [np.zeros(40),np.zeros(40)] #initialize this to be something to avoid Labber error
        self.sample_rate = self.getValue('Sample Rate')
        self.new_data = False
        for n in range(0,int(self.getValue('Number of Pulses'))): #initialize Custom Waveforms for Custom Pulses to be SOMETHING such that the driver doesn't throw an error in the beginning
            self.setValue('#%d Custom Waveform' % (n+1), np.zeros(40))

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        pass

    def set_parameters(self, options={}):
        self.num_pulses = int(self.getValue('Number of Pulses'))
        self.sample_rate = self.getValue('Sample Rate')
        #self.pulse_lengths = np.array([self.getValue('#%d Length' % (n+1)) for n in range(0,self.num_pulses)])
        self.pulse_lengths = []
        self.pulse_lengths_samples = []

        #I use units of ns below because that will lead to less rounding innacuracy due to floating point
        for n in range(0,self.num_pulses):
            if self.getValue('Pulse %d Type' % (n+1)) == 'Custom': #get length of custom waveforms from the array itself
                waveform_len = len(self.getValue('#%d Custom Waveform' % (n+1))['y'])
                self.pulse_lengths.append(waveform_len/(self.sample_rate/1e9) ) # in units of ns
                self.pulse_lengths_samples.append(waveform_len)
            else:
                pulse_len = self.getValue('#%d Length' % (n+1))
                self.pulse_lengths.append(pulse_len) #in units of ns
                self.pulse_lengths_samples.append(np.int_(np.ceil(pulse_len * self.sample_rate/1e9)))
        self.pulse_lengths = np.array(self.pulse_lengths); self.pulse_lengths_samples = np.array(self.pulse_lengths_samples)

        #self.pulse_lengths_samples = np.int_(np.ceil(self.pulse_lengths * self.sample_rate/1e9)) #calculate pulse lengths in terms of samples
        self.pulse_sample_boundaries = np.array([np.sum(self.pulse_lengths_samples[:i]) for i in range(0, self.num_pulses+1)])#calculate pulse time boundaries in terms of samples
        len_t_vec = self.pulse_sample_boundaries[-1] #length of complete sequence time vector
        self.t = np.linspace(0,(len_t_vec-1)/self.sample_rate, len_t_vec) #time vector of sequence
        self.sequence_delay = np.int(np.ceil(self.getValue('Sequence Delay')*1e-9*self.sample_rate)) #initial delay of sequence in samples
        self.do_readout = self.getValue('Do Readout?')


        #XY IQ parameters
        self.xy_iq_ratio = self.getValue('XY I/Q Ratio')
        self.xy_iq_skew = (self.getValue('XY I/Q Phase Skew')/360)*2*np.pi
        self.xy_I_offset = self.getValue('XY I DC Offset')
        self.xy_Q_offset = self.getValue('XY Q DC Offset')

    def generate_qubit_waveforms(self, options={}):
        self.set_parameters(options) #grabs configuration parameters to generate waveforms
        len_t_vec = len(self.t)
        self.XY_waveform = np.zeros(len_t_vec, dtype = complex);
        self.Z_waveform = np.zeros(len_t_vec);

        for n in range(0, self.num_pulses):
            if self.getValue('Pulse %d Type' % (n+1)) == 'Custom': #if pulse type is "Custom", set which line it will go to with "What control line?" channel and PulseType class
                type = PulseType(self.getValue('#%d What control line?' % (n+1)))
                pulse = Pulse(pulse_type = type, shape = PulseShape('Custom'))
            else:
                type = PulseType(self.getValue('Pulse %d Type' % (n+1)) )
                pulse = Pulse(pulse_type = type, shape = PulseShape(self.getValue('#%d Shape' % (n+1))) )

            pulse.length = self.pulse_lengths[n]*1e-9 #convert to s
            if pulse.length < (1/self.sample_rate):
                continue

            pulse.amplitude = self.getValue('#%d Amplitude' % (n+1))
            pulse.frequency = self.getValue('#%d Frequency' % (n+1))*1e6 #convert to Hz
            pulse.phase = (self.getValue('#%d Phase' % (n+1))/360)*2*np.pi #convert to radians
            pulse.use_drag = self.getValue('#%d DRAG' % (n+1))
            pulse.drag_coefficient = self.getValue('#%d DRAG alpha' % (n+1))
            pulse.drag_detuning = self.getValue('#%d DRAG delta' % (n+1))*1e6 #cinverrt to Hz
            pulse.gaussian_num_stds = self.getValue('#%d Num Gaussian Sigma' % (n+1))
            pulse.square_rise_time = self.getValue('#%d Square Rise Time' % (n+1))*1e-9 #convert to s

            #calculate pulse waveform below with slice of time that corresponds to a particular pulse
            pulse_waveform = pulse.calculate_waveform(self.t[self.pulse_sample_boundaries[n]:self.pulse_sample_boundaries[n+1]],
                             IQ_ratio = self.xy_iq_ratio, IQ_skew = self.xy_iq_skew, I_offset = self.xy_I_offset,
                             Q_offset = self.xy_Q_offset, custom_waveform = self.getValue('#%d Custom Waveform' % (n+1))['y'])

            if pulse.pulse_type ==  PulseType.XY:
                self.XY_waveform[self.pulse_sample_boundaries[n]:self.pulse_sample_boundaries[n+1]] = pulse_waveform
            elif pulse.pulse_type ==  PulseType.Z:
                self.Z_waveform[self.pulse_sample_boundaries[n]:self.pulse_sample_boundaries[n+1]] = pulse_waveform


        self.Z_waveform = self.Z_waveform + self.add_biases_to_Z(options) #add Z-biases to Z-waveform according to Labber pulses configuration
        # add sequence delay to waveforms
        self.XY_waveform = np.concatenate( (np.zeros(self.sequence_delay), self.XY_waveform) )
        self.Z_waveform = np.concatenate( (np.zeros(self.sequence_delay), self.Z_waveform) )

        #adding truncation to waveform
        truncation_length = self.getValue('Truncation Length') #units of ns
        if truncation_length > 0:
            truncation_length_samples = np.int_(np.ceil(truncation_length * self.sample_rate/1e9))
            self.XY_waveform = self.XY_waveform[:-truncation_length_samples]
            self.Z_waveform = self.Z_waveform[:-truncation_length_samples]


        #making readout always start at a multiple of 10ns after AWG is triggered by burst generator
        if self.getValue('Make Waveform Multiple of 10ns?'):
            num_samples_10_ns = np.int(np.round(self.sample_rate * 10e-9))
            extra_samples_10_ns = np.remainder(len(self.XY_waveform), num_samples_10_ns)
            if extra_samples_10_ns != 0:
                self.XY_waveform = np.concatenate( (np.zeros(num_samples_10_ns - extra_samples_10_ns), self.XY_waveform) )
                self.Z_waveform = np.concatenate( (np.zeros(num_samples_10_ns - extra_samples_10_ns), self.Z_waveform) )

        #adding extra delay to Z waveform to account for propagation discrepancy
        self.Z_waveform = np.concatenate((np.zeros(np.int_(np.ceil(self.getValue('Z Waveform Delay') * self.sample_rate/1e9))), self.Z_waveform))

    def add_biases_to_Z(self, options={}):
        Z_biases = np.array([self.getValue('#%d Z-Bias' % (n+1)) for n in range(0,self.num_pulses)])
        Z_bias_waveform = np.zeros(len(self.t))
        #last_value_Zbias = 0.0 #initialize previous Z-bias value

        for n in range(0, self.num_pulses):
            if self.pulse_lengths[n]*1e-9 < (1/self.sample_rate):
                continue
            #initialize a Z-bias pulse that comes with any pulse
            t_pulse = self.t[self.pulse_sample_boundaries[n]:self.pulse_sample_boundaries[n+1]]
            Z_bias_pulse = Pulse(shape = PulseShape.ZBIAS); Z_bias_pulse.amplitude = Z_biases[n];
            #Z_bias_pulse.square_rise_time = 3/self.sample_rate # I AM HARDCODING THE EDGES OF THE Z-BIASES HERE!!!
            if self.getValue('#%d Flux Mod?' % (n+1)) == True:
                mod_amp = self.getValue('#%d Flux Mod Amplitude' % (n+1))
                mod_freq = self.getValue('#%d Flux Mod Frequency' % (n+1))
            else:
                mod_amp = 0; mod_freq = 0

            Z_bias_waveform[self.pulse_sample_boundaries[n]:self.pulse_sample_boundaries[n+1]] = \
            Z_bias_pulse.calculate_waveform(t_pulse, Z_bias_mod_amp = mod_amp, Z_bias_mod_freq = mod_freq)
            #last_value_Zbias = Z_biases[n]

        return Z_bias_waveform

    def generate_readout_waveforms(self, options={}):
        num_q = int(self.getValue('Number of Qubits'))
        readout_wavs = [] #below I get a readout_wav for each readout frequency, and sum them up
        self.set_parameters(options)


        for q in range(0,num_q):
            pulse = Pulse(pulse_type = PulseType.READOUT,
                     shape = PulseShape(self.getValue('Readout Shape')) ) #initialize readout pulse
            pulse.length = self.getValue('Readout Length') * 1e-9
            pulse.amplitude = self.getValue('Readout Amplitude')
            pulse.frequency = self.getValue('Readout Frequency #%d' % (q+1))*1e6
            pulse.phase = (self.getValue('Readout Phase #%d' % (q+1))/360)*2*np.pi
            pulse.square_rise_time = 0 #don't need to worry about pulse edges for readout
            iq_ratio = self.getValue('Readout I/Q Ratio')
            iq_skew = (self.getValue('Readout I/Q Phase Skew')/360)*2*np.pi
            I_offset = self.getValue('Readout I DC Offset')
            Q_offset = self.getValue('Readout Q DC Offset')


            t = np.linspace(0, pulse.length, np.int(np.ceil(pulse.length * self.sample_rate))+1)
            pulse_waveform = pulse.calculate_waveform(t, IQ_ratio = iq_ratio, IQ_skew = iq_skew,
                                                I_offset = I_offset, Q_offset = Q_offset)
            readout_wavs.append(pulse_waveform)

        multiplexed_readout_wav = sum(readout_wavs)
        trig_length = np.int(np.ceil(self.getValue('Readout Trig Duration') * 1e-9 * self.sample_rate))
        trig_waveform = self.getValue('Readout Trig Amplitude') * np.ones(trig_length); trig_waveform[-1]

        if self.getValue('Do Heralding?'): #concatenate waveforms with delays to get heralding pulse in there
            heralding_delay = int(np.ceil(self.getValue('Delay After Heralding Pulse') * self.sample_rate/1e9)) #in number of samples
            if self.getValue('Make Waveform Multiple of 10ns?'): #to ensure second readout always start at a multiple of 10ns after AWG is triggered by burst generator
                num_samples_10_ns = np.int(np.round(self.sample_rate * 10e-9))
                extra_samples_10_ns = np.remainder(len(multiplexed_readout_wav) + heralding_delay, num_samples_10_ns);
                heralding_delay = heralding_delay + (num_samples_10_ns - extra_samples_10_ns)

            self.Readout_waveform = np.concatenate( (multiplexed_readout_wav, np.zeros(heralding_delay), np.zeros(len(self.t)+self.sequence_delay), multiplexed_readout_wav) )
            self.XY_waveform = np.concatenate( (np.zeros(len(t) + heralding_delay), self.XY_waveform) )
            self.Z_waveform = np.concatenate( (self.getValue('Readout Z-Bias')*np.ones(len(t)), np.zeros(heralding_delay), self.Z_waveform, self.getValue('Readout Z-Bias')*np.ones(len(t)) ) )
            if self.getValue('Generate Readout Trig?'): #generate readout trig waveform
                self.Readout_trig = np.concatenate( (trig_waveform[:-1], [0], np.zeros(heralding_delay + len(t) - trig_length), np.zeros(len(self.t)+self.sequence_delay), trig_waveform[:-1], [0]) )
        else:
            self.Readout_waveform = np.concatenate( (np.zeros(len(self.XY_waveform)), multiplexed_readout_wav) ) #concatenate delay preceding readout waveform (i.e. the sequence length)
            self.Z_waveform = np.concatenate( (self.Z_waveform, self.getValue('Readout Z-Bias')*np.ones(len(t))) )
            if self.getValue('Generate Readout Trig?'): #generate readout trig waveform
                self.Readout_trig = np.concatenate( (np.zeros(len(self.XY_waveform)), trig_waveform[:-1], [0]) )

    def demodulate(self, options={}):
        if self.new_data == False:
            return
        num_q = int(self.getValue('Number of Qubits'))
        signal_i = self.getValue('Demodulation - Input I'); signal_q = self.getValue('Demodulation - Input Q')
        dt = signal_i['dt'] #If sampling rate of digitizer is different than sampling rate of AWG, getting this "dt" is important for doing demodulation
        # avoid exceptions if no time step is given
        if dt == 0:
            dt = 1.0
        complex_signal = signal_i['y'] + 1j * signal_q['y'] # + (np.random.normal(0, .2, len(signal_i['y'])) + 1j*np.random.normal(0, .2, len(signal_i['y']))) #put data in complex form
        readout_length_samples = int(self.getValue('Demodulation - Number of Samples'))

        t = np.linspace(0, (readout_length_samples-1) * dt, readout_length_samples)
        num_records = int( len(complex_signal)/readout_length_samples ) #get number of readout pulses contained in one digitizer data dump
        complex_signal_single_shots = complex_signal.reshape( (num_records, readout_length_samples) ) #reshape array to separate different measurements
        skip_start = np.int(np.ceil(self.getValue('Demodulation - Skip') / (dt*1e9)))

        for q in range(0,num_q): #do demodulation for each qubit frequency
            frequency = self.getValue('Readout Frequency #%d' % (q+1))*1e6
            demod_vector = np.exp(-2j * np.pi * t * frequency)
            demod_signal = np.sum( complex_signal_single_shots[:, skip_start:] * demod_vector[skip_start:], axis = 1 )/( readout_length_samples - skip_start ) #integration as described in Daniel Sanks thesis; normalized by readout length

            #ref = self.getValue('Demodulation - Input Ref')['y'].reshape( (num_records, readout_length_samples) )
            #demod_ref = np.sum(ref[:, skip_start:] * demod_vector[skip_start:], axis=1); dAngle_ref = np.angle(demod_ref)
            #demod_signal = np.sum( complex_signal_single_shots[:, skip_start:] * demod_vector[skip_start:], axis = 1 )/(np.exp(1j*dAngle_ref) * ( readout_length_samples - skip_start ))

            #demod_vector = self.getValue('Demodulation - Input Ref')['y'].reshape( (num_records, readout_length_samples) )
            #demod_signal = np.sum( complex_signal_single_shots[:, skip_start:] * demod_vector[:, skip_start:], axis = 1 )/( readout_length_samples - skip_start )

            self.multiplexed_demod_signals[q] = demod_signal

        self.new_data = False
        return

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        if quant.name.startswith('Demodulation - Input'):
            self.new_data = True
        # just return the value
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # proceed depending on quantity
        dt = 1/self.sample_rate

        if quant.name.startswith('Waveform'):


            self.generate_qubit_waveforms(options)

            if self.do_readout:
                self.generate_readout_waveforms(options)

            if quant.name == 'Waveform XY - I':
                value = quant.getTraceDict(self.XY_waveform.real, dt=dt) #quant.getTraceDict is Labber mumbo-jumbo used for plotting these waveforms
            elif quant.name == 'Waveform XY - Q':
                value = quant.getTraceDict(self.XY_waveform.imag, dt=dt)
            elif quant.name == 'Waveform Z':
                value = quant.getTraceDict(self.Z_waveform, dt=dt)
            elif quant.name == 'Waveform Readout - I':
                value = quant.getTraceDict(self.Readout_waveform.real, dt=dt)
            elif quant.name == 'Waveform Readout - Q':
                value = quant.getTraceDict(self.Readout_waveform.imag, dt=dt)
            elif quant.name == 'Waveform Readout Trig':
                value = quant.getTraceDict(self.Readout_trig, dt=dt)

        elif quant.name.startswith('QB'):
            self.demodulate()
            n = int(quant.name[2]) - 1 #parsing word QBi
            if quant.name.endswith('Avg'):
                value = np.mean(self.multiplexed_demod_signals[n])
            else:
                value = quant.getTraceDict(self.multiplexed_demod_signals[n], dt=0.001*dt)

        else:
            # for other quantities, just return current value of control
            value = quant.getValue()

        return value

if __name__ == '__main__':
    pass
