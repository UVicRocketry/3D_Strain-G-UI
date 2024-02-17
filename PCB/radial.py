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

# KiCAD uses nanometers as its scale for some reason so we need to scale the values to that.
mm_to_nano   = 1000000
inch_to_nano = 2.54e+7

# Set the center of the radial pattern. For us, we just place a circle wherever we want it
# then check its properties and get the center point. 
center_x = 160 * mm_to_nano
center_y = 90 * mm_to_nano

#Variable radius change
radd = .0


def function(board, footrefs, radius, offset, total_offset):
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
        newpos = pcbnew.VECTOR2I(int(pos_x), int(pos_y))
        
        # Set the new position and angle for the module
        print("\ni=", i, "Footprint", footrefs[i]) 

        if foot is not None:
            foot.SetOrientationDegrees((total_offset + angle*i) + offset)
            foot.SetPosition(newpos)
            print("Setting orientation to", angle*i + offset)
            print("Setting position to", pos_x, pos_y)

    return

def main():
    # Get our board from pcbnew
    # We use this to access components, pads, vias, etc.
    board = pcbnew.GetBoard()
    print("Got board", board)

    # Footprint References or "footrefs" are the names of the footprints that we would like to mess around with.
    # The order of this list is also the same order that they will get laid out in radially.
    # This means if you would like gaps at regular intervals, you can add a dummy footref in, and add 
    # an if check to skip over those components in the for loop below.

    # 
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
    footrefs = ["U1", "U2", "U3", "Dummy",
                "U4", "U5", "U6", "Dummy",
                "U7", "U8", "U9", "Dummy",
                "U10", "U11", "U12", "Dummy"]
    """
    footrefs = ["U1", "U2", "U3", "Dummy",
                "U4", "U5", "U6", "Dummy",
                "U7", "U8", "U9", "Dummy",
                "U10", "Dummy", "U12", "Dummy", ]
    """
    radius = 1.5 + radd     
    offset = 90
    total_offset=180 + 360/16
    function(board, footrefs, radius, offset, total_offset)


    # Wheatstone bridge resistors on pin 8 of the HX711s
    footrefs = ["R2", "Dummy", "R5", "Dummy", "R8", "Dummy", "Dummy", "Dummy",
            "R11", "Dummy", "R14", "Dummy", "R17", "Dummy", "Dummy", "Dummy",
            "R20", "Dummy", "R23", "Dummy", "R26", "Dummy", "Dummy", "Dummy",
            "R29", "Dummy", "R32", "Dummy", "R35", "Dummy", "Dummy", "Dummy"]
    
    

    '''
    footrefs = ["R2", "Dummy", "R5", "Dummy", "R8", "Dummy", "Dummy", "Dummy",
            "R11", "Dummy", "R14", "Dummy", "R17", "Dummy", "Dummy", "Dummy",
            "R20", "Dummy", "R23", "Dummy", "R26", "Dummy", "Dummy", "Dummy",
            "R29", "Dummy", "Dummy", "Dummy", "R35", "Dummy", "Dummy", "Dummy"]
    '''
    
    '''
    footrefs = ["R2", "R1", "R5", "R4", "R8", "R7", "Dummy", "Dummy", "Dummy",
            "R11", "R10", "R14", "R13", "R17", "R16", "Dummy", "Dummy", "Dummy",
            "R20", "R19", "R23", "R22", "R26", "R25", "Dummy", "Dummy", "Dummy",
            "R29", "R28", "R32", "R31", "R35", "R34", "Dummy", "Dummy", "Dummy"]
    '''
    radius = 1.15 + radd
    offset = -93
    total_offset = 208
    function(board, footrefs, radius, offset, total_offset)
 # Wheatstone bridge resistors on pin 7 of the HX711s

    footrefs = ["Dummy", "R1", "Dummy", "R4", "Dummy", "R7", "Dummy", "Dummy",
            "Dummy", "R10", "Dummy", "R13", "Dummy", "R16", "Dummy", "Dummy",
            "Dummy", "R19", "Dummy", "R22", "Dummy", "R25",  "Dummy", "Dummy",
            "Dummy", "R28", "Dummy", "R31", "Dummy", "R34",  "Dummy", "Dummy"]
    
    '''
    footrefs = ["Dummy", "R1", "Dummy", "R4", "Dummy", "R7", "Dummy", "Dummy",
            "Dummy", "R10", "Dummy", "R13", "Dummy", "R16", "Dummy", "Dummy",
            "Dummy", "R19", "Dummy", "R22", "Dummy", "R25",  "Dummy", "Dummy",
            "Dummy", "R28", "Dummy", "Dummy", "Dummy", "R34",  "Dummy", "Dummy"]
    '''
    
    '''
    footrefs = ["R2", "R1", "R5", "R4", "R8", "R7", "Dummy", "Dummy", "Dummy",
            "R11", "R10", "R14", "R13", "R17", "R16", "Dummy", "Dummy", "Dummy",
            "R20", "R19", "R23", "R22", "R26", "R25", "Dummy", "Dummy", "Dummy",
            "R29", "R28", "R32", "R31", "R35", "R34", "Dummy", "Dummy", "Dummy"]
    '''
    radius = 1.25 + radd
    offset = 90
    total_offset = 210
    function(board, footrefs, radius, offset, total_offset)

    # Capacitors on pin 7 and 8 of HX711
    footrefs = ["C2", "C4", "C6", "Dummy",
                "C8", "C10", "C12", "Dummy",
                "C14", "C16", "C18", "Dummy",
                "C20", "C22", "C24", "Dummy"]
    """
    footrefs = ["C2", "C4", "C6", "Dummy",
                "C8", "C10", "C12", "Dummy",
                "C14", "C16", "C18", "Dummy",
                "C20", "Dummy", "C24", "Dummy"]
    """
    radius = 1.35 + radd
    offset = -6
    total_offset = 212
    function(board, footrefs, radius, offset, total_offset)

    # Capacitors on pin 1 of HX711
    footrefs = ["C1", "C3", "C5", "Dummy",
                "C7", "C9", "C11", "Dummy",
                "C13", "C15", "C17", "Dummy",
                "C19", "C21", "C23", "Dummy"]
    '''
    footrefs = ["C1", "C3", "C5", "Dummy",
                "C7", "C9", "C11", "Dummy",
                "C13", "C15", "C17", "Dummy",
                "C19", "Dummy", "C23", "Dummy"]
    '''
    radius = 1.65
    offset = 93
    total_offset = 194.
    function(board, footrefs, radius, offset, total_offset)

    # Other capacitor on pin 1 of HX711

    footrefs = ["C28", "C29", "C30", "Dummy",
                "C31", "C32", "C33", "Dummy",
                "C34", "C35", "C36", "Dummy",
                "C37", "C38", "C39", "Dummy"]
    '''
    footrefs = ["C28", "C29", "C30", "Dummy",
                "C31", "C32", "C33", "Dummy",
                "C34", "C35", "C36", "Dummy",
                "C37", "Dummy", "C39", "Dummy"]
    '''
    radius = 1.5
    offset = 94
    total_offset = 193
    function(board, footrefs, radius, offset, total_offset)

    # 4 mounting Holes (yes I'm incredibly lazy)
    footrefs = ["H1", "H2", "H3", "H4"]
    radius = 1.75    
    offset = 0
    total_offset = 0
    function(board, footrefs, radius, offset, total_offset)

    # 2 Shift registers
    footrefs = ["U13", "U16"]
    radius = 0.85 + radd    
    offset = 90
    total_offset = 90+2
    function(board, footrefs, radius, offset, total_offset)

    # 100 resistors on pin 8
    '''
    footrefs = ["R3", "R6", "R9", "Dummy",
                "R12", "R15", "R18", "Dummy",
                "R21", "R24", "R27", "Dummy",
                "R30", "Dummy", "R36",  "Dummy"]
    '''
    footrefs = ["R3", "R6", "R9", "Dummy",
                "R12", "R15", "R18", "Dummy",
                "R21", "R24", "R27", "Dummy",
                "R30", "R33", "R36",  "Dummy"]
    radius = 1.2 + radd
    offset = -8
    total_offset = 213
    function(board, footrefs, radius, offset, total_offset)
    # 100 resistors on pin 7
    footrefs = ["R41", "R48", "R42", "Dummy",
                "R45", "R43", "R46", "Dummy",
                "R44", "R47", "R51", "Dummy",
                "R49", "R52", "R50",  "Dummy"]
    """
    footrefs = ["R41", "R48", "R42", "Dummy",
                "R45", "R43", "R46", "Dummy",
                "R44", "R47", "R51", "Dummy",
                "R49", "Dummy", "R50",  "Dummy"]
    """
    radius = 1.36 + radd
    offset = -8
    total_offset = 215.5
    function(board, footrefs, radius, offset, total_offset)

    return

if __name__=="__main__":
    main()

