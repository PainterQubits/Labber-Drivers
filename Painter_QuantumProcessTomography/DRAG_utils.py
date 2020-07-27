""" A super cool file for helping with DRAG stuff."""
import numpy as np
import scipy
import dsp_utils

# Empty envelopes
def empty_detuning_envelope(t, args):
    return 0


def empety_x_envelope(t, args):
    return 0


def empty_y_envelope(t, args):
    return 0


# Helper functions for building gaussian pulses
def gaussian(t, sigma):
    return np.exp(-t**2/(2*sigma**2))


def truncated_gaussian(t, sigma, t0, tn):
    erf_part = scipy.special.erf((tn)/(np.sqrt(2)*sigma))
    numerator = gaussian(t-t0, sigma) \
                    - gaussian(tn, sigma)
    denominator = np.sqrt(2*np.pi*sigma**2)*erf_part \
                      - 2*tn*gaussian(tn, sigma)
    return numerator/denominator


def truncated_gaussian_derivative(t, sigma, t0, tn):
    erf_part = scipy.special.erf((tn)/(np.sqrt(2)*sigma))
    numerator = -(t - t0)/(sigma**2) \
                    * gaussian(t-t0, sigma)
    denominator = np.sqrt(2*np.pi*sigma**2)*erf_part \
                  - 2*tn*gaussian(tn, sigma)
    return numerator/denominator


# Functions for bottom two level DRAG in an anharmonic oscillator
def x_envelope_ge(t, args):
    erf_part = scipy.special.erf(args['tn']/(np.sqrt(2)*args['tsigma']))
    numerator = np.exp(-(t - args['tg'])**2/(2*args['tsigma']**2)) - \
        np.exp(-args['tn']**2/(2*args['tsigma']**2))
    denominator = np.sqrt(2*np.pi*args['tsigma']**2)*erf_part - \
        2*args['tn']*np.exp(-args['tn']**2/(2*args['tsigma']**2))
    return args['x_coeff']*args['A']*numerator/denominator


def y_envelope_ge(t, args):
    erf_part = scipy.special.erf(args['tn']/(np.sqrt(2)*args['tsigma']))
    numerator = -(t-args['tg'])/(args['tsigma']**2) * \
        np.exp(-(t - args['tg'])**2/(2*args['tsigma']**2))
    denominator = np.sqrt(2*np.pi*args['tsigma']**2)*erf_part - \
        2*args['tn']*np.exp(-args['tn']**2/(2*args['tsigma']**2))
    return args['y_coeff']*args['A']*numerator/denominator


def det_envelope_ge(t, args):
    erf_part = scipy.special.erf(args['tn']/(np.sqrt(2)*args['tsigma']))
    numerator = np.exp(-(t - args['tg'])**2/(2*args['tsigma']**2)) - \
        np.exp(-args['tn']**2/(2*args['tsigma']**2))
    denominator = np.sqrt(2*np.pi*args['tsigma']**2)*erf_part - \
        2*args['tn']*np.exp(-args['tn']**2/(2*args['tsigma']**2))
    return args['det_coeff']*(args['A']*numerator/denominator)**2


# Functions for intermediate DRAG in an anharmonic oscillator
def x_envelope_ef(t, args):
    """In-Phase Quadrature Envelope for e->f DRAG."""
    return args['A'] * truncated_gaussian(t,
                           args['sigma'],
                           args['t_g']/2,
                           args['t_n']/2)


def y_envelope_ef(t, args):
    """Out-of-Phase Quadrature Envelope for e->f DRAG."""
    anharms = args['anharms']
    couplings = args['couplings']
    e = args['e']
    g = args['g']
    couplings = [c/g for c in couplings]
    coeff = -np.sqrt(couplings[e-1]**2 \
                     + (anharms[e+2]**2/anharms[e-1]**2) \
                     * couplings[e+1]**2) / (2*anharms[e+2])
    return args['A'] * coeff * truncated_gaussian_derivative(t,
                                   args['sigma'],
                                   args['t_g']/2,
                                   args['t_n']/2)


def detuning_envelope_ef(t, args):
    """Detuning envelope for e->f DRAG."""
    anharms = args['anharms']
    couplings = args['couplings']
    e = args['e']
    g = args['g']
    couplings = [c/g for c in couplings]
    coeff = (couplings[e-1]**2 \
                - (anharms[e+2]**2/anharms[e-1]**2) \
                * couplings[e+1]) / (4*anharms[e+2])
    return coeff*(args['A'] * truncated_gaussian(t,
                                  args['sigma'],
                                  args['t_g']/2,
                                  args['t_n']/2))**2


def create_ge_envelopes(sample_rate,
                        gate_time,
                        envelope_args,
                        modulation_args=None,
                        quantization_args=None,
                        upsampling_args=None,
                        noise_args=None):
    """Returns analytically optimal first order DRAG control pulses. 

    Args:
        sample_rate: the sample rate in GSa/s of the pulses
        gate_time: the length in ns of the DRAG gates
        envelope_args: the desired parameters for the X control gaussian
        modulation_args: the parameters for upconverting the envelopes
        quantization_args: for testing - the parameters for quantizing the
            pulses
        upsampling_args: for testing - the parameters for increasing pulse
            resolution
        noise_args: for testing - paremeters for adding noise to pulses
    Returns:
        An np array of the times associated with each pulse value, in ns
        An np array of the x control line in V
        An np array of the y control line in V
        An np array of the z control line in V
    """
    xs, times = dsp_utils.create_custom_signal(
			      x_envelope_ge,
                              sample_rate,
                              gate_time,
	                      envelope_args=envelope_args,
 			      modulation_args=modulation_args,
                              quantization_args=quantization_args,
                              upsampling_args=upsampling_args,
                              noise_args=noise_args)
    ys, _ = dsp_utils.create_custom_signal(
			      y_envelope_ge,
                              sample_rate,
                              gate_time,
	                      envelope_args=envelope_args,
 			      modulation_args=modulation_args,
                              quantization_args=quantization_args,
                              upsampling_args=upsampling_args,
                              noise_args=noise_args)
    dets, _ = dsp_utils.create_custom_signal(
			      det_envelope_ge,
                              sample_rate,
                              gate_time,
	                      envelope_args=envelope_args,
 			      modulation_args=modulation_args,
                              quantization_args=quantization_args,
                              upsampling_args=upsampling_args,
                              noise_args=noise_args)
    return times, xs, ys, dets


def create_constant_detuning_DRAG_envelopes(sample_rate,
                                            gate_time,
                                            envelope_args,
                                            modulation_args=None,
                                            quantization_args=None,
                                            upsampling_args=None,
                                            noise_args=None):
    """Returns DRAG control pulses with a constant detuning line.

    Analytically derived optimal first order DRAG includes the square of the X
    control pulse on the detuning Z line, but solutions can be found through
    optimization methods that instead have different X and Y control weightings
    and a constant detuning control. This function simply returns DRAG shaped
    X and Y control pulses with a constant Z control pulse instead of the
    analytic Z control solution.

    Args:
        sample_rate: the sample rate in GSa/s of the pulses
        gate_time: the length in ns of the DRAG gates
        envelope_args: the desired parameters for the X control gaussian
        modulation_args: the parameters for upconverting the envelopes
        quantization_args: for testing - the parameters for quantizing the
            pulses
        upsampling_args: for testing - the parameters for increasing pulse
            resolution
        noise_args: for testing - paremeters for adding noise to pulses
    Returns:
        An np array of the times associated with each pulse value, in ns
        An np array of the x control line in V
        An np array of the y control line in V
        An np array of the z control line in V
    """
    xs, times = dsp_utils.create_custom_signal(
			        x_envelope_ge,
                    sample_rate,
                    gate_time,
	                envelope_args=envelope_args,
 			        modulation_args=modulation_args,
                    quantization_args=quantization_args,
                    upsampling_args=upsampling_args,
                    noise_args=noise_args)
    ys, _ = dsp_utils.create_custom_signal(
			    y_envelope_ge,
                sample_rate,
                gate_time,
	            envelope_args=envelope_args,
 			    modulation_args=modulation_args,
                quantization_args=quantization_args,
                upsampling_args=upsampling_args,
                noise_args=noise_args)

    def const_function(t, args=None):
        return envelope_args['det_coeff']
    dets, _ = dsp_utils.create_custom_signal(
                  const_function,
                  sample_rate,
                  gate_time,
                  envelope_args=None,
                  modulation_args=None,
                  quantization_args=quantization_args,
                  upsampling_args=upsampling_args,
                  noise_args=noise_args)
    return times, xs, ys, dets

