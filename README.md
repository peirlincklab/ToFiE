# ToFiE: Topology-aware Fiber Extraction workflow for 3D reconstruction of biological fibrous networks

When using this work, please cite:
[preprint](https://doi.org/10.48550/arXiv.2604.18230)

~~~bibtex
@article{Togo2026,
       author = {Togo, Risa and Cardona, Sara and Nagle, Ir{\`e}ne and Koenderink, Gijsje H. and Fereidoonnezhad, Behrooz and Peirlinck, Mathias},
        title = "{ToFiE, a Topology-aware Fiber Extraction workflow for 3D reconstruction of dense and heterogeneous biological fiber networks from microscopy images}",
      journal = {arXiv e-prints},
      url = {http://dx.doi.org/10.48550/arXiv.2604.18230)},
      DOI = {10.48550/arXiv.2604.18230)},
         year = 2026,
        month = apr,
          eid = {arXiv:2604.18230},
        pages = {arXiv:2604.18230},
archivePrefix = {arXiv},
}
~~~

ToFiE is a semi-automated topology-aware fiber extraction workflow that facilitates connectivity-preserving 3D reconstructions of dense and heterogeneous collagen networks from confocal fluorescence images. ToFiE traces a skeleton based on Discrete Morse theory
(DMT) and persistent homology via DisPerse, making it more robust against noise and signal heterogeneity in experimental images. ToFiE is also generally applicable to biological fibrous networks for investigating structure-function and generating experimentally-informed microstructural templates for numerical studies. The workflow relies only on open-source algorithms and can be run completely within the Python environment.

Notice: ToFiE uses DisPerSE for one stage of the analysis pipeline. DisPerSE is not redistributed with ToFiE and must be obtained separately by users in accordance with its own licensing and installation requirements.

![image](3D_view_example_network.svg)
# ToFiE installation

ToFiE is tested with **Python 3.9.4**. Newer Python versions may fail to build `miplib`.

---

## Windows

### 1. Install the prerequisites

Open PowerShell and run:

```powershell
winget install Python.Python.3.9
winget install Oracle.JavaRuntimeEnvironment
winget install Microsoft.VisualStudio.2022.BuildTools --override "--passive --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
```

- The C++ workload (`VCTools`) is what `miplib` needs to compile. Installing "Build Tools" without it is not enough.
- Restart the terminal afterwards.

### 2. Clone the ToFiE repository and create the virtual environment

```powershell
git clone <ToFiE repo URL>
cd ToFiE
py -3.9 -m venv ToFiE_env
```

### 3. Activate the ToFiE environment

The C++ compiler is only available in the **Developer PowerShell for VS** or the Developer Command Prompt, not in the normal PowerShell. Open, `cd` into the repository, and activate the environment:

```powershell
cd path\to\ToFiE
Set-ExecutionPolicy -Scope Process Bypass     # only if activation is blocked
.\ToFiE_env\Scripts\Activate.ps1
```

You should see `(ToFiE_env)` at the start of the prompt.

### 4. Install the packages in the specific order

```powershell
python -m pip install --upgrade pip setuptools wheel
python -m pip install numpy==1.25.2
python -m pip install miplib==1.0.6 --no-build-isolation
python -m pip install -r requirements.txt
```

`numpy` has to be installed before `miplib` because `--no-build-isolation` makes `miplib` build against the numpy already in the environment.

---

## Mac

### 1. Install the prerequisites 

```bash
xcode-select --install                 # C/C++ compiler
brew install python@3.9 openjdk
```

### 2. Clone the ToFiE repository and create the virtual environment

```bash
git clone <ToFiE repo URL>
cd ToFiE
python3.9 -m venv ToFiE_env
source ToFiE_env/bin/activate
```

You should see `(ToFiE_env)` at the start of the prompt.

### 3. Install the packages in the specific order

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install numpy==1.25.2
python -m pip install miplib==1.0.6 --no-build-isolation
python -m pip install -r requirements.txt
```

---

## Sanity checks

```bash
python --version                                 # states 3.9.x
python -c "import miplib, numpy; print('ok')"    # prints 'ok'
java -version                                    # prints Java version
```

## Running scripts

1. Open a terminal in the ToFiE repository.
2. Activate the virtual environment (`.\ToFiE_env\Scripts\Activate.ps1` on Windows, `source ToFiE_env/bin/activate` on Mac).
3. Run the script, for example:

```bash
python test_scripts/run.py
```

# Workflow 
The workflow works in three steps: first it takes high resolution 3D images and performs image processing; denoising, correcting for intensity attenuation with depth, and deconvoluting using a theoretical PSF. Second, it links to the DisPerSe software (Sousbie 2011) to extract the 1-dimensional topological structure of the processed image data, in other words our fiber skeleton. Third, the filaments and junctions of the skeleton are further refined for the particular biological network of interest through several functions and converted into a graph network.

![image](workflow.png)

**Step 1. Image Pre-processing** -  
**Input:** 3d image data (.tif file format). 
To address noise in the raw image, we apply a Gaussian filter, followed by a median filter. The contrast and intensities across the z-axis (depth) of the smoothened image are standardized by re-normalizing pixel intensities falling between a specified lower and upper threshold such that their values span the complete 8-bit range, based on the method of Intensify3D (Yayon et. al. 2018). Pixel values outside the thresholds are clipped to the 8-bit range limits. The normalizing step is important to ensure the algorithm reconstructs unbiasedly at all depths, as darker fibrous structures would be considered as less persistent topological features of the network. The enhanced image stack is deconvoluted with the Gaussian point spread function (PSF) and the Richardson-Lucy deconvolution algorithm using the SDeconv python framework (Prigent et. al. 2023). The resolution of the smoothened image, estimated with the Fourier Ring Correlation (FRC) function in the MIPLIB software (Koh et al. 2019), is used as the lateral and axial size of the PSF. To enhance the contrast after deconvolution, the image stack is renormalized to the full 8-bit range as previously.

- Place your 3D image in the images folder. In the config.yaml file, set the parameters below specific for your image for image processing. For setting the upper percentile, if there are a few very bright pixels in each slice they are not representative of the brightness of the z-slice, so consider setting lower n-th percentile like 99.99. Overcorrection can appear as fluctuating slice intensities across the z-depth, while intensity attenuation with depth persists for undercorrection. Adjust the lower threshold to exclude background intensities when noticeable background signal is present. The usefulness of deconvolution depends on the imaging modality. For SHG images, deconvolution is less relevant, in that case set the number of iterations to zero.

**Step 2. Skeletonization** - Discrete Morse theory (DMT) and persistent homology form the mathematical framework for obtaining the initial skeleton of the network from the processed image. For a detailed explanation, we refer the readers to the work of Sousbie.  We use the specific implementation of DMT in the DisPerSe software to trace the fiber skeleton through the discrete 1−manifold, taking a similar approach as Merle et. al. in DISSECT. Persistent homology identifies more persistent (robust) topological features. Persistence is defined as the difference in field intensities of a topological feature in the 1-manifold, a larger difference indicating greater topological importance. DisPerSe can be run either locally (given sufficient computing resources), or using the cluster. Four parameters (−cut, −smooth, −assemble, −trimBelow) enables adjusting the 1-manifold in DisPerSe. The cut parameter sets the persistence threshold: too high of a threshold means dim fibers are not traced, and too low of a threshold result in an overtraced network. The smooth parameter controls the number of sampling points to average over to smoothen a filament. The assemble parameter defines the maximum angle for merging neighboring filaments in the skeleton. The trimBelow parameter removes topological features associated with an intensity lower than the set threshold. Unwanted cross-connections between fibers across dark regions in the image are removed with a high enough threshold. The obtained DisPerSe skeleton S is defined in filament subunits F, where each filament is described by endpoints c and sampling points s.

- Here adjust the persistence_val and trimBelow_val for your image. Adjust persistence_val according to the image contrast and noise level. If fibers are insufficiently traced, decrease the persistence threshold. If spurious structures are reconstructed, increase it. Increase the trimBelow_val if unwanted connections are reconstructed across dark regions between fibers. Avoid setting it too high, as dim but real fibers may also be removed.  Adjust the amount of smoothing according to the local curvature and irregularity of the fibers. For strongly curved fibers, a lower smoothing value can  help preserve the irregularity. Adjust the angular criterion for assembling neighboring filament segments according to the expected fiber curvature. 

 
**Step 3. Skeleton refinement** - 
A set of custom functions are applied for further refining filament subunits within the skeleton. Original filaments in the skeleton are first broken down at the branchpoints or endpoints, such that endpoints cannot be contained within the redefined filaments. This establishes a consistent base definition. Filaments shorter than a specific length threshold are merged with their neighboring filament, or removed, depending on the connectivity of the endpoints of the short filament. Neighboring filaments that share a similar orientation within an angle threshold are merged. To clean up the skeleton further, broken ends are removed, and to obtain a fully connected network dangling ends can also be removed. The processed skeleton is converted into an undirected graph with the NetworkX python library, with nodes and edges to represent the endpoints and filaments of the skeleton. 
**Output:** Reconstruction as a graph network (.pkl file format). 

- Adjust the angle_threshold according to the expected local alignment of neighboring fiber segments. Choose a threshold that allows segments belonging to the same physical fiber to be merged without incorrectly merging fibers that intersect at junctions. Adjust the length threshold (or minimum filament length) according to the characteristic length scale of the network. Short filament segments below this threshold are either merged with neighboring segments or removed, depending on their connectivity. Avoid setting the threshold too high, as short but genuine fiber segments may be lost or merged incorrectly. To retain only the network with no dangling ends, set remove_dangling_ends to True.
- Finally, compare the reconstructed skeleton against the original or preprocessed microscopy image.

## Implementation

The three steps of the ToFiE workflow can be executed either locally or on a high-performance computing (HPC) cluster, depending on the image size and computational requirements.

**Local execution:** Follow the installation instructions, activate the virtual environment, and run the Python script `run.py`. Ensure that the Docker application is running throughout the execution.

**HPC execution:** Submit the Bash script `submit_pipeline.sh` with the parameters specified in `config_run.yaml`. Depending on the resource availability and usage limits of the HPC cluster, you may need to adjust the resources requested in `step1_preprocess.sbatch`, `template_reconstruction.sh`, and `step3_postprocess.sbatch`.



