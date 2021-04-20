#!/usr/bin/env python

import clr # pythonnet
clr.AddReference('mcl_SolidStateSwitch_NET45')      # Reference the DLL

from mcl_SolidStateSwitch_NET45 import USB_Digital_Switch
import InstrumentDriver
from InstrumentConfig import InstrumentQuantity

__version__ = "0.0.1"

class Error(Exception):
    pass

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements the MiniCircuits USB Solid State Switch"""


    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        self.switch = USB_Digital_Switch()   # Create an instance of the switch class
        self.serial_number = str(self.getAddress())

        status = self.establish_connection()  # Connect the switch (pass the serial number as an argument if required)
        if status > 0:
            resp = self.switch.Send_SCPI(":MN?", "") # Read model name
        self.model_number = str(resp[2])
        self.setModel(self.model_number)
        self.log(self.model_number, level = 30)

    def establish_connection(self):
        status = self.switch.GetUSBConnectionStatus()
        if status > 0:
            pass
        else:
            status = int(self.switch.Connect(self.serial_number)[0])  # Connect the switch (pass the serial number as an argument if required)
        return status
    
    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        self.switch.Disconnect()

    def performSetValue(self, quant, value, sweepRate = 0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        
        self.establish_connection()
        name = quant.name.split(" ")
        if len(name) == 2:
            switch_type = name[0]
        elif len(name) == 3:
            switch_type = name[0]
            switch_channel = name[2]
        
        if switch_type in ["SP8T", "SP16T"]:
            resp = self.switch.Send_SCPI(":{}:STATE:{}".format(switch_type,
                                                               int(value)),
                                         "")
            self.log(resp)
        elif switch_type in ["SP2T", "SP4T"]:
            resp = self.switch.Send_SCPI(":{}:{}:STATE:{}".format(switch_type,
                                                                  switch_channel,
                                                                  int(value)),
                                         "")
            self.log(resp)
        else:
             pass
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        self.establish_connection()
        name = quant.name.split(" ")
        if len(name) == 2:
            switch_type = name[0]
        elif len(name) == 3:
            switch_type = name[0]
            switch_channel = name[2]

        if switch_type in ["SP8T", "SP16T"]:
            resp = self.switch.Send_SCPI(":{}:STATE?".format(switch_type), "")
            self.log(resp)
            value = int(resp[2])
        elif switch_type in ["SP2T", "SP4T"]:
            resp = self.switch.Send_SCPI(":{}:{}:STATE?".format(switch_type,
                                                                switch_channel),
                                         "")
            self.log(resp)
            value = int(resp[2])
        else:
            value = quant.getValue()
        return value


if __name__ == '__main__':
    pass
