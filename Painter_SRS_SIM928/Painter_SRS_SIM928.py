# Written by Eun Jong Kim on 4/13/2019

from VISA_Driver import VISA_Driver
import time

class Driver(VISA_Driver):
    """ This is the Labber driver for controlling Stanford SIM928 Isolated
    Voltage Sources integrated to SIM900 mainframe"""
    slotMap = {'Slot 1': 1, 'Slot 2': 2, 'Slot 3': 3, 'Slot 4': 4,
              'Slot 5': 5, 'Slot 6': 6, 'Slot 7': 7, 'Slot 8': 8}

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        # calling the generic VISA open to make sure we have a connection
        VISA_Driver.performOpen(self, options=options)
        # self.writeAndLog('BRDC "*RST"')
        pass

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        # calling the generic VISA class to close communication
        VISA_Driver.performClose(self, bError, options=options)
        pass

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""

        return VISA_Driver.performSetValue(self, quant, value,
                                           sweepRate, options=options)

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        name = quant.name

        if name.endswith(('Voltage', 'Output')):
            # get channel in use
            lName =  name.split(' ')
            key = '%s %s' % (lName[0], lName[1])
            ch = lName[3]
            slot = self.slotMap[key]

            # \r: CR (Carriage Return), \n: LF (Line Feed)
            CRLF = '\r\n'

            if ch == 'Voltage':
                self.writeAndLog('FLOQ')  # flush output queue of SIM900
                self.writeAndLog("SNDT " + str(slot) + ',"VOLT?"')
                self.wait(0.2)
                sAns = self.askAndLog("GETN? " + str(slot) + ",7")
                self.wait(0.2)
                while len(sAns) < 6:
                    # perform query until retrieving the proper value
                    sAns = self.askAndLog("GETN? " + str(slot) + ",7")
                    self.wait(0.2)

                return sAns[5:]

            if ch == 'Output':
                self.writeAndLog('FLOQ')  # flush output queue of SIM900
                self.writeAndLog("SNDT " + str(slot) + ',"EXON?"')
                self.wait(0.2)
                sAns = self.askAndLog("GETN? " + str(slot) + ",3")
                self.wait(0.2)

                while len(sAns) < 6:
                    # perform query until retrieving the proper value
                    sAns = self.askAndLog("GETN? " + str(slot) + ",3")
                    self.wait(0.2)

                return sAns[5]

        elif name.endswith(('Status',)):
            value = self.getValue(name)
            return value
