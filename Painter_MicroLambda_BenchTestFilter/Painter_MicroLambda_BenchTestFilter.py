# Written by Eunjong Kim, 3/10/2021

import InstrumentDriver
import socket

class Driver(InstrumentDriver.InstrumentWorker):
    ''' This class implements the MicroLambda Test Bench Filter'''

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        self.log("Open intrument")

        self.establish_connection()
        self.setModel(self.model_number)
        self.log("Socket connection to IP address:", self.ip_address,
                 ", Port:", self.port)
    
    def establish_connection(self):
        try:
            self.send_receive_decode(b"R0000")
        except:
            self.ip_address = self.getAddress()
            self.port = 30303
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.model_number = self.send_receive_decode(b"R0000")
            self.log("Connection Established, model number: " + self.model_number)
            
    def performClose(self, bError=False, options={}):
        '''Perform the close instrument connection operation'''
        self.socket.close()

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        '''Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument'''
        self.establish_connection()
        if quant.name == "Frequency":
            self.socket.sendto(b"F%09.3f" % (value / 1e6),
                               (self.ip_address, self.port))
        else:
            pass

        return value
    
    def send_receive_decode(self, sCmd):
        self.socket.sendto(sCmd, (self.ip_address, self.port))
        r = self.socket.recv(1024)
        return r.decode('ascii').strip().strip('\x00')
        
    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        self.establish_connection()
        ip_port = (self.ip_address, self.port)

        if quant.name == "Frequency":
            r = self.send_receive_decode(b"R0016")
            value = float(r) * 1e6

        elif quant.name == "Model Number":
            value = self.model_number

        elif quant.name == "Serial Number":
            value = self.send_receive_decode(b"R0001")
        
        elif quant.name == "Filter BW":
            r = self.send_receive_decode(b"R0005")
            value = float(r) * 1e6

        elif quant.name == "Filter BW Level":
            r = self.send_receive_decode(b"R0023")
            value = float(r)
    
        elif quant.name == "Filter Insertion Loss":
            r = self.send_receive_decode(b"R0006")
            value = float(r)

        elif quant.name == "Filter Limiting Level":
            r = self.send_receive_decode(b"R0007")
            value = float(r)

        elif quant.name == "Internal Temperature":
            r = self.send_receive_decode(b"T")
            value = float(r[:-1])

        elif quant.name == "+3.0VDC Supply":
            r = self.send_receive_decode(b"V1")
            value = float(r[:-1])

        elif quant.name == "+3.3VDC Supply":
            r = self.send_receive_decode(b"V2")
            value = float(r[:-1])

        elif quant.name == "+5.0VDC Supply":
            r = self.send_receive_decode(b"V3")
            value = float(r[:-1])

        elif quant.name == "+15.0VDC Supply":
            r = self.send_receive_decode(b"V4")
            value = float(r[:-1])

        elif quant.name == "-15.0VDC Supply":
            r = self.send_receive_decode(b"V5")
            value = float(r[:-1])

        elif quant.name == "Minimum Frequency":
            r = self.send_receive_decode(b"R0003")
            value = float(r) * 1e6

        elif quant.name == "Maximum Frequency":
            r = self.send_receive_decode(b"R0004")
            value = float(r) * 1e6

        elif quant.name == "Unit Health Status":
            value = self.send_receive_decode(b"R0013")

        else:
            value = quant.getValue()
        return value


if __name__ == '__main__':
    pass
