#A Driver controller for a Quantum Process Tomography Signal Generator

import InstrumentDriver
import numpy as np

import dsp_utils as dsp_utils
import quantum_process_tomography as qpt


class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements a quantum process tomography driver"""
    # If any of these values are updated, we will need to update our readout trace.
    # Additionally we'll check for any updates to any 'Readout' values.
    READOUT_STALING_CHECKLIST = [
        'Sampling Rate',
        'Pi Pulse Length',
        'Pi-Half Pulse Length',
        'Initial State Index',
        'Measurement Basis Index',
        'Process Pulse Sequence',
        'Do Heralding?',
        'Delay After Heralding Pulse',
        'Process Pulse Length',
    ]

    # If any of these values are updated, we will need to update the basis
    # rotation generators
    BASIS_ROTATION_GENERATORS_STALING_CHECKLIST = [
        'Sampling Rate',
        'G-E Frequency',
        'E-F Frequency',
        'Pi Pulse Length',
        'Pi Pulse Sigmas',
        'Pi Pulse Amplitude',
        'Pi Pulse Derivative Amplitude',
        'Pi-Half Pulse Length',
        'Pi-Half Pulse Sigmas',
        'Pi-Half Pulse Amplitude',
        'Pi-Half Pulse Derivative Amplitude',
        'Basis Rotation Generator Z Bias',
    ]

    # If any of these values are updated, we will need to update the process
    # pulse sequence
    PROCESS_SEQUENCE_STALING_CHECKLIST = [
        'Sampling Rate',
        'Process Pulse Length',
        'Process Pulse Sigma',
        'Process Pulse Amplitude',
        'Process Pulse Derivative Amplitude',
        'Process Pulse Z Bias',
        'Custom Process?',
    ]

    # If any of these values are updated, we will need to update the state
    # preparation sequence
    STATE_PREPARATION_SEQUENCE_STALING_CHECKLIST = [
        'G-E Frequency',
        'E-F Frequency',
        'Initial State Index',
    ]

    # If any of these values are updated, we will need to update the
    # measurement basis sequence.
    MEASUREMENT_BASIS_SEQUENCE_STALING_CHECKLIST = [
        'G-E Frequency',
        'E-F Frequency',
        'Measurement Basis Index',
    ]

    class ControlPulse:
        """ A simple wrapper class for the different 'chunks' of pulses in QPT.

        This QPT implementation breaks up a single QPT 'experiment' into 5
        separate pulse sequences that together concatenate into one experimental
        pulse sequence, in the following way.

        heralding -> state prep -> process -> measurement rotation -> readout

        The heralding sequence includes an initial readout pulse sequence the
        results of which can be used to post-process the results of the process
        and measurement.

        The state initialization sequence initializes the qutrit into one of 9
        potential input states for QPT

        The process sequence is the actual pulse sequence that defines the
        process that is being tomographed (? tomographized ? tomographied ???)

        The measurement preparation sequence are the pulses that rotate the
        relavant components of the qutrit state along the a priori defined
        measurement axis. There are 8 different measurement bases needed to 
        perform complete process tomography (the same as for state tomography
        of a qutrit)

        Finally, the readout sequence is the pulse sequence that actually
        performs the dispersive readout of the qutrit state.

        These different sequences are handled differently in logic to allow for
        maximum 'pulse modularity' so to speak, allowing a user to easily change
        the particulars of one chunk of the QPT experiment with as little code
        complexity as possible.
        """
        def __init__(self):
            self.heralding = np.zeros(0)
            self.state_initialization = np.zeros(0)
            self.process = np.zeros(0)
            self.measurement_preparation = np.zeros(0)
            self.readout = np.zeros(0)

        def build_sequence(self):
            """ Stitches together all the separate pulse parts."""
            sequence = np.concatenate((self.heralding,
                                       self.state_initialization,
                                       self.process,
                                       self.measurement_preparation,
                                       self.readout))
            return sequence

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # These variables govern when particular waveforms need to be
        # refreshed due to changes in dependent parameters.
        self.basis_rotation_generators_are_stale = False
        self.state_prep_sequence_is_stale = False
        self.process_sequence_is_stale = False
        self.measurement_basis_sequence_is_stale = False
        self.readout_is_stale = False

        # Initialize empty generator shape waveforms
        #
        # All the Clifford gates that state preparation and measurement
        # sequences comprise can be generated from pi or pi-half pulses
        # applied to x or y qutrit controls, and hence the only envelopes we
        # need are for pi and pi-half pulses, as well as a trivial identity
        # envelope.
        #
        # Both G-E and E-F pulses use the same general envelope shapes, just
        # upconverted to different frequencies.
        self.generator_envelopes = {
            'pi_identity': np.zeros(0),
            'pi_half_identity': np.zeros(0),
            'pi': np.zeros(0),
            'pi_derivative': np.zeros(0),
            'pi_detuning': np.zeros(0),
            'pi_half': np.zeros(0),
            'pi_half_derivative': np.zeros(0),
            'pi_half_detuning': np.zeros(0)
        }

        # These lists will hold human readable labels of the gates that compose
        # the state preparation and measurement rotation sequences
        self.state_prep_sequence = []
        self.measurement_basis_sequence = []

        # X Pulses
        self.x_ge = self.ControlPulse()
        self.x_ef = self.ControlPulse()
        # Y Pulses
        self.y_ge = self.ControlPulse()
        self.y_ef = self.ControlPulse()
        # Z Pulses
        self.z = self.ControlPulse()
        # Readout Pulses
        self.readout_i = self.ControlPulse()
        self.readout_q = self.ControlPulse()
        self.readout_trigger = self.ControlPulse()

        # Assume 2.4 GHz sampling rate
        self.dt = 1 / 2.4


    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        pass


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # We must check to see if any of our waveforms depend on the parameter
        # being updated, and if we do, set the appropriate staling checklist so
        # that if we request that waveform through a getValue() call, we will
        # first update it. 
        if quant.name in Driver.READOUT_STALING_CHECKLIST or 'Readout' in quant.name:
            self.readout_is_stale = True
        if quant.name in Driver.BASIS_ROTATION_GENERATORS_STALING_CHECKLIST:
            self.basis_rotation_generators_are_stale = True
        if quant.name in Driver.STATE_PREPARATION_SEQUENCE_STALING_CHECKLIST:
            self.state_prep_sequence_is_stale = True
        if quant.name in Driver.MEASUREMENT_BASIS_SEQUENCE_STALING_CHECKLIST:
            self.measurement_basis_sequence_is_stale = True
        if quant.name in Driver.PROCESS_SEQUENCE_STALING_CHECKLIST:
            self.process_sequence_is_stale = True
        # Force standard deviations of pulses to be integers
        if 'Sigmas' in quant.name:
            if value <= 1:
                value = 1
            else:
                value = np.floor(value)
        # just return the value
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # proceed depending on quantity
        if 'Waveform' in quant.name:
            # Always update dt
            sampling_rate = self.getValue('Sampling Rate')
            self.dt = 1 / sampling_rate

            # Make all of our waveform checks and update what we need to
            if self.basis_rotation_generators_are_stale:
                self.update_basis_rotation_generators()
                self.update_state_preparation_sequence()
                self.update_measurement_basis_sequence()
                self.basis_rotation_generators_are_stale = False
                self.state_prep_sequence_is_stale = False
                self.measurement_basis_sequence_is_stale = False

            if self.state_prep_sequence_is_stale:
                self.update_state_preparation_sequence()
                self.state_prep_sequence_is_stale = False
           
            if self.process_sequence_is_stale:
                self.update_process_sequence()
                self.process_sequence_is_stale = False

            if self.measurement_basis_sequence_is_stale:
                self.update_measurement_basis_sequence()
                self.measurement_basis_sequence_is_stale = False

            if self.readout_is_stale:
                self.update_readout()
                self.readout_is_stale = False

            if self.getValue('Process X - G-E') is not None:
                self.update_process_sequence()

            # Plot and return the appropriate trace dict:
            if quant.name == 'Waveform - X Signal':
                ge_frequency = 1e-3*self.getValue('G-E Frequency')
                ef_frequency = 1e-3*self.getValue('E-F Frequency')
                x_ge_signal = dsp_utils.modulate_signal(self.x_ge.build_sequence(),
                                                 self.dt,
                                                 ge_frequency,
                                                 np.pi/2) \
                              + dsp_utils.modulate_signal(self.y_ge.build_sequence(),
                                                 self.dt,
                                                 ge_frequency,
                                                 -np.pi/2) # sine phase
                x_ef_signal = dsp_utils.modulate_signal(self.x_ef.build_sequence(),
                                                 self.dt,
                                                 ef_frequency,
                                                 np.pi/2) \
                              + dsp_utils.modulate_signal(self.y_ef.build_sequence(),
                                                 self.dt,
                                                 ef_frequency,
                                                 -np.pi/2) 
                signal = x_ge_signal + x_ef_signal
                trace = quant.getTraceDict(signal, t0=0.0, dt=self.dt)
            elif quant.name == 'Waveform - Y Signal':
                ge_frequency = 1e-3*self.getValue('G-E Frequency')
                ef_frequency = 1e-3*self.getValue('E-F Frequency')
                y_ge_signal = dsp_utils.modulate_signal(self.y_ge.build_sequence(),
                                                 self.dt,
                                                 ge_frequency,
                                                 0) \
                              + dsp_utils.modulate_signal(self.x_ge.build_sequence(),
                                                 self.dt,
                                                 ge_frequency,
                                                 0)
                y_ef_signal = dsp_utils.modulate_signal(self.y_ef.build_sequence(),
                                                 self.dt,
                                                 ef_frequency,
                                                 0) \
                              + dsp_utils.modulate_signal(self.x_ef.build_sequence(),
                                                 self.dt,
                                                 ef_frequency,
                                                 0)

                signal = y_ge_signal + y_ef_signal
                trace = quant.getTraceDict(signal, t0=0.0, dt=self.dt)
            elif quant.name == 'Waveform - Z Signal':
                signal = self.z.build_sequence()
                trace = quant.getTraceDict(signal, t0=0.0, dt=self.dt)
            elif quant.name == 'Waveform - Readout I':
                signal = self.readout_i.build_sequence()
                trace = quant.getTraceDict(signal, t0=0.0, dt=self.dt)
            elif quant.name == 'Waveform - Readout Q':
                signal = self.readout_q.build_sequence()
                trace = quant.getTraceDict(signal, t0=0.0, dt=self.dt)
            elif quant.name == 'Waveform - Readout Trigger':
                signal = self.readout_trigger.build_sequence()
                trace = quant.getTraceDict(signal, t0=0.0, dt=self.dt)
            return trace

        elif 'QB' in quant.name:
            demodulated_signal = self.demodulate()
            return demodulated_signal

        else: 
            # for other quantities, just return current value of control
            return quant.getValue()


    def update_basis_rotation_generators(self):
        """ Updates the stored dictionary of generator envelopes.

        The G-E and E-F pulses for state preparation and measurement basis
        rotation share the same pi and pi-half pulse envelopes. To differentiate
        a G-E pi pulse from an E-F pi pulse, the same pi envelope would be
        modulated at either the G-E or the E-F frequency. 

        This method updates the common envelope shapes whenever their parameters
        are updated."""
        generator_envelope_args = {
            'sampling_rate': self.getValue('Sampling Rate'),
            'pi_pulse_length': self.getValue('Pi Pulse Length'),
            'pi_pulse_sigma': self.getValue('Pi Pulse Sigmas'),
            'pi_pulse_amplitude': self.getValue('Pi Pulse Amplitude'),
            'pi_pulse_derivative_amplitude': \
                                self.getValue('Pi Pulse Derivative Amplitude'),
            'pi_half_pulse_length': self.getValue('Pi-Half Pulse Length'),
            'pi_half_pulse_sigma': self.getValue('Pi-Half Pulse Sigmas'),
            'pi_half_pulse_amplitude': self.getValue('Pi-Half Pulse Amplitude'),
            'pi_half_pulse_derivative_amplitude': \
                                self.getValue('Pi-Half Pulse Derivative Amplitude'),
            'z_bias': self.getValue('Basis Rotation Generator Z Bias'),
        }
        self.generator_envelopes = qpt.build_basis_rotation_envelopes(
                                       generator_envelope_args,
                                       const_detuning=True)


    def update_state_preparation_sequence(self):
        """Updates all the waveforms responsible for state preparation."""
        # Build the appropriate preparation sequence given the current index.
        initial_state_index = self.getValue('Initial State Index')
        ge, ef = qpt.build_state_preparation_sequence(initial_state_index,
                                                       self.generator_envelopes)
        self.x_ge.state_initialization = ge['x']
        self.y_ge.state_initialization = ge['y']
        self.x_ef.state_initialization = ef['x']
        self.y_ef.state_initialization = ef['y']
        self.z.state_initialization = ge['z'] + ef['z']

        # Fill the readout control channels with zeros because they do not
        # participate in state preparation.
        self.readout_i.state_initialization = np.zeros(len(ge['x']))
        self.readout_q.state_initialization = np.zeros(len(ge['x']))
        self.readout_trigger.state_initialization = np.zeros(len(ge['x']))


    def update_process_sequence(self):
        """Grabs the process waveforms that have been externally set.

        To allow for maximum flexibility of the process being
        tomograted, the process is defined externally in an arbitrary sequence
        generator and an external script is used to pass the waveform
        from the sequence generator into the `Process X/Y - G-E/E-F` fields
        of the QPT Driver. An example of such a script that performs this
        action can be found in connect_to_asg.py.

        Thus anytime a nontrivial (as in non-identity) process is to be
        tomograined, one must set up two arbitrary sequence generators (one for
        the G-E pulses and one for the E-F pulses) and the QPT driver, and then
        run the external script that passes the waveforms from the ASG's to QPT.

        Without this apparently cumbersome step, the only processes that this
        QPT driver (in its current manifestation) could tomogrep would be 
        entirely Clifford processes that the Clifford generators stored herein
        could create."""
        use_custom_process = self.getValue('Custom Process?')
        if use_custom_process:
            self.x_ge.process = self.getValue('Process X - G-E')['y']
            self.x_ef.process = self.getValue('Process X - E-F')['y']
            self.y_ge.process = self.getValue('Process Y - G-E')['y']
            self.y_ef.process = self.getValue('Process Y - E-F')['y']
            self.z.process = self.getValue('Process Z')['y']
    
            
        else:
            sampling_rate = self.getValue('Sampling Rate')
            envelope_amplitude = self.getValue('Process Pulse Amplitude')
            derivative_amplitude = self.getValue(
                                        'Process Pulse Derivative Amplitude')
            process_z_bias = self.getValue('Process Pulse Z Bias')
            gaussian_args = {
                'length': self.getValue('Process Pulse Length'),
                'sigma': self.getValue('Process Pulse Sigma'),
            }
            envelope, derivative = qpt.get_basic_gaussian_process_pulse(
                                                                sampling_rate,
                                                                gaussian_args)

            if 'G-E' in self.getValue('Process Pulse Frequency'):
                self.x_ge.process = envelope_amplitude * envelope
                self.y_ge.process = derivative_amplitude * derivative
                self.x_ef.process = np.zeros(len(envelope))
                self.y_ef.process = np.zeros(len(envelope))
            else:
                self.x_ge.process = np.zeros(len(envelope))
                self.y_ge.process = np.zeros(len(envelope))
                self.x_ef.process = envelope_amplitude * envelope
                self.y_ef.process = derivative_amplitude * derivative
            self.z.process = process_z_bias * np.ones(len(envelope))

        self.readout_i.process = np.zeros(len(self.x_ge.process))
        self.readout_q.process = np.zeros(len(self.x_ge.process))
        self.readout_trigger.process = np.zeros(len(self.x_ge.process))


    def update_measurement_basis_sequence(self):
        """Updates all the waveforms for rotating into a measurement basis."""
        # Build the proper pulse sequence based on the current index.
        measurement_preparation_index = self.getValue('Measurement Basis Index')
        ge, ef = qpt.build_measurement_preparation_sequence(measurement_preparation_index,
                                                            self.generator_envelopes)
        self.x_ge.measurement_preparation = ge['x']
        self.y_ge.measurement_preparation = ge['y']
        self.x_ef.measurement_preparation = ef['x']
        self.y_ef.measurement_preparation = ef['y']
        self.z.measurement_preparation = ge['z'] + ef['z']
        
        # Fill readout control channels with zeros because they don't
        # participate in measurement basis preparation.
        self.readout_i.measurement_preparation = np.zeros(len(ge['x']))
        self.readout_q.measurement_preparation = np.zeros(len(ge['x']))
        self.readout_trigger.measurement_preparation = np.zeros(len(ge['x']))


    def update_readout(self):
        """ Updates heralding and readout pulses.

        If readout or heralding parameters have updated, so too must the
        waveforms be updated.

        Readout is always performed, because QPT always requires readout. The
        only particularly nuanced part of the readout pulse generation is
        whether or not fast readout is requested. Without fast readout, the
        readout pulse is simply a pair of I and Q sinusoids of that ramp from
        no amplitude to a constant amplitude over a short period at the
        beginning of the pulse (currently hardcoded to be 2ns). If fast readout
        is requested, then rather than a linear amplitude ramp, the first 1/4
        of the readout pulse length will essentially be a modulated gaussian
        with an amplitude 3.5 times that of the slow readout signal. this is
        designed to fill the readout resonator with photons quickly, to reach
        readout steady state faster. After this first 1/4, the readout signal
        smoothly returns to what it would be in the slow readout case.

        If heralding is performed, then it consists of exactly the same pulse
        sequence as the readout at the end of QPT, plus some delay before the
        beginning of hte state preparation pulse sequence. Heralding allows one
        to post-select on the initial state of the qutrit before state
        preparation is attempted, to make sure, for example, that your qutrit
        has been initialized in the ground state.
        """
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

        # Create a simple rectangular window with a rising edge that will be
        # modulated into the readout signal
        readout_times = np.linspace(0, readout_length, sampling_rate*readout_length)
        rising_time = 2
        rising_edge_samples = int(sampling_rate*rising_time)
        envelope = np.ones(len(readout_times))
        rising_edge = np.linspace(0, 1, rising_edge_samples)
        envelope[:rising_edge_samples] = rising_edge

        # If fast readout is requested, change the first 1/4 of the rectangle
        # to be a gaussian with standard deviation equal to 1/8 the readout
        # length. The new envelope is just the product of the slow readout
        # rectangular envelope with a gaussian added to a constant 1 function.
        # In the tails of the gaussian, the gaussian + 1 just looks like 1, and
        # so the product with the slow envelope looks the same as the slow 
        # envelope, thus ensuring a smooth transition from gaussian peak to
        # steady state constant amplitude sinusoid.
        if do_fast_readout:
            # build a gaussian envelope that we can add on top of our normal
            # envelope
            gaussian_length = readout_length / 4
            gaussian_center = gaussian_length / 2
            sigma = gaussian_length/3
            gaussian_envelope = 1 + 2.5 * \
                np.exp(-(readout_times - gaussian_center)**2/(2*sigma**2))
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
            self.readout_trigger.readout = np.zeros(0)
            self.readout_trigger.heralding = np.zeros(0)
        else:
            trigger_length = self.getValue('Readout Trig Duration')
            trigger_amplitude = self.getValue('Readout Trig Amplitude')
            # Require at lest one point so we don't get needless index out of
            # range errors for rising and falling edge constraints.
            trigger_times = np.linspace(
                                0,
                                trigger_length,
                                sampling_rate*trigger_length + 1)
            trigger = trigger_amplitude*np.ones(len(trigger_times))
            # Enforce rising edge
            trigger[0] = 0
            # Enforce falling edge
            trigger[-1] = 0
            self.readout_trigger.readout = trigger

        # Update Z line (might be nonzero to accommodate readout bias)
        z = readout_z_bias*np.ones(len(readout_times))
        self.z.readout = z

        self.readout_i.readout = readout_i
        self.readout_q.readout = readout_q
        self.x_ge.readout = np.zeros(len(readout_i))
        self.x_ef.readout = np.zeros(len(readout_i))
        self.y_ge.readout = np.zeros(len(readout_i))
        self.y_ef.readout = np.zeros(len(readout_i))

        # If heralding is requested, do heralding.
        if do_heralding:
            # A delay after heralding is just accommodated by appending zeros to
            # all our heralding sequences corresponding to the delay time.
            heralding_delay = self.getValue('Delay After Heralding Pulse')
            heralding_downtime = np.linspace(
                                     0, # start time
                                     heralding_delay,
                                     sampling_rate*heralding_delay)
            heralding_gap_signal = np.zeros(len(heralding_downtime))

            self.readout_i.heralding = np.concatenate((readout_i,
                                                       heralding_gap_signal))
            self.readout_q.heralding = np.concatenate((readout_q,
                                                       heralding_gap_signal))
            self.z.heralding = np.concatenate((z, heralding_gap_signal))
            
            # The x and y pulse sequences are uniformly zero during heralding
            x_and_y_zeros = np.zeros(len(readout_i))
            
            self.x_ge.heralding = np.concatenate((x_and_y_zeros,
                                                  heralding_gap_signal))
            self.x_ef.heralding = np.concatenate((x_and_y_zeros,
                                                  heralding_gap_signal))
            self.y_ge.heralding = np.concatenate((x_and_y_zeros,
                                                  heralding_gap_signal))
            self.y_ef.heralding = np.concatenate((x_and_y_zeros,
                                                  heralding_gap_signal))
            
            # Trigger heralding is essentially the same with some extra edge
            # case handling in the event that the trigger length is set so long
            # it overlaps with state preparation.
            if do_generate_trigger:
                herald_trigger_holder = np.zeros(len(self.readout_i.heralding))
                herald_trigger = np.concatenate((trigger, heralding_gap_signal))
                # In the event that the heralding trigger overlaps with state
                # prep, truncate it.
                if len(herald_trigger) <= len(herald_trigger_holder):
                    herald_trigger_holder[:len(herald_trigger)] = herald_trigger
                else:
                    herald_trigger_holder = trigger_amplitude * \
                                                np.ones(len(herald_trigger_holder))
                    herald_trigger_holder[0] = 0
                    herald_trigger_holder[1] = 1
                self.readout_trigger.heralding = herald_trigger_holder
        else:
            # Make sure to unset everything if we remove heralding
            self.readout_i.heralding = np.zeros(0)
            self.readout_q.heralding = np.zeros(0)
            self.z.heralding = np.zeros(0)
            self.x_ge.heralding = np.zeros(0)
            self.y_ge.heralding = np.zeros(0)
            self.x_ef.heralding = np.zeros(0)
            self.y_ef.heralding = np.zeros(0)
            self.readout_trigger.heralding = np.zeros(0)


    def demodulate(self):
        """Demodulates a given signal assuming that it has been downconverted
        from fridge output RF to the same frequency as the IF Readout Frequency
        field of this Driver."""
        # I'm not really sure how we can be sure about the units of dt, which 
        # inform the units of this frequency. For example when I was running
        # simple tests demodulating the readout waveforms of another QPT driver
        # directly the units were in ns, but in VF's driver demodulation units
        # are in seconds...
        demodulation_frequency = self.getValue('Readout Frequency')*1e-3
        signal_i = self.getValue('Demodulation - Input I')
        signal_q = self.getValue('Demodulation - Input Q')
        readout_samples = int(self.getValue('Demodulation - Number of Samples'))
        dt = signal_i['dt']
        if dt == 0:
            dt = 1.0
        skip_start = int(self.getValue('Demodulation - Skip') / (dt*1e9))
        
        complex_signal = signal_i['y'] + 1j * signal_q['y']

        # In VF's demodulation code, he reshapes readout signals into chunks of
        # 'readout_samples' length, corresponding to the expected length of the
        # signal to demodulate - this seems to contradict the purpose of having
        # such a field to restrict the amount of signal that gets fed into 
        # demodulation?
        number_of_records = int(len(complex_signal) / readout_samples)

        # raise Exception(len(complex_signal))
        # Shape complex input signal to be as long as the expected demodulation
        holder = np.zeros(readout_samples)
        if len(complex_signal) < readout_samples:
            holder[:len(complex_signal)] = complex_signal
        else:
            holder = complex_signal[:readout_samples]
        complex_signal = holder

        # Define our demodulation reference as a 'cosine-like' (initial phase
        # 0) complex oscillating signal at the readout IF frequency
        t = np.linspace(0, dt*(readout_samples - 1), readout_samples)
        demodulation_reference = np.exp(-2j * np.pi * t * demodulation_frequency)

        # Perform the demodulation, which consists of a pointwise integral of
        # our signal against a complex demodulation reference tone of fixed 
        # frequency and phase
        # 1: Multiply signal and demodulation reference pointwise
        #demodulated_signal = complex_signal[skip_start: skip_start + readout_samples] * demodulation_reference[skip_start]
        demodulated_signal = complex_signal[skip_start:] * demodulation_reference[skip_start:]
        # 2: Sum pointwise multiplication to complete the integral
        demodulated_signal = np.sum(demodulated_signal)
        # 3: Normalize by length
        demodulated_signal = demodulated_signal / (readout_samples - skip_start)

        return demodulated_signal
