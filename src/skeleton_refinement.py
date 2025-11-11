import yaml
from pathlib import Path
from denoise_contrast_enhance import open_tif_to_numpy
from read_skeleton import load_NDskl
from skeleton_processing import SkeletonObject
from skeleton_network import skeleton_to_network 
from pyVista_visualization import pyVista_visualization
import pickle
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np



def skeleton_refinement(config_path):
        
    # Load parameters from config.yaml file
    with open(config_path) as f:
        config = yaml.safe_load(f)

    base_path = Path(config["path"])
    path_to_dir = str(base_path / config["path_to_dir"].strip("/"))  + "/"
    path_to_output = str(base_path / config["path_to_output"].strip("/"))  + "/"

    image = config["image"]
    img , metadata = open_tif_to_numpy(path_to_dir + image, crop_factor= 1)

    pixel_spacing = config["pixel_spacing"]
    angle_threshold = config["angle_threshold"]
    length_threshold = config["length_threshold"]
    remove_broken_ends = config["remove_broken_ends"]
    remove_dangling_ends = config["remove_dangling_ends"]

    persistence_val = config["persistence_val"]
    smooth_val = config["smooth_val"]
    assemble_val = config["assemble_val"]
    trimBelow_val = config["trimBelow_val"]

    raw_skeleton_file = "processed_" + image + f".fits_c{persistence_val}.up.NDskl.BRK.S{smooth_val}.ASMB.TRIM.rmB.a.NDskl"

    # Load skeleton
    skeleton = load_NDskl(path_to_output + raw_skeleton_file) 
    print(f"Skeleton loaded from: {path_to_output}{raw_skeleton_file}")

    # Refine skeleton
    skel_obj = SkeletonObject(skeleton, pixel_spacing[:2]).skeleton_processing(
        angle_threshold=angle_threshold,
        length_threshold=length_threshold
    )

    if remove_broken_ends == True:
        skel_obj = skel_obj.broken_ends()

    skel_obj = skel_obj.assemble_filaments(angle_threshold = angle_threshold)

    if remove_dangling_ends == True:
        skel_obj.dangling_ends()

    print(f"Skeleton is refined succesfully.")

    graph = skeleton_to_network(skel_obj, img, pixel_to_um = pixel_spacing[:2])
    print(f"Conversion to graph network...")

    # Save graph object to pickle file
    print("Saving...")
    network = f"refined_GN_{image}_c{persistence_val}_S{smooth_val}_as{assemble_val}_trim{trimBelow_val}_athr{str(angle_threshold)}_lthr{str(length_threshold)}.pickle"
    pickle.dump(graph, open(path_to_output + network, 'wb'))  
    print("Graph network saved to: " + path_to_output + network)

    # 2D visualization
    dic_pos = {}
    for node, attr in graph.nodes(data=True):
        dic_pos[node] = [attr['x_um'], -attr['y_um']]
    plt.figure(figsize=(6,4), dpi=300)
    nx.draw(graph, node_size = 0.75, node_color="orange", edge_color = "orange", width = 0.5, pos = dic_pos, alpha = 0.8)
    plt.imshow(np.max(img, axis = 0),  alpha = 1, cmap = "gray")
    plt.axis("off")
    plt.savefig(path_to_output + f"/figures/refined_GN_projection_{image}.png", dpi=300, pad_inches=0, bbox_inches='tight')
    plt.show(block=True)

    # 3D visualization
    pyVista_visualization(str(base_path), image, path_to_output + network )

   
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    skeleton_refinement(args.config)

