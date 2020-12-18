from typing import get_type_hints
from PyQt5 import QtWidgets, uic, QtCore
import pyqtgraph.opengl as gl
import numpy as np
from pyqtgraph.opengl.items.GLGridItem import GLGridItem
from stl import mesh
import sys
import os
from serial import Serial

# Print extra information to the terminal during operation when True
VERBOSE = False

class Rocket():
    _altitude = 0.0
    
    # List of GLMeshItems created from .STLs
    _mesh_models = []
    
    # Angular positions of rocket
    _yaw = 0.0
    _pitch = 0.0
    _roll = 0.0

    def __init__(self, stl_dir, graph):
        self.create_meshes(stl_dir)
        for m in self._mesh_models:
            MainWindow.addItem(m)


    # Given a directory of .STL files, returns a list of GLMeshItems
    def create_meshes(self, directory):
        # Create a list of meshes from all the STL files in the specified directory
        mesh_list = []
        
        for filename in os.listdir(directory):
            if filename.endswith(".STL"):
                if(VERBOSE):
                    print("Found model: " + filename)
                
                stl_model = mesh.Mesh.from_file(os.path.join(directory, filename))
                verts, I, J, K = self.stl2mesh3d(stl_model)
                faces = np.stack((I,J,K)).T
                new_mesh = gl.GLMeshItem(vertexes=verts, faces=faces, smooth=False)
                mesh_list.append(new_mesh)

        return mesh_list

    # Spooky magic that helps convert .STL files into GLMeshItems
    def stl2mesh3d(self, stl_mesh):
        # Taken from https://chart-studio.plotly.com/~empet/15434.embed
        
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

    # Rotate the model by the specifed number of degrees
    def rotate_by(self, d_yaw, d_pitch, d_roll):
        
        for m in self.mesh_models:
            m.rotate(d_yaw, 1, 0, 0)    # x axis
            m.rotate(d_pitch, 0, 1, 0)  # y axis
            m.rotate(d_roll, 0, 0, 1)   # z axis
        
        self._yaw   += d_yaw
        self._pitch += d_pitch
        self._roll  += d_roll

    # Rotate the model to the specified angle in degrees
    def set_rotation(self, yaw, pitch, roll):
        self.rotate_by(yaw - self._yaw, pitch - self._pitch, roll - self._roll)


class MainWindow(QtWidgets.QMainWindow):
    r = Rocket()
    # Parabola function
    x = 0

    alti_grid = GLGridItem()
    alti_grid_height = 0.0
    height = 0.0
    altimeter_reading = 0.0

    def __init__(self, *args, **kwargs):
        
        super(MainWindow, self).__init__(*args, **kwargs)
        # Load the UI Page. uic is the thing that lets us use a .ui file
        uic.loadUi('Basic_Plot.ui', self)
        
        self.setup_graph()
        self.start_timer()
        self.setup_arduino()

        # Add Altitude grid 
        self.graph.addItem(self.alti_grid)
        self.alti_grid.setSpacing(100, 100, 0)
        self.alti_grid.setSize(2000, 2000, 0)
        self.alti_grid.translate(0, 0, 1000)

    def start_timer(self):
        self.timer = QtCore.QTimer()
        self.timer.setInterval(10)
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
        self.ser.flushInput()           # Get rid of old serial data
        line = self.ser.readline()      # Read an entire line
        line = line.strip()             # Strip \n and \r
        angles = line.split(b'\t')      # Make list, delimiting on binary tabs

        self.altitude_grids()
        self.altimeter_reading = self.get_altimeter()
        self.x += 0.1

        # Rotate rocket
        self.HYAK.set_rotation(angles[0], angles[1], angles[2])

    def setup_arduino(self):
        # Stuff for reading arduino serial.println()
        try:
            serial_port = "COM3"
            baud_rate = 115200; # In arduino .ino file, Serial.begin(baud_rate)
            self.ser = Serial(serial_port, baud_rate)
        except:
            print("Could not set up serial connection with Arduino. Check the connection and try again!")

    def altitude_grids(self):
        
        # Positive value when the rocket is going up
        dz = self.altimeter_reading - self.height

        # Grid is too "high" (low). Move it to the top
        if(self.alti_grid_height > 2000):
            self.alti_grid.translate(0, 0, 2000)
            self.alti_grid_height = 0
        # Grid is too "low" (high). Move it to the bottom
        elif(self.alti_grid_height < 0):
            self.alti_grid.translate(0, 0, -2000)
            self.alti_grid_height = 2000

        self.alti_grid.translate(0, 0, -dz)
        self.height += dz
        self.alti_grid_height += dz

    def get_altimeter(self):
        return 16328 - pow(self.x - 128,2)

def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())

if __name__ == '__main__':      
    main()
