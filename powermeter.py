# -*- coding: utf-8 -*-
"""
Created on Mon Aug 25 19:12:31 2014

@author: nick
"""

import serial
import serial.tools.list_ports


class pmcommunication(object):
# Module for communicating with the power meter    
    baudrate = 115200
    
    def __init__(self, port):
        self.serial = self._open_port(port)
        self._serial_write(b'a')# flush io buffer
        print(str(self._serial_read())+ "Buffer cleared (Ignore unknown command message)") #will read unknown command
        #self.set_range(4) #Sets bias resistor to 1k
        
    def _open_port(self, port):
        ser = serial.Serial(port, timeout=2)
        #ser.readline()
        #ser.timeout = 1 #causes problem with nexus 7
        return ser
        
    def close_port(self):
        self.serial.close()
        
    
    def _serial_write(self, string):
        self.serial.write('{}\n'.format(string).encode())
    
    def _serial_read(self):
        msg_string = self.serial.readline()
        # Remove any linefeeds etc
        msg_string = msg_string.rstrip()
        return msg_string
    
    def reset(self):
        self._serial_write('*RST')
        return self._serial_read()
        
    def get_voltage(self):
        self._serial_write('VOLT?')
        voltage = self._serial_read()
       # print (voltage)
        return voltage
        
    def get_range(self):
        self._serial_write('RANGE?')
        pm_range = self._serial_read()
        #print pm_range
        return pm_range
    
    
    def set_range(self,value):
        self._serial_write('RANGE'+ str(value))
        self.pm_range = value -1
        return self.pm_range
    
    def serial_number(self):
        self._serial_write('*IDN?')
        return self._serial_read()

if __name__ == '__main__':
    import time
    powermeter = pmcommunication("COM5")
    powermeter.set_range(3)
    
    start = time.time()
    i=0
    while i <10000:
        print(powermeter.get_voltage())
        i += 1
    end = time.time()

    print("Waktu", end - start)
    
    
       
      
    
    
    