# Painter Downsampler
The Labber Driver Painter Downsampler is signal generator/analyzer built to work with arbitrary waveform generators (AWSs) of different sample rates when generating multi-qubit pulses. The down-sampling works by linear interpolation of the data with higher sample rate using `scipy.interpolate.interp1d` function.

Written by Eunjong Kim, July 19, 2019.
