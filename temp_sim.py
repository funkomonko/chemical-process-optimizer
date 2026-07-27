import sys
import os
import clr

dwsim_path = r"C:/Users/Rayirth/AppData/Local/DWSIM"
thermocs_path = r"C:/Users/Rayirth/AppData/Local/DWSIM/ThermoCS"

sys.path.append(dwsim_path)
sys.path.append(thermocs_path)
os.chdir(dwsim_path)

if hasattr(os, 'add_dll_directory'):
    os.add_dll_directory(dwsim_path)
    os.add_dll_directory(thermocs_path)

# Force load all DWSIM dependencies into memory
clr.AddReference("CapeOpen")
clr.AddReference("DWSIM.Automation")
clr.AddReference("DWSIM.Interfaces")
clr.AddReference("DWSIM.GlobalSettings")
clr.AddReference("DWSIM.SharedClasses")
clr.AddReference("DWSIM.Thermodynamics")
clr.AddReference("ThermoCS")
clr.AddReference("DWSIM.UnitOperations")

from DWSIM.Automation import Automation3
from DWSIM.Interfaces.Enums.GraphicObjects import ObjectType
from DWSIM.UnitOperations import UnitOperations
from System import Array

# ----------------------------------------------------------------------
# Create automation interface and a new flowsheet
# ----------------------------------------------------------------------
interf = Automation3()
flowsheet = interf.CreateFlowsheet()

# ----------------------------------------------------------------------
# Add compounds and property package (Peng‑Robinson)
# ----------------------------------------------------------------------
flowsheet.AddCompound("Water")
flowsheet.AddCompound("Ethanol")
pp = flowsheet.CreateAndAddPropertyPackage("Peng-Robinson (PR)")

# ----------------------------------------------------------------------
# 1) Feed stream (50/50 molar Water‑Ethanol)
# ----------------------------------------------------------------------
feed_obj = flowsheet.AddObject(ObjectType.MaterialStream, 50, 50, "Feed Stream")
feed_stream = feed_obj.GetAsObject()
feed_stream.SetTemperature(298.15)          # K
feed_stream.SetPressure(101325.0)           # Pa
feed_stream.SetMassFlow(10.0)               # kg/s
feed_stream.SetOverallMolarComposition(Array[float]([0.5, 0.5]))
feed_stream.SetPropertyPackage(pp)

# ----------------------------------------------------------------------
# 2) Heater (outlet temperature 358.15 K)
# ----------------------------------------------------------------------
heater_obj = flowsheet.AddObject(ObjectType.Heater, 150, 50, "Heater Block")
heater = heater_obj.GetAsObject()
heater.CalcMode = UnitOperations.Heater.CalculationMode.OutletTemperature
heater.OutletTemperature = 358.15

# ----------------------------------------------------------------------
# 3) Energy stream for the heater (optional but shown)
# ----------------------------------------------------------------------
energy_obj = flowsheet.AddObject(ObjectType.EnergyStream, 150, 100, "Heat Duty")
energy_stream = energy_obj.GetAsObject()

# ----------------------------------------------------------------------
# 4) Intermediate material stream (heater → flash)
# ----------------------------------------------------------------------
inter_obj = flowsheet.AddObject(ObjectType.MaterialStream, 250, 50, "Heater‑to‑Flash")
inter_stream = inter_obj.GetAsObject()
inter_stream.SetPropertyPackage(pp)

# ----------------------------------------------------------------------
# 5) Flash drum
# ----------------------------------------------------------------------
flash_obj = flowsheet.AddObject(ObjectType.Vessel, 350, 50, "Flash Drum")
flash = flash_obj.GetAsObject()   # no property package needed

# ----------------------------------------------------------------------
# 6) Vapor and liquid product streams
# ----------------------------------------------------------------------
vapor_obj = flowsheet.AddObject(ObjectType.MaterialStream, 450, 30, "Vapor Product")
vapor_stream = vapor_obj.GetAsObject()
vapor_stream.SetPropertyPackage(pp)

liquid_obj = flowsheet.AddObject(ObjectType.MaterialStream, 450, 70, "Liquid Product")
liquid_stream = liquid_obj.GetAsObject()
liquid_stream.SetPropertyPackage(pp)

# ----------------------------------------------------------------------
# 7) Connect the topology (always via intermediate streams)
# ----------------------------------------------------------------------
flowsheet.ConnectObjects(feed_obj.GraphicObject, heater_obj.GraphicObject, -1, -1)
flowsheet.ConnectObjects(heater_obj.GraphicObject, inter_obj.GraphicObject, -1, -1)
flowsheet.ConnectObjects(inter_obj.GraphicObject, flash_obj.GraphicObject, -1, -1)
flowsheet.ConnectObjects(flash_obj.GraphicObject, vapor_obj.GraphicObject, -1, -1)
flowsheet.ConnectObjects(flash_obj.GraphicObject, liquid_obj.GraphicObject, -1, -1)
# Connect the energy stream to the heater (optional)
flowsheet.ConnectObjects(energy_obj.GraphicObject, heater_obj.GraphicObject, -1, -1)

# ----------------------------------------------------------------------
# 8) Run the simulation
# ----------------------------------------------------------------------
feed_stream.Calculate()
inter_stream.Calculate()
vapor_stream.Calculate()
liquid_stream.Calculate()
interf.CalculateFlowsheet2(flowsheet)

# ----------------------------------------------------------------------
# 9) Extract and print results
# ----------------------------------------------------------------------
v_mass = vapor_stream.GetMassFlow()
v_comp = vapor_stream.OverallMolarComposition   # .NET array
v_comp_list = [float(x) for x in v_comp]

l_mass = liquid_stream.GetMassFlow()
l_comp = liquid_stream.OverallMolarComposition
l_comp_list = [float(x) for x in l_comp]

print("Vapor product mass flow (kg/s):", v_mass)
print("Vapor product molar composition (Water, Ethanol):", v_comp_list)
print("Liquid product mass flow (kg/s):", l_mass)
print("Liquid product molar composition (Water, Ethanol):", l_comp_list)