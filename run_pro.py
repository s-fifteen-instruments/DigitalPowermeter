#!/usr/bin/env python
"""
Created on Mon Aug 29 2016

Modified from the similar program by Nick
@author: Adrian Utama

Modified from the works from authors above to work in Windows in Python3.

Optical Powermeter (tkinter) Version 1.02 (last modified on Mar 23 2017)
v1.01: There was a bug as worker thread 1 run endlessly when the program just started. Fixed.
v1.02: Corrected calibration (svn-8 onwards)
v1.03: Updated syntax to work with Python3 , updated the serial detection to suit windows and linux users.
"""

import tkinter
import os
import glob
import time
import powermeter as pm
import queue
import threading
import json
import serial.tools.list_ports

# PLOTTING ADD ON --->
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.figure import Figure
import matplotlib.animation as animation
import matplotlib.ticker as mtick
# <---

REFRESH_RATE = 100  #100ms
NUM_OF_AVG = 50
RESISTORS = [1e6,100e3,10e3,1e3,20] #Sense resistors that is used. The 0th element refers to the 1st range. The second resistor should be 100 kOhm (110 kOhm parallel with 1 MOhm)
CALIBRATION_FILE = 's5106_interpolated.cal'    #detector calibration file

def insanity_check(number, min_value, max_value):
    ''' To check whether the value is out of given range'''
    if number > max_value:
        return max_value
    if number < min_value:
        return min_value
    else:
        return number

class GuiPart:
    def __init__(self, master, queue, endCommand):
        self.queue = queue

        # Variable to signify the start of the measurement
        self.started = 0
        self.trigger = 0    # If this is true, the program will flush the previous average values

        self.range = 1

        # Set the object, initial value, and steps for the modifiable parameter (using buttonModifyPressed).
        # Up to now there is only one entry at channel 0, which is the wavelength detection of the laser
        self.entry = [0]
        self.set_value = [780]
        self.rough_step = [30]
        self.fine_step = [1]


        # Set up the GUI
        tkinter.Label(master, text='Select Device', font=("Helvetica", 16)).grid(row=1, padx=5, pady=5, column=1)
        # self.ports = glob.glob('/dev/ttyACM*')  # Get the ports for the device
        portslist = list(serial.tools.list_ports.comports())
        self.devicelist = []
        self.addresslist = []
        for port in portslist:
            self.devicelist.append(port.device + " " + port.description)
            self.addresslist.append(port.device)
        self.set_ports = tkinter.StringVar(master)
        self.ports_option = tkinter.OptionMenu(master, self.set_ports, *self.devicelist)
        self.ports_option.grid(row = 1, padx = 5, pady = 5, column = 2, columnspan = 3)
        self.ports_option.configure(font=("Helvetica", 14), width = 12, justify=tkinter.LEFT)
        tkinter.Button(master, text='  Start  ', font=("Helvetica", 16), command=lambda:self.startDevice()).grid(sticky="w", row=1, column=5, columnspan = 3, padx=5, pady=5)


        tkinter.Label(master, text='Select Range', font=("Helvetica", 16)).grid(row=2, padx=5, pady=5, column=1)
        self.set_range = tkinter.StringVar(master)
        self.set_range.set("1")
        self.range_option = tkinter.OptionMenu(master, self.set_range, "1", "2", "3", "4", "5")
        self.range_option.grid(row = 2, padx = 5, pady = 5, column = 2, columnspan = 3)
        self.range_option.configure(font=("Helvetica", 14), width = 12, justify=tkinter.LEFT)
        self.set_range.trace('w', lambda *args: self.changeRange())

        self.set_autorange = tkinter.IntVar()
        self.chk_set = tkinter.Checkbutton(root, text='Auto', font=("Helvetica", 16), variable=self.set_autorange)
        self.chk_set.grid(row=2, column=5, columnspan = 3, padx=5, pady=5, sticky="w")

        tkinter.Label(master, text='Wavelength', font=("Helvetica", 16)).grid(row=3, padx=5, pady=5, column=1)
        self.entry[0] = tkinter.Entry(master, width=10, font=("Helvetica", 16), justify=tkinter.CENTER)
        self.entry[0].grid(row=3, column=4)
        self.entry[0].insert(0, str(self.set_value[0])+ " nm")
        tkinter.Button(master, text='<<', font=("Helvetica", 12), command=lambda:self.buttonModifyPressed(0, 1)).grid(row=3, column=2)
        tkinter.Button(master, text='<', font=("Helvetica", 12), command=lambda:self.buttonModifyPressed(0, 2)).grid(row=3, column=3)
        tkinter.Button(master, text='>', font=("Helvetica", 12), command=lambda:self.buttonModifyPressed(0, 3)).grid(row=3, column=5)
        tkinter.Button(master, text='>>',font=("Helvetica", 12), command=lambda:self.buttonModifyPressed(0, 4)).grid(row=3, column=6)
        tkinter.Label(master, text='', font=("Helvetica", 16), width = 2).grid(row=3, padx=5, pady=5, column=7)

        self.display_opm = tkinter.StringVar(master)
        self.display_opm.set("OFF")
        self.label_display_opm = tkinter.Label(master, font=("Helvetica", 60), textvariable=self.display_opm, width=10, bg="black", fg="white")
        self.label_display_opm.grid(row=4, columnspan=8, padx=5, pady=5)

        # PLOTTING ADD ON--->
        self.xdata = range(1,101,1)
        self.ydata = [0] * 100

        self.figure = Figure(figsize=(6, 3))
        self.figure_subplot = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=root)
        self.canvas.get_tk_widget().grid(row =5, column = 1, columnspan = 8)

        self.line, = self.figure_subplot.plot(self.xdata, self.ydata)
        self.figure_subplot.grid()

        self.figure_subplot.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.2e'))
        self.figure_subplot.set_xticklabels([])
        self.figure.tight_layout()

        self.anim = animation.FuncAnimation(self.figure, self.animated, interval = 100, blit=False)
        # <---

        tkinter.Button(master, text='Shutdown', font=("Helvetica", 16), command=endCommand).grid(row=10, column=1, padx=5, pady=5)

    def animated(self, i):
        self.line.set_ydata(self.ydata)
        self.figure_subplot.set_xlim([1, 100])
        self.figure_subplot.set_ylim([min(self.ydata)*0.9, max(self.ydata)*1.1+1e-9])
        return self.line,

    def startDevice(self):
        self.started = 1
        for idx, device in enumerate(self.devicelist):
            if self.set_ports.get() == device:
                deviceAddress = self.addresslist[idx]
        print("SelectedPort " + deviceAddress)
        self.powermeter = pm.pmcommunication(deviceAddress)
        self.changeRange()
        print ("Device", self.set_ports.get(), "ready to go.")

    def changeRange(self):
        if self.started == 1:
            self.started = 0    # Cut off the measurement for a small time while setting the new values
            self.range = int(self.set_range.get())
            self.powermeter.set_range(self.range)
            self.trigger = 1
            self.started = 1    # Resume the measurement
        else:
            print("You have not started connection to any device.")

    def buttonModifyPressed(self, channel, button_type):
        # This function is to modify the value in the entry box by using <<, <, >, and >>
        # Channel 0 refers the entry box: wavelength of the laser

        if button_type == 1:
            self.set_value[channel] -= self.rough_step[channel]
        elif button_type == 2:
            self.set_value[channel] -= self.fine_step[channel]
        elif button_type == 3:
            self.set_value[channel] += self.fine_step[channel]
        elif button_type == 4:
            self.set_value[channel] += self.rough_step[channel]

        if channel == 0:
            # Wavelength. The min and max value provided by the calibration table
            self.set_value[channel] = insanity_check(self.set_value[channel], 340, 1099)
            self.entry[channel].delete(0, tkinter.END)
            self.entry[0].insert(0, str(self.set_value[0])+ " nm")
        else:
            pass

    def processIncoming(self):
        """Handle all messages currently in the queue, if any."""
        while self.queue.qsize(  ):
            try:
                msg = self.queue.get(0)
                # Check contents of message and do whatever is needed. As a
                # simple test, print it (in real life, you would
                # suitably update the GUI's display in a richer fashion).
                print(msg)
            except Queue.Empty:
                # just on general principles, although we don't
                # expect this branch to be taken in this case
                pass

class ThreadedClient:
    """
    Launch the main part of the GUI and the worker thread. periodicCall and
    endApplication could reside in the GUI part, but putting them here
    means that you have all the thread controls in a single place.
    """
    def __init__(self, master):
        """
        Start the GUI and the asynchronous threads. We are in the main
        (original) thread of the application, which will later be used by
        the GUI as well. We spawn a new thread for the worker (I/O).
        """
        self.master = master
        self.running = 1

        # Create the queue
        self.queue = queue.Queue(  )

        # Set up the GUI part
        self.gui = GuiPart(master, self.queue, self.endApplication)
        master.protocol("WM_DELETE_WINDOW", self.endApplication)   # About the silly exit button

        # Start the procedure regarding the initialisation of experimental parameters and objects
        self.initialiseParameters()

        # Set up the thread to do asynchronous I/O
        # More threads can also be created and used, if necessary
        self.thread1 = threading.Thread(target=self.workerThread1_OPM)
        self.thread1.start(  )

        # Start the periodic call in the GUI to check if the queue contains
        # anything
        self.periodicCall(  )

    def initialiseParameters(self):

        # Initialisation of several variables
        self.average_opm = 0
        self.average_voltage_opm = 0

        # Obtain the calibration table
        f = open(CALIBRATION_FILE,'r')
        data = json.load(f)
        f.close()
        self.wavelength_table = data[0]
        self.responsivity_table = data[1]

        self.i = 1

    def periodicCall(self):
        """
        Check every 100 ms if there is something new in the queue.
        """
        self.gui.processIncoming(  )

        # Setting a refresh rate for periodic call
        self.master.after(REFRESH_RATE, self.periodicCall)

        # Check whether it is in autorange mode
        MAX_VOLTAGE = 2.4
        MIN_VOLTAGE = 0.02
        if self.gui.set_autorange.get() == 1:
            if self.average_voltage_opm > MAX_VOLTAGE:
                new_range = self.gui.range + 1
                new_range = insanity_check(new_range,1,5)
                self.gui.set_range.set(str(new_range))
                self.gui.changeRange()
            if self.average_voltage_opm < MIN_VOLTAGE:
                new_range = self.gui.range - 1
                new_range = insanity_check(new_range,1,5)
                self.gui.set_range.set(str(new_range))
                self.gui.changeRange()

        # Convert from average_voltage_opm to average_opm
        self.average_opm = self.conversion(self.average_voltage_opm)

        # Updating the display value of optical powermeter
        if self.gui.started == 1:
            power_str = self.floatToStringPower(self.average_opm)
            self.gui.display_opm.set(power_str)
        else:
            self.gui.display_opm.set("OFF")

        # PLOTTING ADD ON --->
        if self.gui.started:
            self.gui.ydata.pop(0)
            self.gui.ydata.append(self.average_opm)
        # <---

        # Shutting down the program
        if not self.running:
            print("Shutting Down")
            import sys
            sys.exit()

    def floatToStringPower(self,variable):
        if variable > 1:
            display = variable
            if variable >= 1e1:
                power_str = '%.1f'%round(display,1) + " " + "W"
            else:
                power_str = '%.2f'%round(display,2) + " " + "W"
        elif variable > 1e-3:
            display = variable *1e3
            if variable >= 1e-2:
                power_str = '%.1f'%round(display,1) + " " + "mW"
            else:
                power_str = '%.2f'%round(display,2) + " " + "mW"
        elif variable > 1e-6:
            display = variable *1e6
            if variable >= 1e-5:
                power_str = '%.1f'%round(display,1) + " " + "uW"
            else:
                power_str = '%.2f'%round(display,2) + " " + "uW"
        else:
            display = variable *1e9
            power_str = '%.1f'%round(display,1) + " " + "nW"

        return power_str

    def conversion(self, voltage):
        # Function that converts voltage to power
        amperage = voltage/RESISTORS[self.gui.range - 1]    # The 1st range refer to the 0th element of RESISTORS array
        index_wavelength = self.wavelength_table.index(int(self.gui.set_value[0])) # self.gui.set_value[0] refers to wavelength
        responsivity = self.responsivity_table[index_wavelength]
        power = amperage/float(responsivity)
        return power


    def workerThread1_OPM(self):
        """
        This is where we handle the asynchronous I/O. For example, it may be
        a 'select(  )'. One important thing to remember is that the thread has
        to yield control pretty regularly, by select or otherwise.
        """
        while self.running:
            if self.gui.started == True:
                # To simulate asynchronous I/O, we create a random number at
                # random intervals. Replace the following two lines with the real
                # thing.
                try:
                    # Optical Powermeter
                    if self.gui.trigger == 1:
                        time.sleep(0.02)     # Time to wait for the physical changes to the device: 20 ms
                        now = float(self.gui.powermeter.get_voltage())
                        self.average_voltage_opm = now  # Flush the previous measured values
                        self.gui.trigger = 0
                    else:
                        now = float(self.gui.powermeter.get_voltage())
                        self.average_voltage_opm = (NUM_OF_AVG-1)*self.average_voltage_opm/NUM_OF_AVG + now/NUM_OF_AVG
                except:
                    pass
            else:
                time.sleep(0.1)


    def endApplication(self):
        # Kill and wait for the processes to be killed
        self.running = 0
        time.sleep(0.1)
        # Close the connection to the device
        if self.gui.started:
            self.gui.powermeter.reset()
            self.gui.powermeter.close_port()


if __name__ == '__main__':

    root = tkinter.Tk(  )
    root.title("Optical Powermeter Version 1.03")

    img = tkinter.PhotoImage(file='icon.png')
    root.tk.call('wm', 'iconphoto', root._w, img)

    client = ThreadedClient(root)
    root.mainloop(  )
