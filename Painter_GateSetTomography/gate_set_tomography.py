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
    elif key == 'xp':
        x = np.concatenate((x, pulses['pi']))
        y = np.concatenate((y, pulses['pi_derivative']))
        z = np.concatenate((z, pulses['pi_detuning']))
    elif key is 'yp':
        x = np.concatenate((x, -pulses['pi_derivative']))
        y = np.concatenate((y, pulses['pi']))
        z = np.concatenate((z, pulses['pi_detuning']))
    elif key == 'x2p':
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
    else:
        raise Exception(key)
    return x, y, z


def build_full_pulse_sequence(gate_seq,
                              pulse_dictionary,
                              sample_rate):
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


def generate_random_clifford_sequence(length):
    random_indices = np.random.randint(0, 24, length)
    gate_seq = []
    for index in random_indices:
        add_singleQ_clifford(index, gate_seq)
    inverse_index = find_and_insert_clifford_inverse(gate_seq)

    return gate_seq


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
    pi_post_delay = int(pi_params['delay'])
    pi_half_post_delay = int(pi_half_params['delay'])

    pi_delay_signal = np.ones(pi_post_delay)
    pi_half_delay_signal = np.ones(pi_half_post_delay)

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
                                         / np.max(pi_ref['r'])
    if np.max(pi_half_ref['r']) > 0:
        pi_half_envelope_args['x_coeff'] = pi_half_params['amplitude'] \
                                         / np.max(pi_half_ref['r'])
        pi_half_envelope_args['y_coeff'] = pi_half_params['derivative_amplitude'] \
                                         / np.max(pi_half_ref['r'])

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
    pi_identity = np.zeros(len(pi_env['r']) + pi_post_delay)
    pi_half_identity = np.zeros(len(pi_half_env['r']) + pi_half_post_delay)

    pi_envelope = np.concatenate((np.array(pi_env['r']),
                            0 * pi_delay_signal))
    pi_derivative = np.concatenate((np.array(pi_deriv['r']),
                            0 * pi_delay_signal))
    pi_detuning = np.concatenate((np.array(pi_dets['r']),
                            pi_params['detuning'] * pi_delay_signal))

    pi_half_envelope = np.concatenate((np.array(pi_half_env['r']),
                            0 * pi_half_delay_signal))
    pi_half_derivative = np.concatenate((np.array(pi_half_deriv['r']),
                            0 * pi_half_delay_signal))
    pi_half_detuning = np.concatenate((np.array(pi_half_dets['r']),
                            pi_half_params['detuning'] * pi_half_delay_signal))

    # Construct the pulse dictionary:
    pulse_dict = {
      'pi_identity': pi_identity,
      'pi_half_identity': pi_half_identity,
      'pi': pi_envelope,
      'pi_derivative': pi_derivative,
      'pi_detuning': pi_detuning,
      'pi_half': pi_half_envelope,
      'pi_half_derivative': pi_half_derivative,
      'pi_half_detuning': pi_half_detuning,
    }
    return pulse_dict


def parse_gst_file(path):
    pygsti_to_driver_labels_dict = {
        'y': 'y2p',
        'x': 'x2p',
        'ypi': 'yp',
        'i': 'id',
    }

    # utility function for expanding germs, assumes that there is a germ in the
    # given experiment string, as specified by a number of gates being enclosed
    # in parentheses
    def expand_germ(experiment_string):
        germ_repetitions = 1
        # if specified in the experiment string, set 
        if '^' in experiment_string:
            temp = experiment_string.split('^')
            next_G_index = temp[1].find('G')
            if next_G_index > -1:
                numerical_substring = temp[1][0:next_G_index]
                measurement_basis_substring = temp[1][next_G_index:]
            else:
                numerical_substring = temp[1]
                measurement_basis_substring = ''
            germ_repetitions = int(numerical_substring.strip())
            experiment_string = temp[0] + measurement_basis_substring
        
        if experiment_string[0] == '(':
            temp_1 = experiment_string[1:]
            prep = ''
            temp_2 = temp_1.split(')')
        else:
            temp_1 = experiment_string.split('(')
            prep = temp_1[0]
            temp_2 = temp_1[1].split(')')
        
        germ = temp_2[0]

        if len(temp_2) > 1:
            measure = temp_2[1]
        else:
            measure = ''

        expanded_germs = ''
        for i in range(germ_repetitions):
            expanded_germs += germ        

        return (prep + expanded_germs + measure).strip()

    experiments = []
    with open(path) as f:
        for line in f:
            experiment_string = line.split()[0]

            if '#' in experiment_string:
                continue

            elif '{}' in experiment_string:
                experiments.append(['noop'])
                continue

            elif '(' in experiment_string:
                experiment_string = expand_germ(experiment_string)

            # Annoyingly split will return an initial empty string when the
            # split character is the first character of the string being split
            gates = experiment_string[1:].split('G')
            experiments.append([pygsti_to_driver_labels_dict[gate_label] for
                                    gate_label in gates])

    return experiments


