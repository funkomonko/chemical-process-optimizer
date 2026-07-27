import clr
import sys
import os

# Point this to your DWSIM installation folder
dwsimpath = r"C:\Users\YourName\AppData\Local\DWSIM" 

# Add DWSIM to the system path so Python can find the .dll files
sys.path.append(dwsimpath)

# Load the core DWSIM libraries via pythonnet
clr.AddReference("CapeOpen")
clr.AddReference("DWSIM.Automation")
clr.AddReference("DWSIM.Interfaces")
clr.AddReference("DWSIM.GlobalSettings")
clr.AddReference("DWSIM.SharedClasses")
clr.AddReference("DWSIM.Thermodynamics")

from DWSIM.Automation import Automation3

# Initialize the DWSIM Automation engine
interf = Automation3()
print("DWSIM Automation Engine successfully loaded!")

# Create a blank flowsheet
flowsheet = interf.CreateFlowsheet()
print("Blank flowsheet created successfully in memory.")