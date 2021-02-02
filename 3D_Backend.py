from OpenGL.raw.GL.VERSION.GL_1_0 import GL_LINEAR_ATTENUATION
from PyQt5 import QtGui, QtWidgets, uic, QtCore
from PyQt5.QtWidgets import QFileDialog
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

# pip3 install PyQT5 numpy numpy-stl pyserial pyqtgraph pyopengl

class Rocket():
    # Will be used for log files
    _name = ""

    # List of meshes created from STL files
    _mesh_models = []

    # STL folder name
    _stl_dir = ""
    
    # Angular positions
    _yaw = 0.0
    _pitch = 0.0
    _roll = 0.0

    _altitude = 0.0
    _time = 0.0

    # Set by the "Live Mode?" checkbox in the gui
    _livemode = False

    # Set by logfile_btn(). Contains the path of the log file we are reading from
    _logfile_path = ""

    # How much the color of a strain section changes based on a strain reading
    # Higher numbers means more sensitive
    _color_sensitivity = 0.02

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

    # TODO, implement this in update() (Its a really tricky problem to solve)  
    # For instance if the solidworks model has 8 strain sections per ring, but only 4 gauges per ring, _gradients_per_section = 1
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
        print("\n")

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
            print("Could not set up serial connection with Arduino. Check the connection and try again!\n\n")

    def get_color(self, n: int):
        # Given a strain reading, returns a color (tuple). Used to color the strain sections based on readings from the strain gauges.
        # We use a sigmoid function (a function that always returns values between 0 and 1) to scale our colors.
        # This makes sure that we never go over 255 (the max for a RGB color) 

        # Compressive strain readings are less than 0 so the sigmoid returns a number less than 0.5
        # Tensile strain readings greater than 0 so the sigmoid returns a number greater than 0.5
        # Higher strain means increased red and decreased blue
        sigmoid = 1 / (1 + math.exp(-n*self._color_sensitivity))
        color   = QtGui.QColor(int(255*sigmoid), 0, int(255*(1-sigmoid)))

        return color

    def update(self, logfile_line: int):
        # Get rid of old serial data (the baud rate isn't fast enough to keep up so the buffer fills up)
        # self.ser.flushInput()                   
        # This is causing some weird behaviour so leaving it out and cranking up the frame rate so the buffer doesn't overflow
        # Should only be a problem when updating live from an arduino

        # Read an entire line in the form "time,yaw,pitch,roll,altitude,strain1,strain2,strain3,..."
        # We read from either live from an arduino or from a log file
        if self._livemode:
            line        = self.ser.readline()
            line        = line.strip()          # Strip \n and \r (They cause problems)
            list_data   = line.split(b',')      # Make a list, delimiting on BINARY commas
        else:
            line        = linecache.getline(self._logfile_path, logfile_line)
            line        = line.strip()          
            list_data   = line.split(',')       # Delimiting on commas

        time        = list_data[0]              # Get timestamp
        angles      = list_data[1:4]            # Get ypr values
        altitude    = float(list_data[4])       # Get altitude value
        strains     = list_data[5:]             # Get strain values. [n:] means from n to the end of the list

        # Now with list_data, we can update the model

        # Rotate by the difference in angle. rotate() takes 5 params: rotate(degrees, x, y, z, coord sys)
        # The x,y,z represent the axis to rotate around. We use cos and sin a bunch here because we want 
        # to rotate relative to the rocket coords, not to the global coords.
        # TODO this needs to be double checked. It seems to work fine but my linear algebra skills were never
        # the best.
        roll_radians = math.radians(self._roll)
        for m in self._mesh_models:
            m.rotate(self._yaw   - float(angles[2]), math.cos(roll_radians), math.sin(roll_radians), 0, True)
            m.rotate(self._pitch - float(angles[1]), math.sin(roll_radians), math.cos(roll_radians), 0, True)
            m.rotate(self._roll  - float(angles[0]), 0, 0, 1, True)

        # Update class variables to reflect new data
        self._yaw = float(angles[2])
        self._pitch = float(angles[1])
        self._roll = float(angles[0])

        self._altitude = altitude
        self._time = time # TODO This breaks in live mode for some reason??

        # Color the strain sections based on strain values
        for i in range(len(strains)):
            strain = float(strains[i])                      # Strain reading
            ss_index = self._strain_sections[str(i + 1)]    # Index in _mesh_models that corresponds to ith strain section
            color = self.get_color(strain)                  # Color based on the strain
            self._mesh_models[ss_index].setColor(color)     # Update the color of the strain mesh


class MainWindow(QtWidgets.QMainWindow):
    # TODO Added pause and play button, and step fwrd and reverse, now make them work.
    # TODO add a xyz coor graphic.
    
    # Declare our Rocket. __init__ will do the rest
    _R = Rocket()
    _grid_height = 0.0      # The height with respect to the "bottom" z grid.
    _alititude_grid = None  # Becomes a GLMeshItem
    _prev_altitude = 0.0    # The previous _grid_height

    _playing = 0            # Set by the frame pause/play button on the gui
    _frame_direction = 0    # Which direction we are moving in the log file. 1 = fwrd, -1 = rvrs, 0 = paused

    def __init__(self, *args, **kwargs):
        
        super(MainWindow, self).__init__(*args, **kwargs)
        # Load the UI Page. uic is the thing that lets us use a .ui file
        uic.loadUi('3D_GUI.ui', self)
        
        self.setup_graph()
        self.connect_gui()

        # The rest of the methods will be called by the user in the GUI
        # TODO Use the configparser library to load .rocket files with this info in them
        self._R._stl_dir = "STL_files"
        self._R._r = 3
        self._R._n = 4
        self._R._gradients_per_section = 1
        self._R.create_meshes()
        self._R.setup_arduino("COM3")
        self.add_rocket_to_graph(self._R)

    def set_framerate(self):
        # Update timer   
        self.timer = QtCore.QTimer()
        if self.UI_framerate_slider.value() != 0:
            self.timer.setInterval(int(1000/self.UI_framerate_slider.value()))
        else:
            self.timer.setInterval(2147483646)
        self.timer.timeout.connect(self.update_gui)
        self.timer.start()
        
    def setup_graph(self):    
        
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
        self.graph.setCameraPosition(distance=2000)
        print("Camera postion is:", self.graph.cameraPosition(), "\n")

    def update_gui(self):
        if self._playing:
            
            # TODO this will break when we are on line 0 and step backwards
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

            # Update the altitude line edit on the gui
            self.UI_altitude_LE.setText(str(self._R._altitude))
            self.UI_altitude_time_LE.setText(str(self._R._time))

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

    ## GUI Methods
    def connect_gui(self):
        # These methods connect a gui object's event to a method.
        # Here we can see UI_browse_btn's "clicked" event is being connected to the browse_btn()
        # method in the backend. This means if UI_browse_btn is clicked, browse_btn() runs.

        # Our naming convention is:
        #   gui objects:        UI_description_objecttype
        #   backend methods:    description_objecttype

        # This makes things much easier to understand.
        self.UI_framerate_slider.valueChanged.connect(self.set_framerate)
        self.UI_browse_btn.clicked.connect(self.browse_btn)
        self.UI_logfile_btn.clicked.connect(self.logfile_btn)
        self.UI_closelog_btn.clicked.connect(self.closelog_btn)
        self.UI_livemode_CB.stateChanged.connect(self.livemode_CB)
        self.UI_playpause_btn.clicked.connect(self.playpause_btn)
        self.UI_forward_btn.clicked.connect(self.forward_btn)
        self.UI_backward_btn.clicked.connect(self.backward_btn)
        self.UI_resetview_btn.clicked.connect(self.resetview_btn)

    def browse_btn(self):
        # This creates a file dialog box so we can select a data file
        # getOpenFileName() returns the file path selected by the user AND the filter used 
        # as a tuple. In our case the filter is *.rocket but we only want the file path so we 
        # seperate them with this cool line courtesy of stack overflow.
        # https://stackoverflow.com/questions/43509220/qtwidgets-qfiledialog-getopenfilename-returns-a-tuple
        fname, filter = QFileDialog.getOpenFileName(self, 'Open file', filter="*.rocket")
        
        # Update the lineEdit beside "Browse" button on the GUI.
        self.UI_browse_LE.setText(fname)

    def logfile_btn(self):
        fname, filter = QFileDialog.getOpenFileName(self, 'Open file')
        
        # Update the lineEdit beside "Load File" button on the GUI.
        self.UI_logfile_LE.setText(fname)

        # Update our Rocket's filepath
        self._R._logfile_path = fname

        print("Opened log file:", fname, "\n")
    
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
        self._playing = self.UI_playpause_btn.isChecked()
        self._frame_direction = int(self._playing)
        
        if self._playing:
            print("Playing\n")
        else:
            print("Paused\n")
            
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
        self._frame_direction = -1
        self._playing = True
        self.update_gui()
        self._playing = False
        self._frame_direction = 1
        self.UI_playpause_btn.setChecked(False)
        print("Stepped backwards 1 frame\n")

    def resetview_btn(self):
        self.graph.reset()
        self.graph.setCameraPosition(distance=2000)
        print("Reset view")
        print("Camera postion is:", self.graph.cameraPosition(), "\n")



def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())

if __name__ == '__main__':      
    main()
