# -*- coding: utf-8 -*-
"""TuningCurveFitting.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1IzpvN_HUJRpddWcFwEpxOWO4Ura-9-gy
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
rcParams['font.size'] = 14
from scipy.optimize import curve_fit

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import csv

number_of_qubits = 6
frequency_points = 41

frequencies = np.zeros((number_of_qubits, frequency_points))

#qubit 1 data
frequencies[0] = np.array([4.8733, 4.8194, 4.790, 4.789, 4.811, 4.8529, 4.9166, 5.0006, 5.092, \
5.1952, 5.2958, 5.3957, 5.4927, 5.5821, 5.6628, 5.7363, 5.7989, 5.8477, 5.8904, \
5.9118, 5.9229, 5.9225, 5.9067, 5.8799, 5.8393, 5.7798, 5.7178, 5.647, 5.5577, 5.466,\
5.367, 5.262, 5.153, 5.066, 4.977, 4.899, 4.838, 4.805, 4.789, 4.798, 4.832])

#qubit 2 data
frequencies[1] = np.array([5.329, 5.272, 5.241, 5.243, 5.272, 5.327, 5.406, 5.503, 5.604, 5.727,\
    5.844, 5.957, 6.064, 6.162, 6.250, 6.324, 6.384, 6.427, 6.456, 6.468, 6.472, 6.461, \
        6.441, 6.401, 6.348, 6.279, 6.196, 6.100, 5.997, 5.885, 5.770, 5.658, 5.541, 5.441, \
            5.355, 5.291, 5.252, 5.240, 5.255, 5.305, 5.374])

#qubit 3 data
frequencies[2] =  np.array([5.365, 5.312, 5.279, 5.279, 5.310, 5.365, 5.448, 5.542, 5.704, 5.795, \
    5.911, 6.026, 6.133, 6.235, 6.322, 6.398, 6.461, 6.508, 6.535, 6.551, 6.551, 6.530, 6.496,\
        6.446, 6.381, 6.301, 6.208, 6.105, 5.993, 5.88, 5.763, 5.653, 5.580, 5.420, 5.348, 5.298, \
            5.274, 5.281, 5.317, 5.377, 5.453])

#qubit 5 data
frequencies[3] = np.array([5.385, 5.310, 5.257, 5.241, 5.261, 5.310, 5.391, 5.554, 5.64, 5.763, 5.889, \
    6.014, 6.129, 6.238, 6.329, 6.404, 6.462, 6.502, 6.526, 6.514, 6.477, 6.423, 6.350, \
        6.261, 6.160, 6.046, 5.923, 5.798, 5.681, 5.582, 5.521, 5.419, 5.334, 5.271, 5.243, 5.252, \
            5.298, 5.369, 5.464, 5.569, 5.631])

#qubit 6 data
frequencies[4] = np.array([5.569, 5.481, 5.426, 5.407, 5.433, 5.494, 5.586, 5.706, 5.836, 5.964, 6.142, \
    6.256, 6.366, 6.468, 6.548, 6.605, 6.658, 6.674, 6.672, 6.651, 6.576, 6.532, 6.445, 6.341, \
        6.227, 6.119, 5.934, 5.802, 5.679, 5.563, 5.480, 5.423, 5.408, 5.433, 5.497, 5.590, \
            5.709, 5.837, 5.962, 6.033, 6.256])

#qubit 7 data
frequencies [5] = np.array([5.406, 5.279, 5.16, 5.054, 4.963, 4.899, 4.869, 4.869, 4.906, 4.977, 5.07, 5.18,
          5.302, 5.422, 5.546, 5.654, 5.755, 5.841, 5.926, 5.967, 6, 6.017, 6.02, 6.001,
          5.964, 5.903, 5.833, 5.744, 5.642, 5.53, 5.405, 5.284, 5.162, 5.055, 4.967, 4.901,
          4.866, 4.866, 4.906, 4.974, 5.067])


fmax = np.zeros(number_of_qubits)
fmin = np.zeros(number_of_qubits)
V_0 = np.zeros(number_of_qubits)
V_off = np.zeros(number_of_qubits)

err_V0 = np.zeros(number_of_qubits)
err_Voff = np.zeros(number_of_qubits)
err_fmax = np.zeros(number_of_qubits)
err_fmin = np.zeros(number_of_qubits)

#create CSV file
headers = ['Qubit', 'fmax (GHz)', 'fmin (GHz)', 'V_0 (V)']
filename = "Tuning_Curves.csv"
with open('Tuning_Curves.csv','w') as csvfile:
    writer=csv.writer(csvfile)
    # writing the header
    writer.writerow(headers)



    for i in range(number_of_qubits):
        Vx = np.linspace(-7, 7, frequency_points)

        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=Vx, y=frequencies[i], mode='lines+markers', name='fq'))
        fig1.update_layout(title="Tuning Curve Q" + str(i+1), xaxis_title="Tuning voltage (V)", yaxis_title="Qubit freq (GHz)")
        fig1.show()
        TuningFit = lambda Vx, V0, Voff, Em, d: np.sqrt(np.abs(Em * np.cos(np.pi * (Vx - Voff) / V0)
                                            * np.sqrt(1 + d**2 * np.tan(np.pi * (Vx - Voff) / V0)**2)))

        # initial parameters for fitting. CHANGES NEEDED!
        p00 = [10.56, 0.5, 36, 0.67]  
        popt, pcov = curve_fit(TuningFit, Vx, frequencies[i], p0 = p00)

        Vfit = np.linspace(-7, 7, 1000)
        fqfit = TuningFit(Vfit, *popt)

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=Vx, y=frequencies[i], mode='markers', name='Meas.'))
        fig2.add_trace(go.Scatter(x=Vfit, y=fqfit, mode='lines', name='Fit'))
        fig2.update_layout(title="Tuning Curve Q" + str(i+1), xaxis_title="Tuning voltage (V)", yaxis_title="Qubit freq (GHz)")
        fig2.show()

        fmax[i] = np.sqrt(np.abs(popt[2]))
        V_off[i] = popt[1]
        V_0[i] = popt[0]
        fmin[i] = np.sqrt(np.abs(popt[3] * popt[2]))

        err_V0[i] = np.sqrt(pcov[0][0])
        err_Voff[i] = np.sqrt(pcov[1][1])
        err_fmax[i] = np.sqrt(pcov[2][2]) / 2
        err_fmin[i] = np.sqrt(pcov[2][2] + pcov[3][3]) / 2

        content = [i, fmax[i], fmin[i], V_0[i]]
        print(content)
        writer.writerow(content)
