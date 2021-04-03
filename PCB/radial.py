import pcbnew
import math

'''
Run this script to automatically lay out the strain gauge contacts radially

    1)  Open the board in PCBNew
    2)  Open the scripting console: Tools > Scripting Console
    3)  Type 'ls' and hit enter. You should see this file in the printed list
    4)  Run 'execfile("radial.py")'
    5)  Done

Note: You must refresh the pcb to see the changes in PCBNew: Tools > Update PCB From Schematic

'''

# Set the center of the radial pattern. For us, we just place a circle wherever we want it
# then check its properties and get the center point. KiCAD uses nanometers as its scale for
# some reason so we need to scale the values from mm to that.
scale = 1000000
center_x = 150 * scale
center_y = 100 * scale

# Get our board from pcbnew
# We use this to access components, pads, vias, etc.
board = pcbnew.GetBoard()
print("Got board")

# Module References or "modrefs" are the names of the modules that we would like to mess around with.
# In our case, they are the radial wire contact pads that we want to adjust the orientation of.
# The order of this list is also the same order that they will get laid out in radially.

# For the radial wire contact pods
# modrefs = ["TP1", "TP2", "TP3", "TP4", "TP5", "TP6", "TP7", "TP8",
#            "TP25", "TP28",
#            "TP9", "TP10", "TP11", "TP12", "TP13", "TP14", "TP15", "TP16",
#            "TP26", "TP29",
#            "TP17", "TP18", "TP19", "TP20", "TP21", "TP22", "TP23", "TP24",
#            "TP27", "TP30"]

modrefs = ["U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8", "U9", "U10", "U11", "U12"]

print("Got modrefs:", modrefs)

# This list will store the modules corresponding to the names in modrefs
mods = []

for mod in modrefs:
    # Populate our list
    mods.append(board.FindModuleByReference(mod))

print("Got mods:", mods)

# Now that we have our modules we can start laying them out radially
num_mods    = len(modrefs)      # Number of modules to lay out radially
angle       = 360 / num_mods    # Angular increment between each module 
#radius      = 28500000          # 1.122 inches in nanometers (the default unit of kicad) (for radial wire contacts)
radius      = 22225000          # 0.875 inches (for HX711)
offset      = -90               # We'll need to offset each angle since the default orientation
                                # of the module is vertical

# enumerate just gives us an iterator i that we can use to adjust the angle
for i, mod in enumerate(mods):
    
    # Create the new position for the module
    # -1 or else the layout is "inverted" or something
    pos_x = -1*radius*math.cos(math.radians(angle*i)) + center_x
    pos_y = radius*math.sin(math.radians(angle*i)) + center_y
    newpos = pcbnew.wxPoint(pos_x, pos_y)
    
    # Set the new position and angle for the module
    print("Mod", modrefs[i]) 
    print("Setting orientation to", angle*i + offset)
    mod.SetOrientationDegrees(angle*i + offset)

    print("Setting position to", pos_x, pos_y)
    mod.SetPosition(newpos)


