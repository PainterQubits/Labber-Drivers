import numpy as np

import DRAG_utils as DRAG_utils
import dsp_utils

# This maps a simple integer index to a list of readable labels for the pulses
# that are needed to initialize a particular input state for 3LS QPT
prep_sequence_indices_to_pulse_labels = {
    0: [],                    # |g>
    1: ['y_ge'],              # |e>
    2: ['y_ge', 'y_ef'],      # |f>
    3: ['y_half_ge'],         # |g> + |e>
    4: ['y_half_ge', 'y_ef'], # |g> + |f>
    5: ['y_ge', 'y_half_ef'], # |e> + |f>
    6: ['x_half_ge'],         # |g> + i|e>
    7: ['x_half_ge', 'y_ef'], # |g> + i|f>
    8: ['x_ge', 'y_half_ef']  # |e> + i|f>
}

# This maps a simple integer index to a list of readable labels for the pulses
# that are needed to rotate into a particular measurement basis for 3LS QPT
measurement_sequence_indices_to_pulse_labels = {
    0: [],                    # gg, ee, ff
    1: ['y_half_ge'],         # Re(ge)
    2: ['x_half_ge'],         # Im(ge)
    3: ['y_half_ef'],         # Re(ef)
    4: ['x_half_ef'],         # Im(ef)
    5: ['y_ge', 'y_half_ef'], # Re(gf)
    6: ['y_ge', 'x_half_ef'], # Im(gf)
}


def add_pulses_by_key(key, pulse_dictionary, ge, ef):
    """Converts readable pulse labels into numpy array of pulse

    Assuming that you have a valid pulse_dictionary that contains all the
    requisite 3LS Clifford generators in numpy array form, this function
    converts a human readable label of a given Clifford into a sequence of 
    Clifford generators that generate the pulse associated with that label.

    This is done also assuming pulses are defined by three seperate x, y, and
    z control lines.

    Args:
        key: the human readable label of the Clifford from the allowed set
             (see the index to pulse labels dictionaries above for defined
             labels)
        pulse_dictionary: A dictionary that contains general Clifford
            generator pulse envelopes
        ge: Because we're dealing with 3LS, and we want to upconvert ge and ef
            control signals separately, we pass in a container to hold the ge
            parts of the pulse
        ef: Like ge but for ef parts of the pulse
    """
        
    if key is 'x_ge':
        ge['x'] = np.concatenate((ge['x'], pulse_dictionary['pi']))
        ge['y'] = np.concatenate((ge['y'], pulse_dictionary['pi_derivative']))
        ge['z'] = np.concatenate((ge['z'], pulse_dictionary['pi_detuning']))
        ef['x'] = np.concatenate((ef['x'], pulse_dictionary['identity']))
        ef['y'] = np.concatenate((ef['y'], pulse_dictionary['identity']))
        ef['z'] = np.concatenate((ef['z'], pulse_dictionary['identity']))
    elif key is 'x_ef':
        ef['x'] = np.concatenate((ef['x'], pulse_dictionary['pi']))
        ef['y'] = np.concatenate((ef['y'], pulse_dictionary['pi_derivative']))
        ef['z'] = np.concatenate((ef['z'], pulse_dictionary['pi_detuning']))
        ge['x'] = np.concatenate((ge['x'], pulse_dictionary['identity']))
        ge['y'] = np.concatenate((ge['y'], pulse_dictionary['identity']))
        ge['z'] = np.concatenate((ge['z'], pulse_dictionary['identity']))
    elif key is 'x_half_ge':
        ge['x'] = np.concatenate((ge['x'], pulse_dictionary['pi_half']))
        ge['y'] = np.concatenate((ge['y'], pulse_dictionary['pi_half_derivative']))
        ge['z'] = np.concatenate((ge['z'], pulse_dictionary['pi_half_detuning']))
        ef['x'] = np.concatenate((ef['x'], pulse_dictionary['identity']))
        ef['y'] = np.concatenate((ef['y'], pulse_dictionary['identity']))
        ef['z'] = np.concatenate((ef['z'], pulse_dictionary['identity']))
    elif key is 'x_half_ef':
        ef['x'] = np.concatenate((ef['x'], pulse_dictionary['pi_half']))
        ef['y'] = np.concatenate((ef['y'], pulse_dictionary['pi_half_derivative']))
        ef['z'] = np.concatenate((ef['z'], pulse_dictionary['pi_half_detuning']))
        ge['x'] = np.concatenate((ge['x'], pulse_dictionary['identity']))
        ge['y'] = np.concatenate((ge['y'], pulse_dictionary['identity']))
        ge['z'] = np.concatenate((ge['z'], pulse_dictionary['identity']))
    elif key is 'y_ge':
        ge['y'] = np.concatenate((ge['y'], pulse_dictionary['pi']))
        ge['x'] = np.concatenate((ge['x'], -pulse_dictionary['pi_derivative']))
        ge['z'] = np.concatenate((ge['z'], pulse_dictionary['pi_detuning']))
        ef['x'] = np.concatenate((ef['x'], pulse_dictionary['identity']))
        ef['y'] = np.concatenate((ef['y'], pulse_dictionary['identity']))
        ef['z'] = np.concatenate((ef['z'], pulse_dictionary['identity']))
    elif key is 'y_ef':
        ef['y'] = np.concatenate((ef['y'], pulse_dictionary['pi']))
        ef['x'] = np.concatenate((ef['x'], -pulse_dictionary['pi_derivative']))
        ef['z'] = np.concatenate((ef['z'], pulse_dictionary['pi_detuning']))
        ge['x'] = np.concatenate((ge['x'], pulse_dictionary['identity']))
        ge['y'] = np.concatenate((ge['y'], pulse_dictionary['identity']))
        ge['z'] = np.concatenate((ge['z'], pulse_dictionary['identity']))
    elif key is 'y_half_ge':
        ge['y'] = np.concatenate((ge['y'], pulse_dictionary['pi_half']))
        ge['x'] = np.concatenate((ge['x'], -pulse_dictionary['pi_half_derivative']))
        ge['z'] = np.concatenate((ge['z'], pulse_dictionary['pi_half_detuning']))
        ef['x'] = np.concatenate((ef['x'], pulse_dictionary['identity']))
        ef['y'] = np.concatenate((ef['y'], pulse_dictionary['identity']))
        ef['z'] = np.concatenate((ef['z'], pulse_dictionary['identity']))
    elif key is 'y_half_ef':
        ef['y'] = np.concatenate((ef['y'], pulse_dictionary['pi_half']))
        ef['x'] = np.concatenate((ef['x'], -pulse_dictionary['pi_half_derivative']))
        ef['z'] = np.concatenate((ef['z'], pulse_dictionary['pi_half_detuning']))
        ge['x'] = np.concatenate((ge['x'], pulse_dictionary['identity']))
        ge['y'] = np.concatenate((ge['y'], pulse_dictionary['identity']))
        ge['z'] = np.concatenate((ge['z'], pulse_dictionary['identity']))


def build_basis_rotation_envelopes(generator_envelope_args,
                                   const_detuning=False):
    """ Creates the signals for a pi and pi-half pulse.

    Args:
      pulse_len: the length of the pulses in ns
      sample_rate: the sampling rate of the signal in GHz
      DRAG_params: the DRAG coefficients to use
    Returns:
      A dictionary of 1D numpy arrays of length set by pulse_len*sample_rate
      for the gaussian envelope, derivative envelope, and detuning envelope of
      pi and pi-half pulses, as well as an identity pulse of pulse_len."""
    sample_rate = generator_envelope_args['sampling_rate']
    z_bias = generator_envelope_args['z_bias']
    
    # Arguments for envelopes
    pi_envelope_args = {
        'A': 1,
        'x_coeff': 1,
        'y_coeff': 1/2,
        'det_coeff': z_bias,
        'tg': generator_envelope_args['pi_pulse_length']/2,
        'tn': generator_envelope_args['pi_pulse_length']/2,
        'tsigma': generator_envelope_args['pi_pulse_length']/4
    }
    
    pi_half_envelope_args = {
        'A': 1,
        'x_coeff': 1,
        'y_coeff': 1/2,
        'det_coeff': z_bias,
        'tg': generator_envelope_args['pi_half_pulse_length']/2,
        'tn': generator_envelope_args['pi_half_pulse_length']/2,
        'tsigma': generator_envelope_args['pi_half_pulse_length']/4,
    }
    
    _, reference_pi, _, _ = \
            DRAG_utils.create_constant_detuning_DRAG_envelopes(sample_rate,
                            generator_envelope_args['pi_pulse_length'],
                            pi_envelope_args)
    _, reference_pi_half, _, _ = \
            DRAG_utils.create_constant_detuning_DRAG_envelopes(sample_rate,
                            generator_envelope_args['pi_half_pulse_length'],
                            pi_half_envelope_args)

    pi_envelope_args['A'] = pi_envelope_args['A'] / np.max(reference_pi['r'])
    pi_envelope_args['x_coeff'] = generator_envelope_args['pi_pulse_amplitude']
    pi_half_envelope_args['A'] = pi_half_envelope_args['A'] \
                                    / np.max(reference_pi_half['r'])
    pi_half_envelope_args['x_coeff'] = \
                            generator_envelope_args['pi_half_pulse_amplitude']

    if const_detuning:
        times, pi_env, pi_deriv, pi_dets = \
            DRAG_utils.create_constant_detuning_DRAG_envelopes(sample_rate,
                                           generator_envelope_args['pi_pulse_length'],
                                           pi_envelope_args)
        times, pi_half_env, pi_half_deriv, pi_half_dets = \
            DRAG_utils.create_constant_detuning_DRAG_envelopes(sample_rate, 
                                           generator_envelope_args['pi_half_pulse_length'], 
                                           pi_half_envelope_args)
    else:
        times, pi_env, pi_deriv, pi_dets = \
            DRAG_utils.create_ge_envelopes(sample_rate,
                                           generator_envelope_args['pi_pulse_length'],
                                           pi_envelope_args)
        times, pi_half_env, pi_half_deriv, pi_half_dets = \
            DRAG_utils.create_ge_envelopes(sample_rate, 
                                           generator_envelope_args['pi_half_pulse_length'], 
                                           pi_half_envelope_args)
    identity = np.zeros(len(pi_env['r']))
    
    pi_derivative = generator_envelope_args['pi_pulse_derivative_amplitude'] \
                        * np.array(pi_deriv['r'])
    pi_half_derivative = generator_envelope_args['pi_half_pulse_derivative_amplitude'] \
                        * np.array(pi_deriv['r'])

    # Construct the pulse dictionary:
    pulse_dict = {
      'identity': identity,
      'pi': np.array(pi_env['r']),
      'pi_derivative': pi_derivative,
      'pi_detuning': np.array(pi_dets['r']),
      'pi_half': np.array(pi_half_env['r']),
      'pi_half_derivative': pi_half_derivative,
      'pi_half_detuning': np.array(pi_half_dets['r']),
    }
    return pulse_dict


def build_state_preparation_sequence(index, generators):
    """ Converts an index into a particular state preparation pulse sequence.

    Args:
        index: an integer between 0 and 8 that uniquely identifies an input
            state for 3LS QPT as per prep_sequence_indices_to_pulse_labels.
        generators: a dictionary of general Clifford generator pulse shapes.
    Returns:
        Two dictionaries containing the separate ge and ef x, y, and z numpy
        array encoded pulse sequences for the state prepration sequence defined
        by index.
    """
    ge = {
        'x': np.zeros(0),
        'y': np.zeros(0),
        'z': np.zeros(0)
    }
    ef = {
        'x': np.zeros(0),
        'y': np.zeros(0),
        'z': np.zeros(0)
    }
    if index not in prep_sequence_indices_to_pulse_labels:
        index = 0
    sequence =  prep_sequence_indices_to_pulse_labels[index] 
    for key in sequence:
        add_pulses_by_key(key, generators, ge, ef)
    return ge, ef


def build_measurement_preparation_sequence(index, generators):
    """ Converts an index into a particular measurement basis rotation sequence.

    Args:
        index: an integer between 0 and 8 that uniquely identifies an input
            state for 3LS QPT as per measurement_sequence_indices_to_pulse_labels.
        generators: a dictionary of general Clifford generator pulse shapes.
    Returns:
        Two dictionaries containing the separate ge and ef x, y, and z numpy
        array encoded pulse sequences for the measurement basis rotation sequence 
        defined by index.
    """
    ge = {
        'x': np.zeros(0),
        'y': np.zeros(0),
        'z': np.zeros(0)
    }
    ef = {
        'x': np.zeros(0),
        'y': np.zeros(0),
        'z': np.zeros(0)
    }
    if index not in measurement_sequence_indices_to_pulse_labels:
        index = 0
    sequence =  measurement_sequence_indices_to_pulse_labels[index] 
    for key in sequence:
        add_pulses_by_key(key, generators, ge, ef)
    return ge, ef


def get_basic_gaussian_process_pulse(sampling_rate, gaussian_args):
    """Returns a gaussian pulse envelope and its associated derivative
    envelope."""
    envelope_args = {
        'A': 1,
        'x_coeff': 1,
        'y_coeff': 1/2,
        'det_coeff': 0,
        'tg': gaussian_args['length']/2,
        'tn': gaussian_args['length']/2,
        'tsigma': gaussian_args['length']/4
    }
    _, envelope, derivative, _ = \
            DRAG_utils.create_constant_detuning_DRAG_envelopes(sampling_rate,
                    gaussian_args['length'],
                    envelope_args)
    envelope = envelope['r'] / np.max(envelope['r'])
    derivative = derivative['r'] / np.max(derivative['r'])
    return envelope, derivative

