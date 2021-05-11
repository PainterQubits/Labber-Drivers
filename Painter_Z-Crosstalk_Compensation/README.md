# Painter Z-Crosstalk Compensation #
## Overview ##
The object of the project is to take in flux bias characterization data and output adjusted voltages after crosstalk compensation.
 
The project is developed based on the existing Labber driver packages. It contains a configuration file (*.ini) and a python (*.py) file. The .ini file 
determines the Labber GUI configuration, including input and output channels. The python file performs the input processing and the crosstalk compensation function. 

The package also contains a python jupyter notebook file (tuningcurvefitting.ipynb) that takes in frequency vs voltage data extracted from the measurement and generate 
a tuning curve csv file that can be used as the input file in the driver.

## How To ##
In order to use the Labber driver, users can follow the following procedures. 

1. Add the **Painter Z-Crosstalk Compensation** driver on **InstrumentServer**
page, click **Start Instrument**
2. In the **Setting** page, choose the number of flux biases to be adjusted
in the **Number of Z-Control Lines** dropdown menu (2-7 qubits)
3. Import a crosstalk matrix csv file that contains the N x N crosstalk
matrix in the **Crosstalk Matrix** section, click **Load Crosstalk Matrix**
to load the matrix, exception will be raised if the file contains
a different number of qubits than the number of flux biases in the
**Number of Z-Control Lines** menu
4. Values in the **Mij** in the **Crosstalk Matrix** section will be updated
5. Import a tuning curve csv file that contains the N qubits' tuning curve
values (fmax, fmin, V0) in the **Tuning Curves** section, click **Load
Tuning Curves** to load the matrix, exception will be raised if the file
contains a different number of qubits than the number of flux biases
in the **Number of Z-Control Lines** menu
6. Values in **f max qi**, **f min qi**, and **V0 qi** will be updated based on
the tuning curve file's values
7. Steps 7 - 9 and Steps 15 - 16 can be ignored if Steps 3 - 6 are followed.
If no crosstalk matrix file or tuning curve file is available, manually
input **f max qi** as the maximum frequency for qubit i
8. Input **f min qi** as the minimum frequency for qubit i
9. Input **V0 qi** as the default voltage that corresponds to the full tuning
curve
10. Input **V bias qi** as the voltage applied to qubit i with other flux biases
set to 0
11. Input **f bias qi** as the frequency for qubit i when **V bias** is applied
with other flux biases set to 0, **V bias** and **f bias** are used to
determine the tuning curve phase offset
12. Input **f target qi** as the target frequency for qubit i
13. Choose either **Positive** or **Negative** in the **Slope** dropdown menu,
this is to specify which side of the tuning curve we want to operate on
14. Click **Confirm** to obtain the updated **V target qi** values (calculated
from the tuning curve and later used in the crosstalk compensation)
15. Attain the crosstalk characterization data: measure the qubit frequency
change in the presence of another flux bias line (refer to the
Crosstalk Characterization Procedures below for details) to get dV1
dV2 as a
crosstalk matrix element for qubit 1 under the influence of flux bias 2
16. Enter the crosstalk matrix element **Mij** as the crosstalk effect for
qubit i under flux bias j's influence
17. In the **Output** page, click **Do Conversion**, the values in the **Crosstalk
Matrix (inverse)** and **Adjusted Voltage** will be updated. The **Adjusted
Voltage** values are the flux bias voltages we would want to
apply to the qubits

## Crosstalk Characterization Procedures
We can measure the qubit's frequency shift as a function of the flux bias as follows
1. Park qubit A at a frequency where the frequency has a roughly linear relationship to the flux bias when the change in flux bias is small, in this case, we can bias the qubit at $\Phi_A = \Phi_0/4$
2. Measure $f_A$ using the Ramsey method at three values of $\Phi_A$ about $\Phi_0/4$, and three values of $\Phi_B$  in increments of $\pm\Phi_0$ to obtain slopes of $df_A/d\Phi_B$  and $df_A/d\Phi_A$
3. Repeat the above procedures for all pairs of flux bias and qubit to obtain the full N x N crosstalk matrix 

* In practice, we use $\frac{dV_A}{dV_B}$ as the crosstalk matrix element


## tuningcurvefitting.py or tuningcurvefitting.ipynb
1. From the measurement .hdf5 files, we can extract the frequencies of
qubits manually
2. In the **tuningcurvefitting.py** file, define the number_of_qubits, define
**frequencies** as the number of frequency points in the measurement
file
3. Log the frequencies in frequencies[i] for the i-th qubit
4. Run the python program, a **Tuning_Curves.csv** will be generated
with **fmax**, **fmin**, **V_0**
5. Load the .csv file in the **Painter Z-Crosstalk Compensation** driver


## filewrite.py
This file writes to the configuration .ini file. If the desired qubit number is larger than the existing one, the user should run filewrite.py and the .ini file will be automatically updated. If the desired qubit number is smaller than the existing one, the user should delete the old .ini file and run the filewrite.py to get an updated version.
