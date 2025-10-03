# ToFiE: Python framework for Fiber Topology Extraction from microscopy Images.

A workflow for topology-aware three-dimensional fiber reconstruction of biological networks from microscopy images. Supporting code for this workflow can be found in this repository. 

![image](3D_view_example_network.svg)

## Installation through terminal

### Create virtual environment with python 3.9.4.
`python3.9 -m venv ToFiE_env`

### Activate the environment in terminal.
`source ToFiE_env/bin/activate`

### Install ipykernel to use the environment as a Jupyter kernel. Select this kernel when running python scripts.
`pip install ipykernel`

`python -m ipykernel install --name "ToFiE_env"`

### Install all python modules and dependencies needed using pip.
`pip install -r <project directory>/fiber_feature_analysis/requirements.txt`


![image](workflow_only.png)


## Image Pre-processing

Gaussian blur, median filter, z- intensity correction, deconvolution, and FRC resolution is carried out in **preprocess_images.ipynb**. 
Associated functions for pre-processing are found in **denoise_contrast_enhance.py**. Deconvolution was carried out with the sdeconv Python library. Functions from the MIPLIB Python library were used for FRC resolution estimation. These functions were slightly modified, and can be found in the local folder miplibrary.
  
## Skeletonization and network graph creation

### **persistence_thresholding.ipynb**
The persistence threshold and trimbelow value was determined by plotting a histogram of the image intensities and making a persistence diagram. This is carried out in the notebook, with custom functions from the scripts: **read_skeleton, denoise_contrast_enhance, skeleton_processing**.

### **skeleton_refinement.ipynb**
The raw skeleton obtained from DisPerSe is processed in three steps in this notebook. The custom functions are found in the scripts: **read_skeleton, skeleton_processing**.

### **skeleton_to_network.ipynb**
In this notebook, we load the raw DisPerSe skeleton, process the skeleton and convert the skeleton into a NetworkX graph. The full set of topological and geometrical descriptors are computed from the graph and saved. Custom functions are found in the scripts: **read_skeleton, skeleton_processing, skeleton_network**.

## Interactive visualization with Vedo
**vedo_2d.py, vedo.py**

## 3D orientation histogram
### **fittingbivariateVonMises.m**
To fit the bivariate Von Mises distribution to the 3D orientation histogram, the code by Alberini et. al. (2024) was adapted in the Matlab script.




