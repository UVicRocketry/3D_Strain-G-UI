from asyncio.windows_events import NULL
import pcbnew
import math

'''
Created by JJ De Rooy: jj.derooy123@gmail.com for questions.

Run this script to automatically lay out the strain gauge contacts radially

    1)  Open the board in PCBNew
    2)  Open the scripting console: Tools > Scripting Console
    3)  Type 'ls' and hit enter. You should see this file in the printed list. If not, cd to it.
    4)  Run 'execfile("radial.py")' or if that doesn't work, 'exec(open("radial.py").read())'
    5)  Done ** Also to save time ALT+P will repeat last command in the shell.

Note: You must refresh the components to see any changes. By pressing CTRL+A all components are
highlighted and thus updated.

For more info on how this script works, have a look at the source .h files for pcbnew
https://github.com/KiCad/kicad-source-mirror/tree/master/pcbnew

'''

#KiCAD uses nanometers as its scale for some reason so we need to scale the values to that.
mm_to_nano   = 1000000
inch_to_nano = 2.54e+7

# Set the center of the radial pattern. For us, we just place a circle wherever we want it
# then check its properties and get the center point. 
center_x = 160 * mm_to_nano
center_y = 90 * mm_to_nano

# Get our board from pcbnew
# We use this to access components, pads, vias, etc.
board = pcbnew.GetBoard()
print("Got board", board)

# Footprint References or "footrefs" are the names of the footprints that we would like to mess around with.
# The order of this list is also the same order that they will get laid out in radially.
# This means if you would like gaps at regular intervals, you can add a dummy footref in, and add 
# an if check to skip over those components in the for loop below.

# Just uncomment out a footref list, and its respective radius and offset and run the script as outlined above.
# Sometimes we'll need to offset each angle since the default orientation of the footprint is not what we want.
# It is very helpful to use the measure tool to get the radius and angle from the center of the circle.
# total_offset sets the initial starting angle for rotation

# For the radial wire contact pads
'''
footrefs = ["TP1", "TP2", "TP3", "TP4", "TP5", "TP6", "TP7", "Dummy", "Dummy",
           "TP8", "TP9", "TP10", "TP11", "TP12", "TP13", "TP14", "Dummy", "Dummy",
           "TP15", "TP16", "TP17", "TP18","TP19", "TP20", "TP21", "Dummy", "Dummy",
           "TP22", "TP23", "TP24", "TP25", "TP26", "TP27", "TP28", "Dummy", "Dummy"]
radius = 1.86
offset = -90
total_offset=180 + 1.5*360/36
'''

# HX711s
'''
footrefs = ["U1", "U2", "U3", "Dummy", "Dummy",
            "U4", "U5", "U6", "Dummy", "Dummy",
            "U7", "U8", "U9", "Dummy", "Dummy",
            "U10", "U11", "U12", "Dummy", "Dummy"]
radius = 1.7     
offset = -90
total_offset=180 + 360/18 + 360/52
'''

# Wheatstone bridge resistors on pin 7 and 8 of the HX711s
'''
footrefs = ["R1", "R2", "R4", "R5", "R7", "R8", "Dummy", "Dummy", "Dummy",
            "R10", "R11", "R13", "R14", "R16", "R17", "Dummy", "Dummy", "Dummy",
            "R19", "R20", "R22", "R23", "R25", "R26", "Dummy", "Dummy", "Dummy",
            "R28", "R29", "R31", "R32", "R34", "R35", "Dummy", "Dummy", "Dummy"]
radius = 2.08
offset = 90
total_offset = 200
'''

# Capacitors on pin 7 and 8 of HX711
'''
footrefs = ["C2", "C4", "C6", "Dummy", "Dummy",
            "C8", "C10", "C12", "Dummy", "Dummy",
            "C14", "C16", "C18", "Dummy", "Dummy",
            "C20", "C22", "C24", "Dummy", "Dummy"]
radius = 1.933
offset = 0
total_offset = 200
'''

# Capacitors on pin 1 of HX711
'''
footrefs = ["C1", "C3", "C5", "Dummy", "Dummy",
            "C7", "C9", "C11", "Dummy", "Dummy",
            "C13", "C15", "C17", "Dummy", "Dummy",
            "C19", "C21", "C23", "Dummy", "Dummy"]
radius = 1.57    
offset = -90
total_offset = 215.5
'''

# 4 mounting Holes (yes I'm incredibly lazy)

footrefs = ["H1", "H2", "H3", "H4"]
radius = 1.75    
offset = 0
total_offset = 0


# 2 Shift registers
'''
footrefs = ["U13", "U16"]
radius = 0.75    
offset = 90
total_offset = 0
'''

# 1k resistors on pin 8
'''
footrefs = ["R3", "R6", "R9", "Dummy", "Dummy",
            "R12", "R15", "R18", "Dummy", "Dummy",
            "R21", "R24", "R27", "Dummy", "Dummy",
            "R30", "R33", "R36",  "Dummy", "Dummy"]
radius = 1.96
offset = -90
total_offset = 204.5
'''

print("\nGot footrefs:", footrefs)
print("Total number of footrefs:", len(footrefs))

# This list will store the modules corresponding to the names in footrefs
foots = []

for foot in footrefs:
    # Populate our list
    if foot == "Dummy":
        foots.append(None)
    else:
        foots.append(board.FindFootprintByReference(foot))

print("\nGot footprints:", foots)
print("Total number of footprints:", len(foots))

# Now that we have our footprints we can start laying them out radially
# Our radius was set above.
num_foots = len(footrefs)      # Number of footprints to lay out radially
angle     = 360 / num_foots    # Angular increment between each footprint

# enumerate just gives us an iterator i that we can use to adjust the angle
for i, foot in enumerate(foots):
    
    # Create the new position for the module
    # -1 or else the layout is "inverted" or something idk lol
    pos_x = -1*radius*inch_to_nano*math.cos(math.radians(angle*i + total_offset)) + center_x
    pos_y = radius*inch_to_nano*math.sin(math.radians(angle*i + total_offset)) + center_y
    newpos = pcbnew.wxPoint(pos_x, pos_y)
    
    # Set the new position and angle for the module
    print("\ni=", i, "Footprint", footrefs[i]) 

    if foot is not None:
        foot.SetOrientationDegrees((total_offset + angle*i) + offset)
        foot.SetPosition(newpos)
        print("Setting orientation to", angle*i + offset)
        print("Setting position to", pos_x, pos_y)


