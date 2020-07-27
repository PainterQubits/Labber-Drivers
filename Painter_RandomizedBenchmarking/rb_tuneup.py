import os
from scipy.optimize import minimize
import numpy as np

from Labber import ScriptTools


# Precalculated representative ground and excited iq points for classification
ZERO_POINT = 1*np.exp(1j*np.pi/2) # lol, zero point
ONE_POINT = 1*np.exp(-1j*np.pi/2)


def optimize(config, minimize_function):
    """Optimize using Scipy's built-in Nelder-mead optimizer

    Parameters
    ----------
    config : dict
        Optimizer settings provided from the measurement configuration

    minimize_function : callable
        Function to be minimized,
            evaluation_function(x) -> float
        The function will run Labber measurement for parameter values x.
        The function is typically passed to the scipy optimizer.

    Returns
    -------
    optimizer_result : dict
        Results from optimizer, using scipy's OptimizeResult format.
        Necessary keys are "x", containing the final optimizer parameters.

    """
    # extract parameters
    x0 = np.array([d['Start value'] for d in config['optimizer_channels']])

    # nelder-mead in scipy does not support bounds, not handled here
    # bounds = [(d['Min value'], d['Max value'])
    #           for d in config['optimizer_channels']]

    x_tolerance = [d['Precision'] for d in config['optimizer_channels']]
    # nelder-mead in scipy only supports single value for x tolerance, but
    # parameters are re-scaled by Labber if necessary, so all values are equal
    xatol = min(x_tolerance)

    # define initial simplex from step size parameters
    step_size = [d['Initial step size'] for d in config['optimizer_channels']]
    initial_simplex = np.zeros((len(x0) + 1, len(x0)))
    # first point is start value
    initial_simplex[0] = x0
    # other points are defined by initial step size
    for n, channel in enumerate(config['optimizer_channels']):
        initial_simplex[n + 1] = x0
        # go in direction furthest from bound
        if (x0[n] - channel['Min value']) <= (channel['Max value'] - x0[n]):
            # closer to min value, go positive
            initial_simplex[n + 1, n] += step_size[n]
        else:
            # closer to max value, go negative
            initial_simplex[n + 1, n] -= step_size[n]

    # creat options for minimizer
    options = dict(
        maxiter=config['Max evaluations'],
        maxfev=config['Max evaluations'],
        fatol=config['Relative tolerance'],
        xatol=xatol,
        initial_simplex=initial_simplex,
    )

    # optimize
    res = minimize(
        minimize_function, x0,
        method='Nelder-Mead',
        options=options,
    )

    return res


# THIS FUNCTION IS LIABLE TO CHANGE DEPENDING ON HOW WE DECIDE TO DO OUR
# SINGLE SHOT QUBIT MEASUREMENT. CURRENTLY IT ASSUMES WE HAVE TWO POINTS IN THE
# IQ PLANE REPRESENTING 'IDEAL 1' and 'IDEAL 0' AND CLASSIFIES BASED ON THE 
# MINIMUM DISTANCE BETWEEN A CANDIDATE POINT AND THESE TWO POINTS.
def discriminate_qubit_state(iq_point):
    d0 = np.abs(iq_point - ZERO_POINT) # lol, zero point
    d1 = np.abs(iq_point - ONE_POINT)
    if d1 < d0:
        return 1
    else
        return 0


def tuneup_cost_function(x, measurement_config):
    flip_fraction = 0

    # Update measurement with new simplex vertex values for DRAG parameters
    alpha = x[0]
    beta = x[1]
    delta = x[2]
    measurement_config.updateValue('Randomized Benchmarking - Primary Envelope Weight', alpha)
    measurement_config.updateValue('Randomized Benchmarking - Derivative Envelope Weight', beta)
    measurement_config.updateValue('Randomized Benchmarking - Constant Detuning Bias', delta)

    # Loop over K new random seeds, generating K new random sequences
    (_ iq_points) = measurement_config.performMeasurement()
    num_flipped = 0
    for iq_point in iq_points:
        num_flipped += discriminate_qubit_state(iq_point)
    flip_fraction = num_flipped / len(iq_points)
    return flip_fraction
        

def extract_nelder_mead_rb_tuneup_config(config_path):
    # define configuration
    scenario = Scenario(config_path).get_config_as_dict()

    optimizer_channels = []
    for step in scenario['step_items']:
        if step['optimizer_config']['enabled'] == True:
            optimizer_channels.append(step['optimizer_config'])

    optimizer_config = scenario['optimizer']
    optimizer_config['optimizer_channels'] = optimizer_channels
    return optimizer_config


if __name__ == "__main__":
    sPath = os.path.dirname(os.path.abspath(__file__))
    config_json = 'RandomizedBenchmarking.json'
    config_out = 'RandomizedBenchmarkingOut.hdf5'

    # Read in the optimization configuration as defined in the exported config
    config = extract_nelder_mead_rb_tuneup_config(
                 os.path.join(sPath, config_json))

    # Read in the measurement configuration as it will be run to execute tuneup
    measurement_config = ScriptTools.MeasurementObject(
                             os.path.join(sPath, config_json),
                             os.path.join(sPath, config_out))
    
    cost_function = lambda x: tuneup_cost_function(x, measurement_config)

    optimum = optimize(config, cost_function)
    print(optimum)
