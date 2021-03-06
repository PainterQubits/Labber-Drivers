#!/usr/bin/env python

from VISA_Driver import VISA_Driver

__version__ = "0.0.1"

class Driver(VISA_Driver):
    """ The Painter Siglent DC PowerSupply driver re-implements the VISA driver with some more options"""

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        name = str(quant.name)
        if name == 'Firmware Version':
            # read-only channels don't perform setValue
            pass
        elif name.endswith(('Active Voltage', 'Active Current')):
            return self.getValue(name)
        else:
            # else, call the generic VISA driver
            return VISA_Driver.performSetValue(self, quant, value, sweepRate,
                                               options=options)

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # perform special getValue for delay commands
        name = str(quant.name)
        if name.endswith(('Output', )):
            lName =  name.split(' - ')
            return self.getValue(name)  # return the local value stored in the driver
        else:
            # run the generic visa driver case
            return VISA_Driver.performGetValue(self, quant, options=options)


if __name__ == '__main__':
    pass
