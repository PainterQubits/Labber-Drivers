Signal generator driver for generating completely arbitrary pulse sequences, without any a-priori hard encoding of pulse shape, pulse order, or number of pulses, for driving a single qubit. Best-suited for experiments with small numbers of qubits, where synchronization of pulses between many qubits is not a concern. Driver can generate parametrized pulses, or can receive completely arbitrary pulses generated in Python via the Python Labber API (through use of the “Custom” pulse type, example script included). 

Given that all possible driver settings need to be hard-coded in Labber, right now the default driver files allow for nine pulses and readout of two qubits. However, a script for generating driver files that allow for different number of pulses and different number of qubit readouts can be found under the “ini_generating_files” folder.

Image of driver:
![image](https://user-images.githubusercontent.com/16061148/99593514-a1281280-29a6-11eb-847e-60829dba97b4.png)
