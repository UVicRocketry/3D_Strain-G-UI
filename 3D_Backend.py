from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtWidgets import QFileDialog
import pyqtgraph.opengl as gl
import numpy as np
from pyqtgraph.opengl.items.GLGridItem import GLGridItem
from stl import mesh
import sys
import os
from serial import Serial
import math

# pip3 install PyQT5 numpy numpy-stl pyserial pyqtgraph opengl

class Rocket():
    # Used for log files
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

    # Set True if setup_arduino() is successful. This is to prevent a bunch of self.ser
    # does not exist errors when update is called if there is no arduino connected
    _arduino_connected = False

    # How much the color of a strain section changes based on a strain reading
    # Higher numbers means more sensitive
    _color_sensitivity = 1

    ## Strain locations
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
    
    # For this we use a dictionary. The key is of the form r-n and the value is the index in _mesh_models that corresponds to the 
    # correct strain section. This dictionary is created by create_meshes()

    # To make reading the STL/CAD files easier, they have a standard naming system of the form whatever_you_want-strain-section_r-n
    # Starting with the first gauge in the first ring we would name the part in CAD 'blahblahblah-strain-section_1-1' 
    # the second 'more_crap_strain-section_1-2' etc. The first gauge in the second ring would be 'rockets_go_brrr_strain-section_2-1' etc

    # The main reason we do it this way is that not all of the entries in _mesh_models are strain sections (ie the nosecone and fins)
    # This lets us use whatever we want for the model, but we only have to name the strain sections in solidworks
    # Another nice thing is that at least in the layout described above, when creating the assembly, we first add a strain section,
    # then create a circular pattern for a ring of strain sections, then a linear pattern of that ring. This *should* get you the right name
    # for all the strain sections without too much trouble

    _strain_sections = {} 
    _r = 0
    _n = 0

    def __init__(self):
        print("Created Rocket!\n\n")

    def create_meshes(self):
        # Create a list of meshes from all the STL files in the STL_files folder according
        # to the layout specified above

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
                if filename.find("strain-section"):
                    l = filename.split('_')                     # Split on '_'. Now l = [crap from SW naming, "strain-section", "r-n"]
                    key = l[len(l) - 1]                         # Get the last thing in l (should be "r-n")
                    if key not in self._strain_sections.keys(): # Shouldn't happen, but check for duplicate names
                        self._strain_sections[key] = index
                    else:
                        print("Duplicate strain-section found: ", filename, " Check .STL filenames!")

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
            self._arduino_connected = True
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
        color   = (255*sigmoid, 0, 255*(1 - sigmoid))    # (r, g, b)

        return color

    def update(self):
        if self._arduino_connected:
            # Get rid of old serial data (the baud rate isn't fast enough to keep up so the buffer fills up)
            # self.ser.flushInput()                   
                                                    
            line        = self.ser.readline()       # Read an entire line in the form "yaw,pitch,roll,altitude,strain1,strain2,strain3,..."
            line        = line.strip()              # Strip \n and \r (They cause problems)
            list_data   = line.split(b',')          # Make a list, delimiting on binary commas
            angles      = list_data[0:3]            # Get ypr values
            altitude    = list_data[3:4]
            strains     = list_data[4:-1]           # Get strain values. [n:-1] means from n to the end of the list

            # Rotate by the difference in angle
            for m in self._mesh_models:
                m.rotate(self._yaw   - float(angles[2]), 1, 0, 0)
                m.rotate(self._pitch - float(angles[1]), 0, 1, 0)
                m.rotate(self._roll  - float(angles[0]), 0, 0, 1)

            # Update class variables to reflect new data
            self._yaw = float(angles[2])
            self._pitch = float(angles[1])
            self._roll = float(angles[0])

            self._altitude = altitude

            # Update the strain section colors
            for ring in range(0, self._r):
                for sg in range(0, self._n):
                    # Get the index of _mesh_models that corresponds to our data point from the _strain_sections dictionary
                    # Keys are in the form "r-n"
                    ss_index = self._strain_sections[str(ring) + "-" + str(sg)]    
                    
                    # Total number of iterations through the double loop
                    strain_reading = strains[ring*self._n + sg] 
                    
                    # Get a color based on the strain
                    color = self.get_color(strain_reading)

                    # Update the color of the mesh
                    self._mesh_models[ss_index].setColor(color)                
                    

class MainWindow(QtWidgets.QMainWindow):

    # Declare our Rocket. __init__ will do the rest
    R = Rocket()

    def __init__(self, *args, **kwargs):
        
        super(MainWindow, self).__init__(*args, **kwargs)
        # Load the UI Page. uic is the thing that lets us use a .ui file
        uic.loadUi('3D_GUI.ui', self)
        
        self.setup_graph()
        self.connect_gui()

        # The rest of the methods will be called by the user in the GUI
        # TODO Use the configparser library to load .rocket files with this info in them
        self.R._stl_dir = "STL_files"
        self.R._r = 3
        self.R._n = 4
        self.R.create_meshes()
        self.R.setup_arduino("COM3")
        self.add_rocket_to_graph(self.R)
        #self.update_timer(550)

    def update_timer(self, framerate: int):
        self.timer = QtCore.QTimer()
        self.timer.setInterval(int(1000/framerate))
        self.timer.timeout.connect(self.update_graph)
        self.timer.start()
        
    def setup_graph(self):    
        
        # Creating and adding grids
        xgrid = gl.GLGridItem()
        ygrid = gl.GLGridItem()
        zgrid = gl.GLGridItem()
        self.graph.addItem(xgrid)
        self.graph.addItem(ygrid)
        self.graph.addItem(zgrid)
        
        # Rotate x and y grids to face the correct direction
        xgrid.rotate(90, 0, 1, 0)
        ygrid.rotate(90, 1, 0, 0)
        
        # Translate x and y grids to to form a "corner"
        xgrid.translate(-1000, 0, 0)
        ygrid.translate(0, -1000, 0)
        zgrid.translate(0, 0, -1000)

        # Set grid widths
        xgrid.setSpacing(100, 100, 0)
        ygrid.setSpacing(100, 100, 0)
        zgrid.setSpacing(100, 100, 0)

        # Set total grid size
        xgrid.setSize(2000, 2000, 0)
        ygrid.setSize(2000, 2000, 0)
        zgrid.setSize(2000, 2000, 0)

    def update_graph(self):
        # Called constantly by update_timer()
        self.R.update()

    def create_rocket(self):
        # TODO Read the data from the GUI that describes what parameters the rocket has.
        self.R.create_meshes()
        self.add_rocket(self.R)
        self.R.setup_arduino()

    def add_rocket_to_graph(self, R: Rocket):
        # Add meshes to the graph. The enumerate bit is from
        # https://stackoverflow.com/questions/3162271/get-loop-count-inside-a-python-for-loop
        for count, m in enumerate(R._mesh_models):
            print("Added mesh to graph. Total meshes: ", count + 1)
            self.graph.addItem(m)

        print("\n")

    ## GUI Methods
    def connect_gui(self):
        self.UI_browse_btn.clicked.connect(self.browse_btn)

    def browse_btn(self):
        # This creates a file dialog box so we can select a data file
        # getOpenFileName() returns the file path selected by the user AND the filter used 
        # as a tuple. In our case the filter is *.rocket but we only want the file path so we 
        # seperate them with this cool line courtesy of stack overflow.
        # https://stackoverflow.com/questions/43509220/qtwidgets-qfiledialog-getopenfilename-returns-a-tuple
        fname, filter = QFileDialog.getOpenFileName(self, 'Open file', filter="*.rocket")
        
        # Update the lineEdit beside "Browse" button on the GUI.
        self.UI_browse_LE.setText(fname)

def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())

if __name__ == '__main__':      
    main()
