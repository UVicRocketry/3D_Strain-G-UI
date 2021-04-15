from PyQt5 import QtGui, QtWidgets, uic, QtCore
from PyQt5.QtWidgets import QFileDialog, QTableWidget, QTableWidgetItem
from numpy.lib.function_base import sinc
import pyqtgraph.opengl as gl
import numpy as np
from pyqtgraph.opengl.items.GLGridItem import GLGridItem
from stl import mesh
import sys
import os
from serial import Serial
import math
import linecache
import json
import qdarkstyle

# Copy this line into the terminal and run it to install all the required libraries.
# pip3 install PyQT5 numpy numpy-stl pyserial pyqtgraph pyopengl qdarkstyle

class Rocket():
    # Used for log files
    _name = ""

    # List of meshes created from STL files
    _mesh_models = []

    # STL folder name
    _stl_dir = ""
    
    # Angular positions
    _yaw = []
    _pitch = []
    _roll = []

    _altitude = []
    _time = []

    # Set by the "Live Mode?" checkbox in the gui
    _livemode = False

    # Set by logfile_btn(). Contains the path of the .csv log file we are reading from
    _logfile_path = ""

    # Set by loadrocket_btn(). Contains the path of the .rocket file we are reading from
    _rocketfile_path = ""

    # How much the color of a strain section changes based on a strain reading
    # Higher numbers means more sensitive. 0.02 is a good bet
    _color_sensitivity = 0

    # Strain locations
    # This is gonna depend on the layout of the strain gauges. For now we will assume there are r rings of n gauges mounted
    # around the circumference of the fuselage. In this diagram:
    # n = 6 (3 visible strain gauges represented by 's', and 3 gauges that aren't visible as they are on the other side of the fuselage)
    # r = 5 (5 rings of strain gauges)
    '''
                +---------------------------------------------------------------------------------+
                |            s              s             s             s             s           |
      Boattail  |            s              s             s             s             s           | Nosecone
                |            s              s             s             s             s           |
                +---------------------------------------------------------------------------------+
                            r=0            r=1           r=2           r=3           r=4             
    '''
    # Since the CAD of the rocket is divided up into sections, we can color each depending on the strain reading. We need a good
    # way of accessing each section of the rocket
    
    # For this we use a dictionary. The key is an integer and the value is the index in _mesh_models that corresponds to the 
    # correct strain section. This dictionary is created by create_meshes()

    # To make reading the STL/CAD files easier, they have a standard naming system of the form "whatever_you_want-strain_section-n"
    # where n is the auto generated number that is created when you make copies of the strain section part in an assembly

    # The main reason we do it this way is that not all of the entries in _mesh_models are strain sections (ie the nosecone and fins)
    # This lets us use whatever we want for the model, but we only have to name the strain sections in solidworks
    # Another nice thing is that at least in the layout described above, when creating the assembly, we first add a strain section,
    # then create a series of circular patterns for a ring of strain sections. This should get you the right name
    # for all the strain sections without too much trouble

    _strain_sections = {}
    _r = 0
    _n = 0

    # Contains a list of the strain sections that are currently selected/highlighted in UI_strain_table
    # Used in update to highlight those sections a different color
    # Set by strain_table()
    _selected_strain_sections = []

    # Contains a list of the actual strain readings from the strain gauges
    # Used to update the strain values table in the gui (in update_gui())
    _strain_values = []

    # TODO, implement this in update() (Its a really tricky problem to solve)  
    # If the solidworks model has 8 strain sections per ring, but only 4 gauges per ring, _gradients_per_section = 1
    # if sw model has 16 ss per ring, and 4 sgs per ring, _gradients_per_section = 3
    _gradients_per_section = 0

    def __init__(self):
        print("Created Rocket!\n")

    def create_meshes(self):
        # Create a list of meshes from all the STL files in the STL_files folder according
        # to the layout specified above

        # Make sure that when exporting solidworks assembly as STL files, you click options,
        # then check "Do not translate STL output data to positive space"
        # This will make the origin in the assembly the point about which the STL model rotates
        # around in the graph. This is also how you set your center of gravity for the rocket.
        # The CG should be the origin in the solidworks assembly.

        # See add_rocket() for more info about what enumerate does here
        for index, filename in enumerate(os.listdir(self._stl_dir)):
            
            if filename.endswith(".STL"):
                print("Found .STL: " + filename)
                stl_model = mesh.Mesh.from_file(os.path.join(self._stl_dir, filename))
                verts, I, J, K = self.stl2mesh3d(stl_model)
                faces = np.stack((I,J,K)).T
                new_mesh = gl.GLMeshItem(vertexes=verts, faces=faces, smooth=False)
                self._mesh_models.append(new_mesh)

                # Add the strain section indices to _strain_sections
                if "strain_section" in filename:
                    # Filenames are in the form somecrap-strain_section-n.STL. We want n as our key
                    key = filename.split('-')   # key = [somecrap, strain_section, n.STL]
                    key = key[-1]               # key = n.STL
                    key = key.split('.')        # key = [n, STL]
                    key = key[0]                # key = n
                    self._strain_sections[key] = index

                    # Now if we want to access a strain section in _mesh_models to change its color, we can find its
                    # index in _mesh_models by accessing _strain_sections
        print("")

    def stl2mesh3d(self, stl_mesh):
        # Taken from https://chart-studio.plotly.com/~empet/15434.embed
        # It's some spooky magic that converts an stl file into a an array of points and vertices that
        # make up the mesh model of the rocket.
        
        # stl_mesh is read by nympy-stl from a stl file; it is  an array of faces/triangles (i.e. three 3d points) 
        # this function extracts the unique vertices and the lists I, J, K to define a Plotly mesh3d
        p, q, r = stl_mesh.vectors.shape #(p, 3, 3)
        # the array stl_mesh.vectors.reshape(p*q, r) can contain multiple copies of the same vertex;
        # extract unique vertices from all mesh triangles
        vertices, ixr = np.unique(stl_mesh.vectors.reshape(p*q, r), return_inverse=True, axis=0)
        I = np.take(ixr, [3*k for k in range(p)])
        J = np.take(ixr, [3*k+1 for k in range(p)])
        K = np.take(ixr, [3*k+2 for k in range(p)])
        return vertices, I, J, K

    def setup_arduino(self, serial_port: str):
        # Stuff for reading text from arduino doing serial.println()
        try:
            baud_rate = 115200 # In arduino .ino file, Serial.begin(baud_rate)
            self.ser = Serial(serial_port, baud_rate)
            #self._livemode = True
        except:
            print("Could not set up serial connection with Arduino. Check the connection and try again!\n")

    def get_color(self, n: int):
        # Given a strain reading, returns a color (tuple). Used to color the strain sections based on readings from the strain gauges.
        # We use a sigmoid function (a function that always returns values between 0 and 1) to scale our colors.
        # This makes sure that we never go over 255 (the max for a RGB color) 

        # Compressive strain readings are less than 0 so the sigmoid returns a number less than 0.5
        # Tensile strain readings greater than 0 so the sigmoid returns a number greater than 0.5
        # Higher strain means increased red and decreased blue

        # This is the rough distance between the max and min strain values
        # This is a graph of whats going on https://www.desmos.com/calculator/wyz0wqfabb
        # The x axis is the strain reading
        
        strain_magnitude = 130

        sigmoid_red     = 1 / (1 + math.exp((strain_magnitude+n)*self._color_sensitivity))
        #sigmoid_green   = -2 * abs((1 / (1 + math.exp(2*n*self._color_sensitivity))) - 0.5) + 1
        sigmoid_green   = 1 / (math.exp(0.05*n) + math.exp(-0.05*n))
        sigmoid_blue    = 1 / (1 + math.exp((strain_magnitude-n)*self._color_sensitivity))

        color   = QtGui.QColor(int(255*sigmoid_red), int(255*sigmoid_green), int(255*sigmoid_blue))

        return color

    def update(self, logfile_line: int):
        # Get rid of old serial data (the baud rate isn't fast enough to keep up so the buffer fills up)
        # self.ser.flushInput()                   
        # This is causing some weird behaviour so leaving it out and cranking up the frame rate so the buffer doesn't overflow
        # Should only be a problem when updating live from an arduino

        # Read an entire line in the form "time,yaw,pitch,roll,altitude,strain1,strain2,strain3,..."
        # We read either live from an arduino or from a log file
        if self._livemode:
            line        = self.ser.readline()
            line        = line.strip()          # Strip \n and \r (They cause problems)
            list_data   = line.split(b',')      # Make a list, delimiting on BINARY commas
        else:
            line        = linecache.getline(self._logfile_path, logfile_line)
            line        = line.strip()          
            list_data   = line.split(',')       # Delimiting on commas

        time                = list_data[0]              # Get timestamp
        angles              = list_data[1:4]            # Get ypr values
        altitude            = float(list_data[4])       # Get altitude value
        self._strain_values = list_data[5:]             # Get strain values. [n:] means from n to the end of the list

        # Now with list_data, we can update the model

        # Rotate by the difference in angle. rotate() takes 5 params: rotate(degrees, x, y, z, coord sys)
        # The x,y,z represent the axis to rotate around. We use cos and sin a bunch here because we want 
        # to rotate relative to the rocket coords, not to the global coords.
        # TODO this needs to be double checked. It seems to work fine but my linear algebra skills were never
        # the best.
        roll_radians = math.radians(self._roll)
        for m in self._mesh_models:
            m.rotate(self._yaw[-1]   - float(angles[2]), math.cos(roll_radians), math.sin(roll_radians), 0, True)
            m.rotate(self._pitch[-1] - float(angles[1]), math.sin(roll_radians), math.cos(roll_radians), 0, True)
            m.rotate(self._roll[-1]  - float(angles[0]), 0, 0, 1, True)

        # Update class variables to reflect new data
        self._yaw.append(float(angles[2]))
        self._pitch.append(float(angles[1]))
        self._roll.append(float(angles[0]))

        self._altitude.append(altitude)
        self._time = time

        # Color the strain sections based on strain values
        # if check to see if the current ss is selected by the user and thus needs to be highlighted
        for i in range(len(self._strain_values)):
            strain = float(self._strain_values[i])          # Strain reading
            ss_index = self._strain_sections[str(i + 1)]    # Index in _mesh_models that corresponds to ith strain section
            
            if i not in self._selected_strain_sections:
                color = self.get_color(strain)              # Color based on the strain
            else:
                color   = QtGui.QColor(255, 0, 255)         # Bright pink because section is selected in gui

            self._mesh_models[ss_index].setColor(color)     # Update the color of the strain mesh

class MainWindow(QtWidgets.QMainWindow):
    # TODO add a xyz coor graphic.
    
    _R = Rocket()
    _grid_height = 0.0          # The height with respect to the "bottom" z grid.
    _alititude_grid = None      # Becomes a GLGridItem
    _prev_altitude = 0.0        # The previous _grid_height

    _playing = 0                # Set by the frame pause/play button on the gui
    _frame_direction = 0        # Which direction we are moving in the log file. 1 = fwrd, -1 = rvrs, 0 = paused
    _total_logfile_lines = 0    # Set by logfile_btn(). Stores the total number of lines in the log file. Used by scrub_slider()

    def __init__(self, *args, **kwargs):
        
        super(MainWindow, self).__init__(*args, **kwargs)
        # Load the UI Page. uic is the thing that lets us use a .ui file
        uic.loadUi('3D_GUI.ui', self)
        
        # Add the grids to the graph in the gui
        self.setup_3D_graph()

        # Connect the buttons on the gui to the backend logic
        self.connect_gui()

        # The rest of the set up will happen when the user loads a .rocket file
        
    def set_framerate(self):
        # Update timer   
        self.timer = QtCore.QTimer()
        if self.UI_framerate_slider.value() != 0:
            self.timer.setInterval(int(1000/self.UI_framerate_slider.value()))
        else:
            self.timer.setInterval(2147483646)
        self.timer.timeout.connect(self.update_gui)
        self.timer.start()
        
    def setup_3D_graph(self):    
        
        # Creating and adding grids
        xgrid = gl.GLGridItem()
        ygrid = gl.GLGridItem()
        zgrid = gl.GLGridItem()
        self._altitude_grid = gl.GLGridItem()
        self.graph.addItem(xgrid)
        self.graph.addItem(ygrid)
        self.graph.addItem(zgrid)
        self.graph.addItem(self._altitude_grid)
        
        # Rotate x and y grids to face the correct direction
        xgrid.rotate(90, 0, 1, 0)
        ygrid.rotate(90, 1, 0, 0)
        
        # Translate x and y grids to to form a "corner"
        xgrid.translate(-1000, 0, 0)
        ygrid.translate(0, -1000, 0)
        zgrid.translate(0, 0, -1000)
        self._altitude_grid.translate(0, 0, -1000)

        # Set grid widths
        xgrid.setSpacing(100, 100, 0)
        ygrid.setSpacing(100, 100, 0)
        zgrid.setSpacing(100, 100, 0)
        self._altitude_grid.setSpacing(500, 500, 0)

        # Set total grid size
        xgrid.setSize(2000, 2000, 0)
        ygrid.setSize(2000, 2000, 0)
        zgrid.setSize(2000, 2000, 0)
        self._altitude_grid.setSize(2000, 2000, 0)

        # Zoom the camera out so we are not inside our model
        self.resetview_btn()

    def setup_2D_graphs(self):
        # Add stuff in here like axis labels and titles to the graphs
        pass

    def update_2D_graphs(self):
        pass

    def update_gui(self):
        if self._playing:

            # Step forward or reverse in our log file
            line_num = int(self.UI_linenum_LE.text()) + self._frame_direction
            self._R.update(line_num)
            self.UI_linenum_LE.setText(str(line_num))

            # Update the altitude grid. If rocket went up, dz is negative
            dz = self._prev_altitude - self._R._altitude
            self._prev_altitude = self._R._altitude

            if self._grid_height < 0:
                self._altitude_grid.translate(0, 0, 2000 - self._grid_height)
                self._grid_height = 2000
            elif self._grid_height > 2000:
                self._altitude_grid.translate(0, 0, -self._grid_height)
                self._grid_height = 0
            
            # TODO Change the 30 here to be based on the data rate. That way the altitude grid
            # moves in a realistic way when compared with the length of the model
            self._altitude_grid.translate(0, 0, 30*dz)
            self._grid_height += 30*dz

            # Update the scrub_slider position even if user hasn't moved it but the file is still playing
            self.UI_scrub_slider.setValue(int(self.UI_linenum_LE.text()))

            # Update the number of rows in UI_strain_table (It gets updated in here in case the user loads
            # a new rocket into the gui). There is one row per strain gauge. (r*n)
            self.UI_strain_table.setRowCount(self._R._r * self._R._n)

            # Add the values and labels to the tables on the gui. QTableWidgets only accept QTableWidgetItem
            # so we create those first, assign our value to it, then insert it into the table
            # Tables are accessed in the form (row, col, value)
            for i in range(self._R._r*self._R._n):
                self.UI_strain_table.setItem(i, 1, QTableWidgetItem(self._R._strain_values[i]))
            
            self.UI_ypr_table.setItem(0, 1, QTableWidgetItem(str(self._R._pitch[-1])))
            self.UI_ypr_table.setItem(1, 1, QTableWidgetItem(str(self._R._roll[-1])))
            self.UI_ypr_table.setItem(2, 1, QTableWidgetItem(str(self._R._yaw[-1])))
            self.UI_ypr_table.setItem(3, 1, QTableWidgetItem(str(self._R._altitude[-1])))
            self.UI_ypr_table.setItem(4, 1, QTableWidgetItem(str(self._R._time[-1])))        

            self.update_2D_graphs()

    def create_rocket(self):
        # TODO Read the data from the GUI that describes what parameters the rocket has.
        self._R.create_meshes()
        self.add_rocket(self._R)
        self._R.setup_arduino()

    def add_rocket_to_graph(self, R: Rocket):
        # Add meshes to the graph. The enumerate bit is from
        # https://stackoverflow.com/questions/3162271/get-loop-count-inside-a-python-for-loop
        for count, m in enumerate(R._mesh_models):
            print("Added mesh to graph. Total meshes: ", count + 1)
            self.graph.addItem(m)

        print("\n")

    def single_update(self):
        # This function will force the gui to update one frame.
        # It does not step forward in log files like update_gui()

        # We do this by setting the frame direction to 0, then calling update_gui()
        # This only needs to happen if the gui isn't already updating, hence the if 
        if not self._playing:
            fd = self._frame_direction
            self._frame_direction = 0
            self._playing = True
            self.update_gui()
            self._playing = False
            self._frame_direction = fd

    ## GUI Methods
    def connect_gui(self):
        # These methods connect a gui object's event to a method.
        # Here we can see UI_loadrocket_btn's "clicked" event is being connected to the UI_loadrocket_btn()
        # method in the backend. This means if UI_loadrocket_btn is clicked, UI_loadrocket_btn() runs.

        # Our naming convention is:
        #   gui objects:        UI_description_objecttype
        #   backend methods:    description_objecttype

        # This makes things much easier to understand.
        self.UI_loadrocket_btn.clicked.connect(self.loadrocket_btn)
        self.UI_framerate_slider.valueChanged.connect(self.set_framerate)
        self.UI_logfile_btn.clicked.connect(self.logfile_btn)
        self.UI_closelog_btn.clicked.connect(self.closelog_btn)
        self.UI_livemode_CB.stateChanged.connect(self.livemode_CB)
        self.UI_playpause_btn.clicked.connect(self.playpause_btn)
        self.UI_forward_btn.clicked.connect(self.forward_btn)
        self.UI_backward_btn.clicked.connect(self.backward_btn)
        self.UI_resetview_btn.clicked.connect(self.resetview_btn)
        self.UI_colorsensitivity_slider.valueChanged.connect(self.colorsensitivity_slider)
        self.UI_scrub_slider.valueChanged.connect(self.scrub_slider)
        self.UI_strain_table.itemSelectionChanged.connect(self.strain_table)
    
    def loadrocket_btn(self):
        # This creates a file dialog box so we can select a data file
        # getOpenFileName() returns the file path selected by the user AND the filter used 
        # as a tuple. In our case the filter is *.rocket but we only want the file path so we 
        # seperate them with this cool line courtesy of stack overflow.
        # https://stackoverflow.com/questions/43509220/qtwidgets-qfiledialog-getopenfilename-returns-a-tuple
        fname, filter = QFileDialog.getOpenFileName(self, 'Open file', filter="*.rocket")
        
        # Update the lineEdit beside "Load Rocket" button on the GUI.
        self.UI_loadrocket_LE.setText(fname)
        
        # Read the data from the file using the json library into a dictionary 
        with open(fname) as f:
            data_string = f.read()
        data_dict = json.loads(data_string) 

        # Assign the values read from the file to our rocket
        self._R._rocketfile_path    = fname
        self._R._name               = data_dict["NAME"]
        self._R._stl_dir            = data_dict["STL_DIRECTORY"]
        self._R._r                  = data_dict["RINGS"]
        self._R._n                  = data_dict["SG_PER_RING"]
        self._R._color_sensitivity  = data_dict["COLOR_SENSITIVITY"]

        # Create the rocket meshes from the stls
        self._R.create_meshes()

        # Add the meshes to the graph
        self.add_rocket_to_graph(self._R)
        
        # Initialize the framerate so that the user doesn't have to move the slider to start playback
        self.set_framerate() 

    def logfile_btn(self):
        fname, filter = QFileDialog.getOpenFileName(self, 'Open file', filter="*.csv")
        
        # Update the lineEdit beside "Load File" button on the GUI.
        self.UI_logfile_LE.setText(fname)
        
        # Update our Rocket's filepath
        self._R._logfile_path = fname
        
        # Get the total number of lines in the file. - 1
        with open(fname) as f:
            _total_logfile_lines = sum(1 for line in f) - 1

        # Update the max value of the slider
        self.UI_scrub_slider.setMaximum(_total_logfile_lines)

        print("Opened log file:", fname)
        print("Total lines:", _total_logfile_lines, "\n")

    def closelog_btn(self):
        # Clear the text on the line edit. This is for switching to live mode
        self.UI_logfile_LE.setText("")
        self._R._logfile_path = ""
        
        print("Closed log file\n")

    def livemode_CB(self):
        # Switch between livemode (reading from arduino) and logfile mode 
        if self.UI_livemode_CB.isChecked():
            print("Enabled live mode\n")
            self._R._livemode = True
        else:
            print("Disabled live mode\n")
            self._R._livemode = False
    
    def playpause_btn(self):
        if len(self._R._logfile_path) != 0:
            self._playing = self.UI_playpause_btn.isChecked()
            self._frame_direction = int(self._playing)
            
            if self._playing:
                print("Playing\n")
            else:
                print("Paused\n")
        else:
            print("No logfile loaded. Click the \"Load Log File\" button\n")
            self.UI_playpause_btn.setChecked(False)
            
    def forward_btn(self):
        # Step one frame forward, then pause
        self._frame_direction = 1
        self._playing = True
        self.update_gui()
        self._playing = False
        self.UI_playpause_btn.setChecked(False)
        print("Stepped forward 1 frame\n")

    def backward_btn(self):
        # Step one frame reverse, then pause

        # Makes sure we don't try to access line numbers below 1
        if int(self.UI_linenum_LE.text()) != 1:
            self._frame_direction = -1
            self._playing = True
            self.update_gui()
            self._playing = False
            self._frame_direction = 1
            self.UI_playpause_btn.setChecked(False)
            print("Stepped backwards 1 frame\n")

    def resetview_btn(self):
        #self.graph.reset()
        self.graph.setCameraPosition(distance=3000)
        print("Reset view")
        print("Camera postion is:", self.graph.cameraPosition(), "\n")
    
    def colorsensitivity_slider(self):
        self._R._color_sensitivity = self.UI_colorsensitivity_slider.value()/5000

    def scrub_slider(self):
        # The max value of the slider is set to the total number of lines in the logfile
        # We can then use the slider to "scrub" through the logfile like a youtube video
        # By setting the text of UI_linenum_LE to the slider value, it will integrate nicely
        # with the rest of the methods that use the log files
        self.UI_linenum_LE.setText(str(self.UI_scrub_slider.value()))
        
        # This updates the gui if it is currently paused
        self.single_update()

    def strain_table(self):
        # Clear out the old, now possibly unselected sections
        self._R._selected_strain_sections.clear()

        # Add the new selected sections to the list
        for cell in self.UI_strain_table.selectedItems():
            self._R._selected_strain_sections.append(cell.row())

        # This updates the gui if it is currently paused
        self.single_update()

def main():
    app = QtWidgets.QApplication(sys.argv)

    # Load the dark theme from qdarkstyle following this guide
    # https://github.com/ColinDuquesnoy/QDarkStyleSheet
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    main = MainWindow()
    main.show()
    sys.exit(app.exec_())

if __name__ == '__main__':      
    main()
