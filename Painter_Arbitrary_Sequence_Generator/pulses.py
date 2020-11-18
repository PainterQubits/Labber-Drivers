#!/usr/bin/env python3
import logging
from enum import Enum

import numpy as np


log = logging.getLogger('LabberDriver')


class PulseType(Enum):
    """Define possible qubit pulse types."""

    XY = 'XY'
    Z = 'Z'
    DELAY = 'Delay'
    READOUT = 'Readout'
    NONE = 'None'

class PulseShape(Enum):
    """Define possible qubit pulses shapes."""

    GAUSSIAN = 'Gaussian'
    SQUARE = 'Square'
    ZBIAS = 'Z-Bias'
    READ_FAST = 'Read_fast'
    CUSTOM = 'Custom'

class Pulse(object):
    """Represents physical pulses played by an AWG.

    Parameters
    ----------
    pulse_type : :obj:`PulseType`
        Pulse type (the default is PulseType.XY).
    shape : :obj:`PulseShape`
        Pulse shape (the default is PulseShape.GAUSSIAN).

    Attributes
    ----------
    length : float
        Pulse length
    amplitude : float
        Pulse amplitude.
    frequency : float
        Carrier frequency of pulse.
    phase : float
        Pulse phase.
    use_drag : bool
        If True, applies DRAG correction.
    drag_coefficient : float
        Drag coefficient.
    drag_detuning : float
        Applies a frequnecy detuning for DRAG pulses.
    gaussian_num_STDs : float
        The truncation range of Gaussian pulses,
        in units of standard deviations.
    square_rise_time : float
        How fast does the pulse edge rise

    """

    def __init__(self,  pulse_type=PulseType.Z, shape=PulseShape.SQUARE):

        # set variables
        self.pulse_type = pulse_type
        self.shape = shape

        self.length = 30e-9
        self.amplitude = 1.0
        self.frequency = 0.0
        self.phase = 0.0
        self.use_drag = False
        self.drag_coefficient = 0.0
        self.drag_detuning = 0.0
        self.gaussian_num_stds = 3.0
        self.square_rise_time = 2e-9


    def calculate_envelope(self, t,): #args will be for flux modulation on the Z-bias
        """Calculate pulse envelope.

        Parameters
        ----------
        t : numpy array
            Array with time values for which to calculate the pulse envelope.

        Returns
        -------
        envelope : numpy array
            Array containing pulse envelope.

        """
        dt = t[1] - t[0]
        len_pulse = len(t)
        envelope = np.zeros(len_pulse) #initialize envelope array

        if self.shape == PulseShape.SQUARE:

            len_edge = np.int(np.ceil(self.square_rise_time/dt)+1) #calculate length of rising edge in samples

            if len_pulse > 2*len_edge: #adding linear rising and falling edges to pulse if length of pulse > 2* length edge
                envelope[:len_edge] = np.linspace(0,1,len_edge)
                envelope[-len_edge:] = np.linspace(1,0,len_edge)
                envelope[len_edge:-len_edge] = 1

            else: #if length of pulse is smaller than 2*length of edge, then make an envelope with only falling and rising edges
                halfway_t = np.int(np.floor(len_pulse/2)) #halfway point of the pulse, in samples
                envelope[:halfway_t] = np.linspace(0,1, halfway_t)
                envelope[halfway_t:] = np.linspace(1,0, len_pulse - halfway_t) #I do len_pulse - halfway_t instead of just halfway_t if the number of samples is odd

        elif self.shape == PulseShape.GAUSSIAN:
            halfway_t = int(np.floor(len_pulse/2)) #calculate midpoint of pulse, in samples
            t0 = t[halfway_t] #midpoint of pulse
            σ = self.length/(2*self.gaussian_num_stds) #calculate σ of gaussian based on pulse length and num of std deviations we want to fit
            envelope = np.exp( -(t-t0)**2/(2*σ**2) )
            envelope = envelope - envelope.min() #make pulse start at 0
            envelope = envelope/envelope.max()

        elif self.shape == PulseShape.READ_FAST: #for readout pulses with a starting high amplitude transient region to ring-up RO resonator faster
            # Below I am hardcoding length of transient here to be 1/4 of pulse length, for it's shape to be Gaussian to minimize spectal leakage, and for it's amplitude to be 2.5 times larger than the steady region
            halfway_t = int(np.floor(len_pulse/8)) #halfway_t is midpoint of transient region, in samples
            t0 = t[halfway_t] #midpoint of transient region
            σ = (self.length/4)/(2*3) #I am harcoding 3 gaussian standard deviations here
            envelope[:halfway_t] = 2.5*np.exp( -(t[:halfway_t]-t0)**2/(2*σ**2) ) #the first half of the transient region is a pure Gaussian
            envelope[halfway_t:2*halfway_t] = 1.5*np.exp( -(t[halfway_t:2*halfway_t]-t0)**2/(2*σ**2) )
            envelope[halfway_t:] = envelope[halfway_t:] + np.ones(len_pulse-halfway_t) #the second region of the transient region is a down-scaled gaussian + the steady part; such that the second half of the transient smoothly converges to the steady part
            envelope = envelope - envelope.min()

        envelope = envelope * self.amplitude

        return envelope

        #if self.shape == PulseShape.ZBIAS: #Z-bias pulse consists of starting from the last Z-bias value and ramping to a new Z-bias value
            #len_edge = np.int(np.ceil(self.square_rise_time/dt)+1) #calculate length of rising edge in samples
            #if len_pulse > len_edge:
            #    envelope[:len_edge] = np.linspace(last_value_Zbias,self.amplitude,len_edge) #make rising edge start from last Z-bias value and end at the new Z-bias level
            #    envelope[len_edge:] = self.amplitude
            #else:
            #    envelope = np.linspace(last_value_Zbias, self.amplitude, len_pulse) #if length of pulse is smaller than rising edge, make the whole Z-bias pulse a rising edge
            #envelope = np.ones(len_pulse) * self.amplitude + args[0] * np.cos(2*pi*args[1] * 1e6* (t-t[0]))
            #return envelope


    def calculate_waveform(self, t, IQ_ratio = 1.0, IQ_skew = 0.0, I_offset = 0.0, Q_offset = 0.0, custom_waveform = None,
                            Z_bias_mod_amp = 0.0, Z_bias_mod_freq = 0.0): #custom waveform input is for Custom pulses
        """Calculate pulse waveform including carrier frequency, phase offsets, IQ mixer compensations, and DRAG implementation

        Parameters
        ----------
        t : numpy array
            Array with time values for which to calculate the pulse waveform.

        Returns
        -------
        waveform : numpy array
            Array containing pulse waveform.

        """
        π = np.pi
        if self.shape == PulseShape.CUSTOM: #make the "envelope" the custom waveform for a "Custom" Pulse
            envelope = custom_waveform
        elif self.shape == PulseShape.ZBIAS:
            envelope = np.ones(len(t)) * self.amplitude + Z_bias_mod_amp * np.cos(2*np.pi*Z_bias_mod_freq * 1e6* (t-t[0]))
        else:
            envelope = self.calculate_envelope(t)
        ω = self.frequency * 2 * π
        dt = t[1]-t[0]

        if self.pulse_type == PulseType.XY: #below I generate I/Q waveforms with the IQ parameters and DRAG
            DRAG_δ = self.drag_detuning * 2 * π
            I_waveform = (envelope * np.cos( (ω + DRAG_δ) * t + self.phase ) +
                          -self.drag_coefficient * np.gradient(envelope)/dt * np.sin( (ω + DRAG_δ) * t + self.phase ) ) + I_offset
            Q_waveform = IQ_ratio*(envelope * np.sin( (ω + DRAG_δ) * t + self.phase + IQ_skew ) -
                          -self.drag_coefficient * np.gradient(envelope)/dt * np.cos( (ω + DRAG_δ) * t + self.phase + IQ_skew ) ) + Q_offset
            waveform = I_waveform + 1j*Q_waveform

        elif self.pulse_type == PulseType.Z:
            t_noPhase = t-t[0] #make sure pulse doesn't have any intrinsic phase regardless of when it starts
            waveform = envelope * np.cos(ω * t_noPhase + self.phase)

        elif self.pulse_type == PulseType.READOUT:
            I_waveform = envelope * np.cos(ω * t + self.phase) + I_offset
            Q_waveform = envelope * IQ_ratio * np.sin(ω * t + self.phase + IQ_skew) + Q_offset
            waveform = I_waveform + 1j*Q_waveform

        elif self.pulse_type == PulseType.NONE or self.pulse_type == PulseType.DELAY:
            waveform = np.zeros(len(t))

        return waveform

if __name__ == '__main__':
    pass
