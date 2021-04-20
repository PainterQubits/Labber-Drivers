#!/usr/bin/env python

import http.client # pip install http
import InstrumentDriver
from InstrumentConfig import InstrumentQuantity

__version__ = "0.0.1"

class Error(Exception):
    pass

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements the MiniCircuits USB Switch Matrix driver"""


    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
       
        self.establish_connection()        
        self.setModel(self.model_number)

        self.log(self.model_number, level = 30)
        
        self.switch_id_lsb_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3,
                              'E': 4, 'F': 5, 'G': 6, 'H': 7}
        #except Exception as e:
            #msg = str(e)
            #raise InstrumentDriver.CommunicationError(msg)
    
    def establish_connection(self):
        try:
            self.hc.request("POST", "/MN?")
            resp = self.hc.getresponse().read()
            model_number = resp.decode('ascii')[3:]
        except:
            ip_address = self.getAddress()
            port = 80
            self.hc = http.client.HTTPConnection(ip_address, port=80, timeout=2)
            self.hc.request("POST", "/MN?")
            resp = self.hc.getresponse().read()
            self.model_number = resp.decode('ascii')[3:]
    
    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        self.hc.close()

    def performSetValue(self, quant, value, sweepRate = 0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        
        self.establish_connection()
        switch_type, _, switch_id = quant.name.split(" ")
        
        if switch_type in ["SPDT", "Transfer"]:
            self.hc.request("POST", "/SET{}={}".format(switch_id, int(value)))
            resp = self.hc.getresponse().read()
            return_val = int(resp.decode('ascii'))
        elif switch_type == 'SP4T':
            self.hc.request("POST", "/SP4T{}:STATE:{}".format(switch_id, int(value)))
            resp = self.hc.getresponse().read()
            return_val = int(resp.decode('ascii'))
        elif switch_type == 'SP6T':
            self.hc.request("POST", "/SP6T{}:STATE:{}".format(switch_id, int(value)))
            resp = self.hc.getresponse().read()
            return_val = int(resp.decode('ascii'))
            
        else:
             pass
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        self.establish_connection()
        switch_type, _, switch_id = quant.name.split(" ")
        
        if switch_type in ["SPDT", "Transfer"]:
            self.hc.request("POST", "/SWPORT?")
            resp = self.hc.getresponse().read()
            decimal = int(resp.decode('ascii'))
            bin_str = '{0:b}'.format(decimal).rjust(8, '0')
            self.log(bin_str, level=30)            
            value = int(bin_str[-(self.switch_id_lsb_map[switch_id] + 1)])
            
        elif switch_type == 'SP4T':
            self.hc.request("POST", "/SP4T{}:STATE?".format(switch_id))
            resp = self.hc.getresponse().read()
            value = int(resp.decode('ascii'))
        elif switch_type == 'SP6T':
            self.hc.request("POST", "/SP6T{}:STATE?".format(switch_id))
            resp = self.hc.getresponse().read()
            value = int(resp.decode('ascii'))

        else:
            value = quant.getValue()
        return value


if __name__ == '__main__':
    pass
