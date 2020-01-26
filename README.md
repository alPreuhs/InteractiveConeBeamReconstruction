# Interactive Cone Beam Reconstruction

In cone beam computed tomography (CBCT) a 3D volume is reconstructed based on several 2D projections from different angles.
This application visualizes the acquisition and reconstruction process and can be used to teach the basics of flat panel CBCT reconstruction using the FDK algorithm.
It is possible to interactively change all relevant parameters and quickly see their effect on the reconstruction result.

The application is based on the project 
[Interactive Reconstruction](https://github.com/alPreuhs/InteractiveReconstruction) 
that explains fan beam CT reconstruction.

Both acqusition and reconstruction use the library 
[pyCONRAD](https://git5.cs.fau.de/PyConrad/pyCONRAD)
which is based on the Java library 
[CONRAD](https://github.com/akmaier/CONRAD).

![](https://github.com/qi55wyqu/InteractiveConeBeamReconstruction/blob/master/gui.png "")

## Setup
The voxel grid and mesh of the phantom and its rotation, translation, scale and color can be edited in the 
```config.xml```
file.

## Usage
``` bash
pythonw InteractiveConeBeamReconstruction.pyw
```

## Required Packages
* [jpype1](https://github.com/jpype-project/jpype) == 0.7
* [pyconrad](https://git5.cs.fau.de/PyConrad/pyCONRAD) >= 0.6.6
* [PyQt5](https://pypi.org/project/PyQt5/) >= 5.13.0
* [numpy](https://github.com/numpy/numpy) >= 1.16.2
* [VTK](https://pypi.org/project/vtk/) >= 8.1.2
* [qimage2ndarray](https://github.com/hmeine/qimage2ndarray) >= 1.8
* [mesh_vox](https://github.com/Septaris/mesh_vox.git) >= 0.1.0

Install using ````pip install -r requirements.txt````


## Add Translation
1. Run ````python generate_translation_files.py NameOfNewLanguage````
2. Translate using Qt Linguist
3. Run ````python generate_translation_files.py````
4. New translation will be loaded into the menu bar at startup

## Tested Environments
The app has been tested to work under the following environments:

<table>
<tr>
    <th>OS</th>
    <th>Python</th>
    <th>Java</th>
    <th>pyCONRAD</th>
</tr>
<tr>
    <td>Windows 10</td> 
    <td>3.7</td> 
    <td>Java SE 12.0.1</td>
    <td>0.6.6</td>
</tr>
<tr>
    <td>Debian 9.9</td> 
    <td>3.5</td> 
    <td>OpenJDK 8.0</td>
    <td>0.6.6</td>
</tr>
<tr>
    <td>macOS 10.15</td> 
    <td>3.7</td> 
    <td>Java SE 12.0.1</td>
    <td>0.6.6</td>
</tr>
</table>

## References
1. A. Maier, H. G. Hofmann, M. Berger, P. Fischer, C. Schwemmer, H. Wu, K. Müller, J. Hornegger, J. H. Choi, C. Riess, A. Keil, and R. Fahrig. 
[CONRAD—A Software Framework for Cone-Beam Imaging in Radiology](https://www.researchgate.net/profile/Jang_Hwan_Choi/publication/259250711_CONRAD-A_software_framework_for_cone-beam_imaging_in_radiology/links/56a22edc08ae24f62705e08b.pdf). 
Medical Physics 40(11):111914-1-8. 2013
2. G. L. Zeng. 
[Medical Image Reconstruction: A Conceptual Tutorial](https://www.springer.com/de/book/9783642053689). 
New York: Springer, 2010.
