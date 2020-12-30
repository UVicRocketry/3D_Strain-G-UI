from PyQt5 import QtWidgets, uic, QtCore
import pyqtgraph.opengl as gl
import numpy as np
from pyqtgraph.opengl.items.GLGridItem import GLGridItem
from stl import mesh
import sys
import os
from serial import Serial
# pip3 install PyQT5 numpy numpy-stl pyserial pyqtgraph opengl

class Rocket():
    # List of .STL meshes
    _mesh_models = []

    # Angular positions
    _yaw = 0.0
    _pitch = 0.0
    _roll = 0.0

    _altitude = 0.0


    def __init__(self):
        print("Created Rocket!\n")
    def create_meshes(self, stl_dir: str) -> list[GLGridItem]:
        # By using the -> and : str we specify the return type and argument type
        # This makes the method harder to break because it forces the user to pass
        # the right type.
        
        # Create a list of meshes from all the STL files in the STL_files folder
        mesh_models = []

        directory = stl_dir
        for filename in os.listdir(directory):
            if filename.endswith(".STL"):
                print("Found .STL: " + filename)
                stl_model = mesh.Mesh.from_file(os.path.join(directory, filename))
                verts, I, J, K = self.stl2mesh3d(stl_model)
                faces = np.stack((I,J,K)).T
                new_mesh = gl.GLMeshItem(vertexes=verts, faces=faces, smooth=False)
                mesh_models.append(new_mesh)

        print("\n")
        return mesh_models

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

    def setup_arduino(self):
        # Stuff for reading text from arduino doing serial.println()
        try:
            serial_port = "/dev/ttyUSB0"
            baud_rate = 115200 # In arduino .ino file, Serial.begin(baud_rate)
            self.ser = Serial(serial_port, baud_rate)
        except:
            print("Could not set up serial connection with Arduino. Check the connection and try again!")

    def update(self):
        self.ser.flushInput()           # Get rid of old serial data
        line = self.ser.readline()      # Read an entire line
        line = line.strip()             # Strip \n and \r (They cause problems)
        angles = line.split(b'\t')      # Make a list, delimiting on binary tabs

        # Rotate by the difference in angle
        for m in self._mesh_models:
            m.rotate(self._yaw   - float(angles[2]), 1, 0, 0)
            m.rotate(self._pitch - float(angles[1]), 0, 1, 0)
            m.rotate(self._roll  - float(angles[0]), 0, 0, 1)

        self._yaw = float(angles[2])
        self._pitch = float(angles[1])
        self._roll = float(angles[0])

class MainWindow(QtWidgets.QMainWindow):

    # Declare our Rocket. __init__ will do the rest
    Olapitsky = Rocket()

    def __init__(self, *args, **kwargs):
        
        super(MainWindow, self).__init__(*args, **kwargs)
        # Load the UI Page. uic is the thing that lets us use a .ui file
        uic.loadUi('3D_GUI.ui', self)
        
        self.setup_graph()

        '''
        # Add Altitude grid 
        self.graph.addItem(self.alti_grid)
        self.alti_grid.setSpacing(500, 500, 0)
        self.alti_grid.setSize(2000, 2000, 0)
        self.alti_grid.translate(0, 0, 1000)
        '''
        
        # Create our meshes from the directory of STL files and setup up the rest of the Rocket
        self.Olapitsky._mesh_models = self.Olapitsky.create_meshes('STL_files')
        self.add_rocket(self.Olapitsky)
        self.Olapitsky.setup_arduino()

        # Start the timer to update the Rocket
        self.update_timer(60)

    def update_timer(self, framerate: int):
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000/framerate)
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
        self.Olapitsky.update()

    def add_rocket(self, R: Rocket) -> None:
        # Add meshes to the graph
        for m in R._mesh_models:
            print("Added mesh")
            self.graph.addItem(m)

def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())

if __name__ == '__main__':      
    main()
