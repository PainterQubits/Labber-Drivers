# Painter Zurich Instruments HDAWG

This driver is a modified version of the standard Zurich HDAWG Labber driver. Only compatible with LabOne software versions > 20.00. Last tested with LabOne version 20.07 (future LabOne versions may not be compatible with this driver). Numerous bugs were fixed, driver structure was simplified, and limited marker functionality has been added (waveforms can be uploaded to a single marker channel on the HDAWG of the user's choosing). 

Descripion of standard Labber Zurich AWG driver:
"This driver encapsulates most features of the Zurich Instruments 8-channel HDAWG. However, communication is done through ziPython and the LabOne server, which you will have to obtain both from Zurich Instruments. While the LabOne server needs to be running during measurement, the ziPython libs need to be copied to the driver path. Just install ziPython (you do not need an actual local Python installation) and copy the zhinst folder from *C:\PythonX\Lib\site-packages\* to the driver folder (next to *Zurich_Instruments_HDAWG.py*)."

