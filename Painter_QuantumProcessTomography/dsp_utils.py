# A utility file for helper functions for digital signal processing tasks like
# modulating a signal or quantization or simulating ADC or DAC etc.

import numpy as np
import scipy
from scipy import signal

def modulate_signal(sig, dt, freq, phase):
  """ Constructs a modulating sinusoid of frequency freq and does a point by
  point multiplication with signal to return the modulated signal. Note that
  the frequency and time step need top be commensurate, ie: use ns for GHz and
  us for MHz.
  
  Args:
    sig: A 1D numpy array. The signal to modulate.
    dt: The time step between samples of signal.
    freq: The desired frequency of the modulating signal.
    phase: The desired phase of the modulating signal.
  Returns:
    A numpy array of length len(sig) holding the modulated signal.
  """
  times = np.arange(0, len(sig))*dt
  modulating_signal = np.cos(2*np.pi*freq*times + phase)
  return sig*modulating_signal


def quantize_signal(sig, u_limit, l_limit, resolution):
  """ Takes a signal and quantizes it to a regularly spaced quantization set

  Args:
    sig: A 1D numpy array of the signal to quantize.
    u_limit: The maximum quantized signal value.
    l_limit: The minimum quantized signal value.
    resolution: The resolution of the quantization set expressed as the number
        of quantization points.
  Returns:
    A 1D numpy array holding the quantized signal
  """
  quantization_set = np.linspace(l_limit, u_limit, resolution)
  
  # Helper func for finding closest quantized value to a signal value.
  def find_nearest(array, value):
      idx = (np.abs(array - value)).argmin()
      return array[idx]
 
  ret_signal = np.zeros(sig.shape)
  for i in range(len(ret_signal)):
    ret_signal[i] = find_nearest(quantization_set, sig[i])

  return ret_signal


def upconvert_and_filter(sig, upconversion_factor, filt=None):
  """ Upconverts a signal and applies a filter to it.

  This function can be used to mock digital to analog conversion by accepting a
  valid 'digital' signal, with say the sampling rate of a realistic signal
  generator, and upconverting it to an artificially high resolution after which
  a filter can be applied that approximately reproduces the actual analog
  we might expect a signal generator such as an AWG to produce.

  Also maybe it'll be useful for other things, idk.

  Args:
    sig: A 1D numpy array holding the digital signal to be upoconverted
    upconversion factor: How many times each input signal value will be
        sequentially repeated in the upconverted signal before filtering. An
        integer.
    filt: The filter to apply to the upconverted signal. If filt is None, no
        filter will be applied.
  Returns:
    A 1D numpy array holding the upconverted and filtered signal.
  """
  ret_signal = np.copy(sig)
  ret_signal = np.repeat(ret_signal, upconversion_factor)
  ret_signal = ret_signal[upconversion_factor//2:len(ret_signal) - upconversion_factor//2]
  if filt is not None:
    padlen = 3*len(filt)
    uc = upconversion_factor
    zero_padding_len = int((padlen - len(ret_signal)))
    if zero_padding_len > 0:
      holder = np.zeros(2*zero_padding_len + len(ret_signal))
      holder[zero_padding_len:zero_padding_len + len(ret_signal)] = ret_signal
      filtered_signal = signal.filtfilt(filt, 1.0, holder)
      ret_signal = filtered_signal[zero_padding_len : \
                                   zero_padding_len + len(ret_signal)]
    else:
      ret_signal = signal.filtfilt(filt, 1.0, ret_signal)

  return ret_signal


def increase_resolution(times, upconversion_factor):
  """ Converts a more granular regular time mesh into a finer mesh.

  Args:
    times: A 1D np array of the original time mesh.
    upconversion_factor: The factor by which to increase the resolution.
  Returns
    A 1D array of a finer time mesh
  """
  start_time = times[0]
  end_time = times[-1]
  num_points = len(times)
  return np.linspace(start_time, end_time, num_points*upconversion_factor)


def add_gaussian_noise(signal, A, mu, sigma):
  """ Adds randomly sampled Gaussian white noise to a signal.

  Args:
    signal: The signal to add noise to.
    A: A free parameter for correcting for units.
    mu: The mean of the Gaussian noise (typically 0).
    sigma: The standard deviation of the Gaussian noise.
  Returns:
    A 1D numpy array of the noisy signal"""
  noise = A*np.random.normal(mu, sigma, signal.shape)
  return signal + noise
  

def create_custom_signal(envelope_function,
                         sample_rate,
                         signal_time,
                         envelope_args=None,
                         modulation_args=None,
                         quantization_args=None,
                         upsampling_args=None,
                         noise_args=None):
  """Creates a custom signal with optional modifications.

  Args:
    envelope_function: the function to generate the desired signal. Must be a
      function of time parameter 't' in the first argument and an optional
      'args' dict in the second parameter.
    sample_rate: the sample rate of the unmodified signal desired
    signal_time: the whole length of the signal in time
    envelope_args: the optional arguemnts to envelope function
    quantization_args: optional parameters if quantization is desired
    upsampling_args: optional parameters if upsampling and filtering is desired
    noise_args: optional parameters if noise is desired
  Returns:
    A 1D np array of the signal described by the arguments"""
  num_raw_samples = int(signal_time * sample_rate)
  raw_times, dt = np.linspace(0, signal_time, num_raw_samples, retstep=True)
  signal = np.array([envelope_function(t, envelope_args) for t in raw_times])
  signals = {
    'r': np.copy(signal)
  }
  times = {
    'r': np.copy(raw_times)
  }

  if modulation_args is not None:
    mod_freq = modulation_args['freq']
    mod_phase = modulation_args['phase']
    signal = modulate_signal(signal, dt, mod_freq, mod_phase)
    signals['m'] = np.copy(signal)

  if quantization_args is not None:
    lower_bound = quantization_args['lower_bound']
    upper_bound = quantization_args['upper_bound']
    resolution = quantization_args['resolution']
    signal = quantize_signal(signal, upper_bound, lower_bound, resolution)
    signals['q'] = np.copy(signal)

  if upsampling_args is not None:
    upsampling_factor = upsampling_args['upsampling_factor']
    filter_args = upsampling_args['filter_args']
    num_upsampled_samples = int((num_raw_samples-1)*upsampling_factor)
    nyquist_rate = sample_rate/2
    fake_nyquist_rate = int(nyquist_rate*upsampling_factor)
    cutoff_freq = filter_args['cutoff_freq'] / fake_nyquist_rate
    roll_off_width = filter_args['roll_off_width'] / fake_nyquist_rate
    ripple_db = filter_args['ripple_db']
    N, beta = scipy.signal.kaiserord(ripple_db, roll_off_width)
    taps = scipy.signal.firwin(N, cutoff_freq, window=('kaiser', beta))
    signal = upconvert_and_filter(signal, upsampling_factor, taps)
    signals['f'] = np.copy(signal)
    fake_times = np.linspace(0, signal_time, num_upsampled_samples)
    times['u'] = fake_times

  if noise_args is not None:
    if noise_args['type'] is 'Gaussian':
      A = noise_args['A']
      mu = noise_args['mu'] 
      sigma = noise_args['sigma']
      signal = add_gaussian_noise(signal, A, mu, sigma)
      signals['n'] = np.copy(signal)
  return signals, times
