# This takes the graph network representation of the skeleton and plots by creating tubes and spheres 

import pickle
import pyvista as pv
import numpy as np
import sys


def pyVista_visualization(dir, image, network_path):

    graph = pickle.load(open(network_path, 'rb'))

    def create_network_Multiblock(graph):

        start_points, end_points = [], []
        edge_nodes = []

        network = pv.MultiBlock()

        for node in graph.nodes():

            node_attribute = graph.nodes[node]
            start_point = [node_attribute["x_um"], node_attribute["y_um"], node_attribute["z_um"]]

            sphere = pv.Sphere(center = start_point, radius = 0.3)
            network.append(sphere)

            for connecting_node in graph.edges(node):

                node2 = connecting_node[1]
                node_attribute = graph.nodes[node2]

                end_point = [node_attribute["x_um"], node_attribute["y_um"], node_attribute["z_um"]]
                start_points.append(start_point)
                end_points.append(end_point)
                edge_nodes.append([node, node2])

        streamline_width=0.175

        all_points = np.array(start_points+end_points)

        xmin , xmax = np.min(all_points[:,0], axis = 0), np.max(all_points[:,0], axis = 0)
        ymin , ymax = np.min(all_points[:,1], axis = 0), np.max(all_points[:,1], axis = 0)
        zmin , zmax = np.min(all_points[:,2], axis = 0), np.max(all_points[:,2], axis = 0)


        for i in range(len(start_points)):
            
            tube = pv.Tube(pointa = start_points[i], pointb= end_points[i], radius=streamline_width)
            tube["angle"] = [abs(graph.edges[edge_nodes[i]]['angle_azi'])] * tube.n_points
            network.append(tube)
        
        return network,(xmin, xmax, ymin, ymax, zmin, zmax)

    
    network, bounds = create_network_Multiblock(graph)

    cube = pv.Cube(bounds = bounds)
    p = pv.Plotter(window_size=[3024 , 1964])
    p.background_color = "#FFFFFF"
    p.add_composite(network, smooth_shading=True, ambient = 0.2, diffuse= 1, specular = 0.5,  opacity = 1,  color = "orange") #map = plt.get_cmap("plasma"), scalars = "angle",)   # color = "orange")

    bounds = network.bounds
    center = network.center

    p.add_mesh(cube, style='wireframe', color='black', line_width=3)  
 
    camera_position = [
        (center[0] + 2*bounds[1] , center[1] + 2*bounds[3], center[2] +  2*bounds[5]),   # Camera postion
        (center[0], center[1], center[2]),   # Look-at point (center of the scene) 
        (0, 0, 1),   # Viewing direction (Z-axis as "up")
    ]

    p.camera_position = camera_position
    p.save_graphic(dir + f"outputs/figures/3D_view_{image}.svg") 
    p.show(interactive=True)


if __name__ == "__main__":
    dir = sys.argv[1]
    image = sys.argv[2]
    network_path = sys.argv[3]

    pyVista_visualization(dir, image, network_path)