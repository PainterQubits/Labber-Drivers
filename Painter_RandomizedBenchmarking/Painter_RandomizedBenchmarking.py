import InstrumentDriver
import numpy as np

import randomized_benchmarking as rb
import dsp_utils as dsp_utils

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements a single qubit randomized benchmarking driver"""
    # If any of these values are updated, we will need to update our readout trace.
    # Additionally we'll check for any updates to any 'Readout' values.
    READOUT_STALING_CHECKLIST = [
        'Sampling Rate',
        'Sequence Length',
        'Random Seed',
        'Do interleaved RB?',
        'Interleaved Gate',
        'Do Heralding?',
        'Delay After Heralding Pulse',
        'Pi Pulse Length',
        'Pi-Half Pulse Length',
        'Percent of Sequence',
    ]

    # If any of these values are updated, we will need to update the Clifford
    # generators
    CLIFFORD_GENERATOR_STALING_CHECKLIST = [
        'Sampling Rate',
        'Modulation Frequency',
        'Pi Pulse Length',
        'Pi Pulse Sigmas',
        'Pi Pulse Amplitude',
        'Pi Pulse Derivative Amplitude',
        'Pi Pulse DRAG Z Bias',
        'Pi-Half Pulse Length',
        'Pi-Half Pulse Sigmas',
        'Pi-Half Pulse Amplitude',
        'Pi-Half Pulse Derivative Amplitude',
        'Pi-Half Pulse DRAG Z Bias',
        'Constant Detuning Bias',
    ]

    # If any of these values are updated, we will need to update control traces.
    CLIFFORD_SEQUENCE_STALING_CHECKLIST = [
        'Sequence Length',
        'Random Seed',
        'Do interleaved RB?',
        'Interleaved Gate',
        'Percent of Sequence',
    ]

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        self.clifford_sequence_is_stale = False
        self.clifford_generators_are_stale = False
        self.readout_is_stale = False

        # Initialize empty waveforms
        self.clifford_generators = {
            'identity': np.zeros(0),
            'pi': np.zeros(0),
            'pi_derivative': np.zeros(0),
            'pi_detuning': np.zeros(0),
            'pi_half': np.zeros(0),
            'pi_half_derivative': np.zeros(0),
            'pi_half_detuning': np.zeros(0)
        }
        self.clifford_sequence = []
        # X signal pieces
        self.heralding_x = np.zeros(0)
        self.x = np.zeros(0)
        self.readout_x = np.zeros(0)
        # Y signal pieces
        self.heralding_y = np.zeros(0)
        self.y = np.zeros(0)
        self.readout_y = np.zeros(0)
        # Z signal pieces
        self.heralding_z = np.zeros(0)
        self.z = np.zeros(0)
        self.readout_z = np.zeros(0)
        # Readout I signal pieces
        self.heralding_i = np.zeros(0)
        self.readout_i = np.zeros(0)
        # Readout Q signal pieces
        self.heralding_q = np.zeros(0)
        self.readout_q = np.zeros(0)
        # Readout Trigger signal pieces
        self.readout_trigger_heralding = np.zeros(0)
        self.readout_trigger = np.zeros(0)
        self.dt = 1


    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        pass


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        if quant.name in Driver.READOUT_STALING_CHECKLIST or 'Readout' in quant.name:
            self.readout_is_stale = True
        if quant.name in Driver.CLIFFORD_GENERATOR_STALING_CHECKLIST:
            self.clifford_generators_are_stale = True
        if quant.name in Driver.CLIFFORD_SEQUENCE_STALING_CHECKLIST:
            self.clifford_sequence_is_stale = True

        # Perform some input handling
        if quant.name == 'Percent of Sequence':
            if not 0 <= value <= 100:
                value = 100
        if quant.name == 'Sequence Length':
            if value < -4:
                value = 0
        if 'Sigmas' in quant.name:
            if value <= 0:
                value = 1
            value = np.ceil(value)
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # proceed depending on quantity
        if 'Waveform' in quant.name:

            # If either the generators or the sequence are stale, we will have
            # to update our x, y, z signals
            if self.clifford_generators_are_stale or self.clifford_sequence_is_stale:
                # If the clifford generators are stale they must be updated
                if self.clifford_generators_are_stale:
                    self.update_clifford_generators()
                    self.clifford_generators_are_stale = False

                # If the sequence is stale, we must update it
                if self.clifford_sequence_is_stale:
                    self.update_clifford_sequence()
                    self.clifford_sequence_is_stale = False
                self.update_xyz_sequences()

            # If the readout is stale we must update it
            if self.readout_is_stale:
                self.update_readout()
                self.readout_is_stale = False

            # Plot and return the appropriate trace dict:
            if quant.name == 'Waveform - X Signal':
                signal = np.concatenate((self.heralding_x, self.x))
                signal = np.concatenate((signal, self.readout_x))
                trace = quant.getTraceDict(signal, t0=0.0, dt=self.dt)
            elif quant.name == 'Waveform - Y Signal':
                signal = np.concatenate((self.heralding_y, self.y))
                signal = np.concatenate((signal, self.readout_y))
                trace = quant.getTraceDict(signal, t0=0.0, dt=self.dt)
            elif quant.name == 'Waveform - Z Signal':
                signal = np.concatenate((self.heralding_z, self.z))
                signal = np.concatenate((signal, self.readout_z))
                trace = quant.getTraceDict(signal, t0=0.0, dt=self.dt)
            elif quant.name == 'Waveform - Readout I':
                signal = np.concatenate((self.heralding_i, self.readout_i))
                trace = quant.getTraceDict(signal, t0=0.0, dt=self.dt)
            elif quant.name == 'Waveform - Readout Q':
                signal = np.concatenate((self.heralding_q, self.readout_q))
                trace = quant.getTraceDict(signal, t0=0.0, dt=self.dt)
            elif quant.name == 'Waveform - Readout Trigger':
                signal = np.concatenate((self.readout_trigger_heralding, self.readout_trigger))
                trace = quant.getTraceDict(signal, t0=0.0, dt=self.dt)
            return trace

        elif 'QB' in quant.name:
            demodulated_signal = self.demodulate()
            return demodulated_signal

        else: 
            # for other quantities, just return current value of control
            return quant.getValue()


    def update_clifford_generators(self):
        sampling_rate = self.getValue('Sampling Rate')

        pi_pulse_length = self.getValue('Pi Pulse Length')
        pi_pulse_sigmas = self.getValue('Pi Pulse Sigmas')
        pi_pulse_amplitude = self.getValue('Pi Pulse Amplitude')
        pi_pulse_derivative_amplitude = \
            self.getValue('Pi Pulse Derivative Amplitude')
        pi_pulse_detuning = self.getValue('Pi Pulse DRAG Z Bias')

        pi_half_pulse_length = self.getValue('Pi-Half Pulse Length')
        pi_half_pulse_sigmas = self.getValue('Pi-Half Pulse Sigmas')
        pi_half_pulse_amplitude = self.getValue('Pi-Half Pulse Amplitude')
        pi_half_pulse_derivative_amplitude = \
            self.getValue('Pi-Half Pulse Derivative Amplitude')
        pi_half_pulse_detuning = self.getValue('Pi-Half Pulse DRAG Z Bias')

        shared_detuning = self.getValue('Shared Z Bias')

        # Generate the generator signals and create a pulse sequence
        pi_params = {
            'length': pi_pulse_length,
            'standard_deviation': pi_pulse_length / pi_pulse_sigmas,
            'amplitude': pi_pulse_amplitude,
            'derivative_amplitude': pi_pulse_derivative_amplitude,
            'detuning': pi_pulse_detuning + shared_detuning,
        }
        pi_half_params = {
            'length': pi_half_pulse_length,
            'standard_deviation': pi_half_pulse_length / pi_half_pulse_sigmas,
            'amplitude': pi_half_pulse_amplitude,
            'derivative_amplitude': pi_half_pulse_derivative_amplitude,
            'detuning': pi_half_pulse_detuning + shared_detuning,
        }
        
        self.clifford_generators = rb.build_generator_signals(sampling_rate,
                                       pi_params,
                                       pi_half_params,
                                       const_detuning=True)
    

    def update_clifford_sequence(self):
        # Collect necessary quantities
        seed = int(self.getValue('Random Seed'))
        num_cliffords = int(self.getValue('Sequence Length'))
        do_interleave = self.getValue('Do interleaved RB?')

        # Use special seeds -1 and -2 for pi and pi-half pulses for calibration
        if not num_cliffords < 0:
            # Update sequence
            np.random.seed(seed + 10015 * num_cliffords)
            if not do_interleave:
                self.clifford_sequence = rb.generate_random_clifford_sequence(
                                             num_cliffords)
            else:
                interleaved_gate = int(self.getValue('Interleaved Gate'))
                self.clifford_sequence = rb.generate_random_clifford_sequence(
                                             num_cliffords,
                                             interleaved_gate=interleaved_gate)
        else:
            if num_cliffords == -1:
                self.clifford_sequence = ['xp']
            elif num_cliffords == -2:
                self.clifford_sequence = ['x2p']
            elif num_cliffords == -3:
                self.clifford_sequence = ['yp']
            elif num_cliffords == -4:
                self.clifford_sequence = ['y2p']


    def update_xyz_sequences(self):
        # Collect necessary quantities
        sampling_rate = self.getValue('Sampling Rate')
        modulation_frequency = 1e-3*self.getValue('Modulation Frequency')
        percent_of_sequence = self.getValue('Percent of Sequence') / 100

        # Update sequences
        x, y, z, times = rb.build_full_pulse_sequence(self.clifford_sequence,
                             self.clifford_generators,
                             sampling_rate)
        self.dt = 1 / sampling_rate
        x_signal = dsp_utils.modulate_signal(x, self.dt, modulation_frequency, 0) \
                   + dsp_utils.modulate_signal(y, self.dt, modulation_frequency, np.pi/2)
        y_signal = dsp_utils.modulate_signal(y, self.dt, modulation_frequency, 0) \
                   + dsp_utils.modulate_signal(x, self.dt, modulation_frequency, -np.pi/2)

        samples_to_keep = int(percent_of_sequence * len(x_signal))

        self.x = x_signal[:samples_to_keep]
        self.y = y_signal[:samples_to_keep]
        self.z = z[:samples_to_keep]


    def update_readout(self):
        # Collect necessary quantities
        sampling_rate = self.getValue('Sampling Rate')
        readout_amplitude = self.getValue('Readout Amplitude')
        readout_frequency = 2*np.pi*1e-3*self.getValue('Readout Frequency') # rad/ns
        readout_phase = np.pi/180*self.getValue('Readout Phase') # rad
        readout_length = self.getValue('Readout Length')

        iq_ratio = self.getValue('Readout I/Q Ratio')
        iq_phase_skew = np.pi/180*self.getValue('Readout I/Q Phase Skew') # rad
        i_dc = self.getValue('Readout I DC Offset')
        q_dc = self.getValue('Readout Q DC Offset')

        do_generate_trigger = self.getValue('Generate Readout Trig?')

        readout_z_bias = self.getValue('Readout Z-Bias')

        do_heralding = self.getValue('Do Heralding?')

        do_fast_readout = self.getValue('Do Wicked Fast Readout?')

        # Update readout
        presignal = np.zeros(len(self.x))
        readout_times = np.linspace(0, readout_length, sampling_rate*readout_length)
        rising_time = 2
        rising_edge_samples = int(sampling_rate*rising_time)

        envelope = np.ones(len(readout_times))
        rising_edge = np.linspace(0, 1, rising_edge_samples)
        envelope[:rising_edge_samples] = rising_edge
        if do_fast_readout:
            # build a gaussian envelope that we can add on top of our normal
            # envelope
            gaussian_length = readout_length / 4
            gaussian_center = gaussian_length / 2
            sigma = gaussian_length/3
            gaussian_envelope = 1 + 2.5*np.exp(-(readout_times - gaussian_center)**2/(2*sigma**2))
            envelope = envelope * gaussian_envelope
        
        readout_i = i_dc + iq_ratio*readout_amplitude * envelope * \
                               np.cos(readout_frequency*readout_times + \
                                      readout_phase + \
                                      iq_phase_skew)
        readout_q = q_dc + readout_amplitude * envelope * \
                               np.sin(readout_frequency*readout_times + \
                                      readout_phase)

        # If the readout need be generated, generate it
        if not do_generate_trigger:
            self.readout_trigger = np.zeros(0)
            self.readout_trigger_heralding = np.zeros(0)
        else:
            trigger_length = self.getValue('Readout Trig Duration')
            trigger_amplitude = self.getValue('Readout Trig Amplitude')
            # Require at lest one point so we don't get needless index out of
            # range errors for rising and falling edge constraints.
            trigger_times = np.linspace(0, trigger_length, sampling_rate*trigger_length + 1)
            trigger = trigger_amplitude*np.ones(len(trigger_times))
            # Enforce rising edge
            trigger[0] = 0
            # Enforce falling edge
            trigger[-1] = 0
            self.readout_trigger = np.concatenate((presignal, trigger))

        # Update Z line (might be nonzero to accommodate readout bias)
        z = readout_z_bias*np.ones(len(readout_times))
        self.readout_z = z

        self.readout_i = np.concatenate((presignal, readout_i))
        self.readout_q = np.concatenate((presignal, readout_q))

        # TODO: THIS MIGHT BE HORRIBLY BROKEN NOW
        if do_heralding:
            heralding_delay = self.getValue('Delay After Heralding Pulse')
            heralding_downtime = np.linspace(0, heralding_delay, sampling_rate*heralding_delay)
            heralding_gap_signal = np.zeros(len(heralding_downtime))
            self.heralding_i = np.concatenate((readout_i, heralding_gap_signal))
            self.heralding_q = np.concatenate((readout_q, heralding_gap_signal))
            self.heralding_z = np.concatenate((z, heralding_gap_signal))
            x_and_y_zeros = np.zeros(len(readout_i))
            self.heralding_x = np.concatenate((x_and_y_zeros, heralding_gap_signal))
            self.heralding_y = np.concatenate((x_and_y_zeros, heralding_gap_signal))
            if do_generate_trigger:
                herald_trigger_holder = np.zeros(len(self.heralding_i))
                herald_trigger = np.concatenate((trigger, heralding_gap_signal))
                if len(herald_trigger) <= len(herald_trigger_holder):
                    herald_trigger_holder[:len(herald_trigger)] = herald_trigger
                else:
                    herald_trigger_holder = trigger_amplitude*np.ones(len(herald_trigger_holder))
                    herald_trigger_holder[0] = 0
                    herald_trigger_holder[1] = 1
                self.readout_trigger_heralding = herald_trigger_holder
        else:
            self.heralding_i = np.zeros(0)
            self.heralding_q = np.zeros(0)
            self.heralding_z = np.zeros(0)
            self.heralding_x = np.zeros(0)
            self.heralding_y = np.zeros(0)
            self.readout_trigger_heralding = np.zeros(0)


    def demodulate(self):
        """Demodulates a given signal assuming that it has been downconverted
        from fridge output RF to the same frequency as the IF Readout Frequency
        field of this Driver."""
        # I'm not really sure how we can be sure about the units of dt, which 
        # inform the units of this frequency. For example when I was running
        # simple tests demodulating the readout waveforms of another QPT driver
        # directly the units were in ns, but in VF's driver demodulation units
        # are in seconds...
        demodulation_frequency = self.getValue('Readout Frequency')*1e6
        signal_i = self.getValue('Demodulation - Input I')
        signal_q = self.getValue('Demodulation - Input Q')
        readout_samples = int(self.getValue('Demodulation - Number of Samples'))
        dt = signal_i['dt']
        if dt == 0:
            dt = 1.0
        skip_start = int(self.getValue('Demodulation - Skip') / (dt))
       
        signal_i = signal_i['y'][skip_start: skip_start + readout_samples]
        signal_q = signal_q['y'][skip_start: skip_start + readout_samples]

        # In VF's demodulation code, he reshapes readout signals into chunks of
        # 'readout_samples' length, corresponding to the expected length of the
        # signal to demodulate - this seems to contradict the purpose of having
        # such a field to restrict the amount of signal that gets fed into 
        # demodulation?
        complex_signal = signal_i + 1j*signal_q

        t = np.linspace(0, len(complex_signal)*dt, len(complex_signal))
        reference_signal = np.exp(-2j*np.pi*t*demodulation_frequency)

        # Perform the discrete integral of the signal against reference
        # normalized by signal length.
        prod = complex_signal * reference_signal
        norm_sum = np.sum(prod) / len(prod)
        return norm_sum
