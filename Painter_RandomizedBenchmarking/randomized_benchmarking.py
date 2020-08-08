import os
import numpy as np
import scipy.optimize as opt

import DRAG_utils

# From Labber's random clifford generator
def add_singleQ_clifford(index, gate_seq):
    """Add single qubit clifford (24)."""
    length_before = len(gate_seq)
    # Paulis
    if index == 0:
        gate_seq.append('id')
    elif index == 1:
        gate_seq.append('xp')
    elif index == 2:
        gate_seq.append('yp')
    elif index == 3:
        gate_seq.append('yp')
        gate_seq.append('xp')

    # 2pi/3 rotations
    elif index == 4:
        gate_seq.append('x2p')
        gate_seq.append('y2p')
    elif index == 5:
        gate_seq.append('x2p')
        gate_seq.append('y2m')
    elif index == 6:
        gate_seq.append('x2m')
        gate_seq.append('y2p')
    elif index == 7:
        gate_seq.append('x2m')
        gate_seq.append('y2m')
    elif index == 8:
        gate_seq.append('y2p')
        gate_seq.append('x2p')
    elif index == 9:
        gate_seq.append('y2p')
        gate_seq.append('x2m')
    elif index == 10:
        gate_seq.append('y2m')
        gate_seq.append('x2p')
    elif index == 11:
        gate_seq.append('y2m')
        gate_seq.append('x2m')

    # pi/2 rotations
    elif index == 12:
        gate_seq.append('x2p')
    elif index == 13:
        gate_seq.append('x2m')
    elif index == 14:
        gate_seq.append('y2p')
    elif index == 15:
        gate_seq.append('y2m')
    elif index == 16:
        gate_seq.append('x2m')
        gate_seq.append('y2p')
        gate_seq.append('x2p')
    elif index == 17:
        gate_seq.append('x2m')
        gate_seq.append('y2m')
        gate_seq.append('x2p')

    # Hadamard-Like
    elif index == 18:
        gate_seq.append('xp')
        gate_seq.append('y2p')
    elif index == 19:
        gate_seq.append('xp')
        gate_seq.append('y2m')
    elif index == 20:
        gate_seq.append('yp')
        gate_seq.append('x2p')
    elif index == 21:
        gate_seq.append('yp')
        gate_seq.append('x2m')
    elif index == 22:
        gate_seq.append('x2p')
        gate_seq.append('y2p')
        gate_seq.append('x2p')
    elif index == 23:
        gate_seq.append('x2m')
        gate_seq.append('y2p')
        gate_seq.append('x2m')

    elif index == -1:
        gate_seq.append('noise')


def add_pulses_by_key(key, pulses, x, y, z):
    if key is 'id':
        x = np.concatenate((x, pulses['pi_identity']))
        y = np.concatenate((y, pulses['pi_identity']))
        z = np.concatenate((z, pulses['pi_identity']))
    elif key is 'xp':
        if 'x_pi' in pulses:
            x = np.concatenate((x, pulses['x_pi']))
            y = np.concatenate((y, pulses['x_pi_derivative']))
            z = np.concatenate((z, pulses['x_pi_detuning']))
        else:
            x = np.concatenate((x, pulses['pi']))
            y = np.concatenate((y, pulses['pi_derivative']))
            z = np.concatenate((z, pulses['pi_detuning']))
    elif key is 'yp':
        x = np.concatenate((x, -pulses['pi_derivative']))
        y = np.concatenate((y, pulses['pi']))
        z = np.concatenate((z, pulses['pi_detuning']))
    elif key is 'x2p':
        x = np.concatenate((x, pulses['pi_half']))
        y = np.concatenate((y, pulses['pi_half_derivative']))
        z = np.concatenate((z, pulses['pi_half_detuning']))
    elif key is 'x2m':
        x = np.concatenate((x, -pulses['pi_half']))
        y = np.concatenate((y, -pulses['pi_half_derivative']))
        z = np.concatenate((z, pulses['pi_half_detuning']))
    elif key is 'y2p':
        x = np.concatenate((x, -pulses['pi_half_derivative']))
        y = np.concatenate((y, pulses['pi_half']))
        z = np.concatenate((z, pulses['pi_half_detuning']))
    elif key is 'y2m':
        x = np.concatenate((x, pulses['pi_half_derivative']))
        y = np.concatenate((y, -pulses['pi_half']))
        z = np.concatenate((z, pulses['pi_half_detuning']))
    elif key is 'noise':
        x = np.concatenate((x, pulses['x_noise']))
        y = np.concatenate((y, pulses['y_noise']))
        z = np.concatenate((z, pulses['z_noise']))
    return x, y, z


def build_full_pulse_sequence(gate_seq, pulse_dictionary, sample_rate):
    x = np.zeros((0))
    y = np.zeros((0))
    z = np.zeros((0))
    for key in gate_seq:
        x, y, z = add_pulses_by_key(key, pulse_dictionary, x, y, z)
    
    # calculate total time
    num_gates = len(gate_seq)
    # total_time = pulse_len*num_gates
    # for now, cumbersomely assume that the noise gates are as long as the actual gates
    num_samples = len(x)
    total_time = num_samples / sample_rate
    times = np.linspace(0, total_time, num_samples)
    return x, y, z, times


def find_and_insert_clifford_inverse(gate_seq):
    dict_m1QBGate = {
        'id': np.matrix('1,0;0,1'),
        'x2p': 1/np.sqrt(2)*np.matrix('1,-1j;-1j,1'),
        'x2m': 1/np.sqrt(2)*np.matrix('1,1j;1j,1'),
        'y2p': 1/np.sqrt(2)*np.matrix('1,-1;1,1'),
        'y2m': 1/np.sqrt(2)*np.matrix('1,1;-1,1'),
        'z2p': np.matrix('1,0;0,1j'),
        'z2m': np.matrix('1,0;0,-1j'),
        'xp': np.matrix('0,-1j;-1j,0'),
        'xm': np.matrix('0,1j;1j,0'),
        'yp': np.matrix('0,-1;1,0'),
        'ym': np.matrix('0,1;-1,0'),
        'zp': np.matrix('1,0;0,-1'),
        'zm': np.matrix('-1,0;0,1')
    }
    for i in range(0,24):
        temp = gate_seq.copy()
        add_singleQ_clifford(i, temp)
        scratch = dict_m1QBGate['id']
        for key in temp:
            scratch = np.matmul(scratch, dict_m1QBGate[key])
        if (np.isclose(scratch, dict_m1QBGate['id'])).all():
            add_singleQ_clifford(i, gate_seq)
            return i
        if (np.isclose(scratch, -dict_m1QBGate['id'])).all():
            add_singleQ_clifford(i, gate_seq)
            return i
    return 0


def generate_random_clifford_sequence(length, noisy=False, interleaved_gate=None):
    random_indices = np.random.randint(0, 24, length)
    if interleaved_gate is not None:
        temp = []
        for index in random_indices:
            temp.append(index)
            temp.append(interleaved_gate)
        random_indices = temp
    ideal_gate_seq = []
    for index in random_indices:
        add_singleQ_clifford(index, ideal_gate_seq)
    inverse_index = find_and_insert_clifford_inverse(ideal_gate_seq)
    
    if noisy is not True:
        return ideal_gate_seq
    
    # If we are artificially inserting our own noise, it was necessary to first
    # compute the ideal clifford sequence so we could find the ideal final
    # inverse gate.
    noisy_indices = []
    noisy_gate_sequence = []
    for i in range(len(random_indices)):
        noisy_indices.append(random_indices[i])
        noisy_indices.append(-1) # noise flag
    # Insert the final inverting gate and its associated noise
    noisy_indices.append(inverse_index)
    noisy_indices.append(-1)
    # Turn the noisy indices into pulse labels
    for index in noisy_indices:
        add_singleQ_clifford(index, noisy_gate_sequence)
    return noisy_gate_sequence


def build_full_pulse_sequence_interleaved_noise(gate_seq, pulse_len, pulse_dictionary, noise_pulses, sample_rate):
    x = np.zeros((0))
    y = np.zeros((0))
    z = np.zeros((0))
    for key in gate_seq:
        x, y, z = add_pulses_by_key(key, pulse_dictionary, x, y, z)
        x, y, z = add_noise(x, y, z, noise_pulses)
    
    # calculate total time
    num_gates = len(gate_seq)
    total_time = pulse_len*num_gates
    times = np.linspace(0, total_time, sample_rate*total_time)
    return x, y, z, times


def add_noise(x, y, z, noise_pulses):
    x = np.concatenate((x, noise_pulses['x']))
    y = np.concatenate((y, noise_pulses['y']))
    z = np.concatenate((y, noise_pulses['y']))


def build_generator_signals(sample_rate,
                            pi_params,
                            pi_half_params,
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
    A_pi = 1
    A_pi_half = 1

    pi_length = pi_params['length']
    pi_half_length = pi_half_params['length']
    
    # Arguments for envelopes
    pi_envelope_args = {
        'A': A_pi,
        'x_coeff': 1,
        'y_coeff': 1,
        'det_coeff': pi_params['detuning'],
        'tg': pi_length / 2,
        'tn': pi_length / 2,
        'tsigma': pi_params['standard_deviation']
    }
    
    pi_half_envelope_args = {
        'A': A_pi_half,
        'x_coeff': 1,
        'y_coeff': 1,
        'det_coeff': pi_half_params['detuning'],
        'tg': pi_half_length / 2,
        'tn': pi_half_length / 2,
        'tsigma': pi_half_params['standard_deviation']
    }

    _, pi_ref, pi_deriv_ref, _ = \
            DRAG_utils.create_constant_detuning_DRAG_envelopes(sample_rate,
                                           pi_length,
                                           pi_envelope_args)
    _, pi_half_ref, pi_half_deriv_ref, _ = \
            DRAG_utils.create_constant_detuning_DRAG_envelopes(sample_rate, 
                                           pi_half_length, 
                                           pi_half_envelope_args)
    
    if np.max(pi_ref['r']) > 0:
        pi_envelope_args['x_coeff'] = pi_params['amplitude'] \
                                         / np.max(pi_ref['r'])
        pi_envelope_args['y_coeff'] = pi_params['derivative_amplitude'] \
                                         / np.max(pi_deriv_ref['r'])
    if np.max(pi_half_ref['r']) > 0:
        pi_half_envelope_args['x_coeff'] = pi_half_params['amplitude'] \
                                         / np.max(pi_half_ref['r'])
        pi_half_envelope_args['y_coeff'] = pi_half_params['derivative_amplitude'] \
                                         / np.max(pi_half_deriv_ref['r'])
    
    if const_detuning:
        times, pi_env, pi_deriv, pi_dets = \
            DRAG_utils.create_constant_detuning_DRAG_envelopes(sample_rate,
                                           pi_length,
                                           pi_envelope_args)
        times, pi_half_env, pi_half_deriv, pi_half_dets = \
            DRAG_utils.create_constant_detuning_DRAG_envelopes(sample_rate, 
                                           pi_half_length, 
                                           pi_half_envelope_args)
    else:
        times, pi_env, pi_deriv, pi_dets = \
            DRAG_utils.create_ge_envelopes(sample_rate,
                                           pi_length,
                                           pi_envelope_args)
        times, pi_half_env, pi_half_deriv, pi_half_dets = \
            DRAG_utils.create_ge_envelopes(sample_rate, 
                                           pi_half_length, 
                                           pi_half_envelope_args)
    pi_identity = np.zeros(len(pi_env['r']))
    pi_half_identity = np.zeros(len(pi_half_env['r']))
    
    # Construct the pulse dictionary:
    pulse_dict = {
      'pi_identity': pi_identity,
      'pi_half_identity': pi_half_identity,
      'pi': np.array(pi_env['r']),
      'pi_derivative': np.array(pi_deriv['r']),
      'pi_detuning': np.array(pi_dets['r']),
      'pi_half': np.array(pi_half_env['r']),
      'pi_half_derivative': np.array(pi_half_deriv['r']),
      'pi_half_detuning': np.array(pi_half_dets['r']),
    }
    return pulse_dict


def build_simple_x_noise(angle, pulse_len, sample_rate, DRAG_params):
    """ Construct the X, Y, and Z signals for an X rotation

    Though the result of this function is to make a completely general X
    rotation, it's named suggestively because it's meant to be used to
    create a simple noise channel that consists of a small rotation about the X
    axis of the Bloch sphere.
    
    Args:
      angle: the small angle of rotation about X
      pulse_len: the length of the noise channel in ns
      sample_rate: the sample rate of the signals to create in GHz
      DRAG_params: a dictionary of the first order DRAG coefficients for each
          control line. allow for DRAG on the rotation so that the infidelity of
          the noise is as engineered as possible (ie: minimize infidelity of
          the noise that comes from any source other than it being a spurious
          rotation).
    Returns:
      3 numpy 1D arrays corresponding to the noise signals."""
    envelope_args = {
        'A': angle,
        'x_coeff': DRAG_params['x_coeff'],
        'y_coeff': DRAG_params['y_coeff'],
        'det_coeff': DRAG_params['det_coeff'],
        'tg': pulse_len/2,
        'tn': pulse_len/2,
        'tsigma': pulse_len/4
    }
    _, x_noise, y_noise, z_noise = \
        DRAG_utils.create_ge_envelopes(sample_rate,
                                       pulse_len,
                                       envelope_args)
    return np.array(x_noise['r']), \
           np.array(y_noise['r']), \
           np.array(z_noise['r'])

