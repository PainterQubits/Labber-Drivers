#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar  9 18:32:31 2021

@author: eunjongkim
"""
import InstrumentDriver
import nidaqmx
from nidaqmx.constants import LineGrouping

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements NI 9403 digital module"""
    
    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        self.module = self.getAddress()

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        pass

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        
        # line index
        idx = int(quant.name.split(" ")[1])
        item = quant.name.split(" ")[-1]
        
        if item == 'State' and self.getValue("Line %d - Direction" % idx) == "Output":
            with nidaqmx.Task() as task:
                task.do_channels.add_do_chan(self.module + "/port0/line%d" % idx)
                task.write(value, auto_start=True)
                self.log("Set Line %d State: %d" % (idx, int(value)), level=30)
        else:
            return value

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # line index
        idx = int(quant.name.split(" ")[1])
        item = quant.name.split(" ")[-1]

        if item == 'State':
            with nidaqmx.Task() as task:
                if self.getValue("Line %d - Direction" % idx) == "Input":
                    task.di_channels.add_di_chan(self.module + "/port0/line%d" % idx)
                if self.getValue("Line %d - Direction" % idx) == "Output":
                    task.do_channels.add_do_chan(self.module + "/port0/line%d" % idx)
               
                value = task.read()
                self.log("Get Line %d State: %d" % (idx, int(value)), level=30)  
            return value
        else:
            return quant.getValue()
        
