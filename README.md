# 3D_Strain-G-UI
Welcome to 3D_Strain-G-UI: a 3D PyQT/PyQTGraph GUI for rocket fuselage bending analysis using strain gauges!

Originally designed for Uvic Rocketry's 10k/Xenia-1 rocket, it is a general piece of software capable of supporting any number of strain gauges, and any rocket shape.

## Basic Requirements
* python3 and pip3
* The following libraries installed using pip3
	* PyQT5
	* numpy
	* numpy-stl
	* pyserial
	* pyqtgraph
	* pyopengl
	* qdarkstyle

Additionally, if you would like to use the live mode of this software, an Arduino programmed with `MPU6050_Demp_Sketch.ino` or similar device capable of serial communication should be connected to the computer.

## Setup
First clone the respository
```
git clone https://github.com/UVicRocketry/3D_Strain-G-UI
```
Then open a terminal in the `3D_Strain-G-UI` folder and run
```
python 3D_Backend.py
```
to start the program.

## Interface Overview
Upon first launch, the following interface is shown. This shows graphs of stats such as yaw, pitch, roll, altitude, etc.

![Startup](https://github.com/UVicRocketry/3D_Strain-G-UI/blob/main/Images/Startup.png)
_Note: only some of these graphs are implemented right now_

Selecting Tab2 of the UI, the main interface is shown.

![Tab2](https://github.com/UVicRocketry/3D_Strain-G-UI/blob/main/Images/Tab2.png)

Here is where the magic happens. The upper left of the UI contains file management controls, below are playback controls, and bottom left are current rocket environmental variables.

## Selecting a Rocket
3D-Strain-G-UI allows `.rocket` configuration files to be loaded via the `Load Rocket` button. A sample rocket called `10K.rocket` is included for testing.

## Loading a Log File
CSV log files formatted as `time,yaw,pitch,roll,altitude,strain1,strain2....` can be loaded for playback using the `Load Log File` button. A sample log file called `Sample_Flight_Data.csv` is included for testing with `10K.rocket`.

## Basic Usage
Load the `10K.rocket` and `Sample_Flight_Data.csv` files into the program. This should show a model of SpaceX's starship created by Arturo R. 

![Loaded_Test_Files](https://github.com/UVicRocketry/3D_Strain-G-UI/blob/main/Images/Loaded_Test_Files.png)

Next, test the playback by pressing play button. The Starship should display strain data, altitude, etc as it reads the log file.

![Playback_Started](https://github.com/UVicRocketry/3D_Strain-G-UI/blob/main/Images/Playback_Started.png)

Click and drag on the rocket to orbit around. Zoom using the scroll wheel, and pan using scroll click. Pause playback using the play button, and reset to the initial view using the `Reset View` button.

![Orbited](https://github.com/UVicRocketry/3D_Strain-G-UI/blob/main/Images/Orbited.png)

Using the slider under the 3D view, scrub through the log file to find apogee. Adjust the framerate slider and begin playback to watch the apogee in slow motion.

![Apogee](https://github.com/UVicRocketry/3D_Strain-G-UI/blob/main/Images/Apogee.png)

Pause playback during a particularly colorful section of the logfile which indicates high strain. In the table beneath the Yaw, Pitch etc. data, select a cell to highlight the strain sensor on the rocket responsible for that data. The section of the model will glow pink when selected.

![Highlighted](https://github.com/UVicRocketry/3D_Strain-G-UI/blob/main/Images/Highlighted.png)

## Creating a Model
Since the models used by the software are `.STL`, any CAD program can be used to create them. 

Specific naming must be used for the strain sections of the following form: `foo-strain_section-n.STL` where n = 1,2,3,4... It is recommended to use linear and radial patterns to automatically number the parts according to this naming convention, however the parts can be named manually as well. Arturo's Starship Solidworks assembly is included as a reference. Other components of the assembly do not need to follow any particular naming convention. Shown below is the feature tree of the included assembly.

![Feature Tree](https://github.com/UVicRocketry/3D_Strain-G-UI/blob/main/Images/Feature_Tree.png)

To ensure that the rocket in the 3D view orbits around the center of mass, the assembly must be treated in a certain way. First, mate the CoM of the assembly to the origin of the assembly. Then, when exporting the assembly as an STL, click options, then check the box labled "Do not translate STL output data to positive space".

![STL_Options](https://github.com/UVicRocketry/3D_Strain-G-UI/blob/main/Images/STL_Export_Options.png)

## Creating a .Rocket Configuration
Configuration files can be created that specify the location of STL files, color sensitivity and other parameters. Below is the `10K.rocket` config included.

```
{
    "NAME": "Arturo's Starship",
    "STL_DIRECTORY" : "STL_Files",
    "RINGS" : 3,
    "SG_PER_RING" : 4,
    "COLOR_SENSITIVITY" : 0.02
}
```

This file can be reused as is with the `STL_DIRECTORY` changed to the relative location of the STLs desired. `RINGS` and `SG_PER_RING` are discussed in the next section.

## Ring Terminology
The software was originally written to consider the strain gauges in "rings" that are placed circumferentially at a given section of the fuselage. Multiple rings are placed at various points of the fuselage to measure strain in those areas. Later however, it was determined that this is not a limitation that need to be applied to the software, and strain gauges do not need to be organized in the fashion. The code could be easily adapted to support say strain gauges in the fins or nosecone. Regardless, the terminology stuck, so until the code is modified, this is how things are.

What this means is in configuration files, the number of rings, and number of strain gauges per ring must be specified. The included sample files contain 12 strain gauges arranged in 3 rings of 4 gauges. The `.rocket` file reflects this.

## Further Work
It would be nice to implement the rest of the graphs in Tab1. Also, removing any ring structure dependence in the code would help to simplify the code and make it more flexible. The `Rocket` class should also be split into a seperate file to make the source files smaller.
