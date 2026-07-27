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
clr.AddReference("DWSIM.UnitOperations")   # <-- required for Heater

from DWSIM.Automation import Automation3
interf = Automation3()
flowsheet = interf.CreateFlowsheet()

# ----------------------------------------------------------------------
# 1. Add compounds and property package
# ----------------------------------------------------------------------
flowsheet.AddCompound("Water")
flowsheet.AddCompound("Ethanol")
pp = flowsheet.CreateAndAddPropertyPackage("Peng-Robinson (PR)")

# ----------------------------------------------------------------------
# 2. Imports needed for stream handling
# ----------------------------------------------------------------------
from DWSIM.Interfaces.Enums.GraphicObjects import ObjectType
from System import Array
from DWSIM.UnitOperations import UnitOperations

# ----------------------------------------------------------------------
# 3. Create Feed Stream
# ----------------------------------------------------------------------
feed_obj = flowsheet.AddObject(ObjectType.MaterialStream, 50, 50, "Feed Stream")
feed_stream = feed_obj.GetAsObject()
feed_stream.SetTemperature(298.15)          # K
feed_stream.SetPressure(101325.0)           # Pa
feed_stream.SetMassFlow(10.0)               # kg/s
feed_stream.SetOverallMolarComposition(Array[float]([0.5, 0.5]))  # 50/50 molar Water‑Ethanol
feed_stream.SetPropertyPackage(pp)

# ----------------------------------------------------------------------
# 4. Heater Block
# ----------------------------------------------------------------------
heater_obj = flowsheet.AddObject(ObjectType.Heater, 150, 50, "Heater Block")
heater = heater_obj.GetAsObject()
heater.CalcMode = UnitOperations.Heater.CalculationMode.OutletTemperature
heater.OutletTemperature = 358.15          # K

# Energy stream (required by DWSIM UI, not used in calculations here)
energy_obj = flowsheet.AddObject(ObjectType.EnergyStream, 150, 100, "Heat Duty")
energy_stream = energy_obj.GetAsObject()

# ----------------------------------------------------------------------
# 5. Intermediate stream (Heater → Flash)
# ----------------------------------------------------------------------
inter_obj = flowsheet.AddObject(ObjectType.MaterialStream, 250, 50, "Heater to Flash")
inter_stream = inter_obj.GetAsObject()
inter_stream.SetPropertyPackage(pp)

# ----------------------------------------------------------------------
# 6. Flash Drum
# ----------------------------------------------------------------------
flash_obj = flowsheet.AddObject(ObjectType.Vessel, 350, 50, "Flash Drum")
flash = flash_obj.GetAsObject()   # not used directly, but kept for completeness

# ----------------------------------------------------------------------
# 7. Product streams
# ----------------------------------------------------------------------
vapor_obj = flowsheet.AddObject(ObjectType.MaterialStream, 450, 30, "Vapor Product")
vapor_stream = vapor_obj.GetAsObject()
vapor_stream.SetPropertyPackage(pp)

liquid_obj = flowsheet.AddObject(ObjectType.MaterialStream, 450, 70, "Liquid Product")
liquid_stream = liquid_obj.GetAsObject()
liquid_stream.SetPropertyPackage(pp)

# ----------------------------------------------------------------------
# 8. Connect objects (using -1, -1 for auto‑port resolution)
# ----------------------------------------------------------------------
flowsheet.ConnectObjects(feed_obj.GraphicObject, heater_obj.GraphicObject, -1, -1)
flowsheet.ConnectObjects(heater_obj.GraphicObject, inter_obj.GraphicObject, -1, -1)
flowsheet.ConnectObjects(inter_obj.GraphicObject, flash_obj.GraphicObject, -1, -1)
flowsheet.ConnectObjects(flash_obj.GraphicObject, vapor_obj.GraphicObject, -1, -1)
flowsheet.ConnectObjects(flash_obj.GraphicObject, liquid_obj.GraphicObject, -1, -1)

# ----------------------------------------------------------------------
# 9. Run the simulation
# ----------------------------------------------------------------------
interf.CalculateFlowsheet2(flowsheet)

# ----------------------------------------------------------------------
# 10. Extract and print results
# ----------------------------------------------------------------------
# Vapor product
v_mass = vapor_stream.GetMassFlow()
v_comp = vapor_stream.GetOverallMolarComposition()
v_comp_list = [float(x) for x in v_comp]   # convert .NET array to Python list

# Liquid product
l_mass = liquid_stream.GetMassFlow()
l_comp = liquid_stream.GetOverallMolarComposition()
l_comp_list = [float(x) for x in l_comp]

print("=== Vapor Product ===")
print(f"Mass Flow (kg/s): {v_mass:.4f}")
print(f"Molar Composition (Water, Ethanol): [{v_comp_list[0]:.4f}, {v_comp_list[1]:.4f}]")
print()
print("=== Liquid Product ===")
print(f"Mass Flow (kg/s): {l_mass:.4f}")
print(f"Molar Composition (Water, Ethanol): [{l_comp_list[0]:.4f}, {l_comp_list[1]:.4f}]")