import networkx as nx
import time
import math
from scipy import sparse
from gisele.functions import *
from gisele.Steiner_tree_code import *


def steiner(geo_df, gdf_cluster_pop, line_bc, resolution, branch_points=None):
    '''

    :param geo_df:
    :param gdf_cluster_pop:
    :param line_bc:
    :param resolution:
    :param branch_points:
    :return: c_grid: GeoDataframe with Linestrings of the lines inside the cluster
    :return: c_grid_cost: float with the cost of the grid
    :return: c_grid_length: float with length of the grid
    :return: c_grid_points: list of Points belonging to the lines

    '''

    if branch_points is None:
        branch_points = []

    print("Running the Steiner's tree algorithm..")

    start_time = time.time()

    #  creating the box around the cluster and calculating edges matrix
    df_box = create_box(gdf_cluster_pop, geo_df)
    dist_2d_matrix = distance_2d(df_box, df_box, 'X', 'Y')
    dist_3d_matrix = distance_3d(df_box, df_box, 'X', 'Y', 'Elevation')

    edges_matrix = cost_matrix(df_box, dist_3d_matrix, line_bc)
    length_limit = resolution * 1.5
    edges_matrix[dist_2d_matrix > math.ceil(length_limit)] = 0

    for i in branch_points:
        if i[0] in edges_matrix.index.values and \
                i[1] in edges_matrix.index.values:
            edges_matrix.loc[i[0], i[1]] = 0.001
            edges_matrix.loc[i[1], i[0]] = 0.001

    edges_matrix_sparse = sparse.csr_matrix(edges_matrix)
    graph = nx.from_scipy_sparse_matrix(edges_matrix_sparse)

    # taking all cluster points inside the box (terminal nodes)
    gdf_cluster_in_box = gpd.GeoDataFrame(crs=geo_df.crs, geometry=[])
    for i in gdf_cluster_pop.ID:
        point = df_box.loc[df_box['ID'] == i]
        gdf_cluster_in_box = pd.concat([gdf_cluster_in_box, point], sort=True)
    terminal_nodes = list(gdf_cluster_in_box.index)
    #check if graph is not empty
    if len(graph.edges) != 0:
        tree = steiner_tree(graph, terminal_nodes, weight='weight')
        path = list(tree.edges)

        # Creating the shapefile
        c_grid, c_grid_points = edges_to_line(path, df_box, edges_matrix)
        c_grid_cost = int(c_grid['Cost'].sum(axis=0))
        c_grid['Length'] = c_grid.length.astype(int)
        c_grid_length = c_grid['Length'].sum(axis=0)
    else:
        print('empty graph: check the resolution!')
        c_grid=gpd.GeoDataFrame(columns=[['Cost','ID1','ID2','Length','geometry']])
        c_grid_cost=0
        c_grid_length=0
        c_grid_points=[]

    final_time = time.time()
    total_time = final_time - start_time
    print("The total time required by the Steiner's tree algorithm was: "
          + str(round(total_time, 4)) + " seconds")

    return c_grid, c_grid_cost, c_grid_length, c_grid_points


def steiner_roads(geo_df, gdf_cluster_pop, line_bc, resolution, gdf_roads,
                  roads_segments, branch_points=None):

    if branch_points is None:
        branch_points = []

    print("Running the Steiner's tree algorithm..")

    start_time = time.time()

    #  creating the box around the cluster and calculating edges matrix
    df_box = create_box(gdf_cluster_pop, geo_df)
    n = df_box.shape[0]

    df_box_roads = create_box(gdf_cluster_pop, gdf_roads)
    df_box_roads.index = pd.Series(range(df_box.index.shape[0],
                                         df_box.index.shape[0] +
                                         df_box_roads.index.shape[0]))
    n_roads = df_box_roads.shape[0]
    df_box_segments = create_box(gdf_cluster_pop, roads_segments)

    df_box = df_box.append(df_box_roads)
    df_box = df_box.drop_duplicates('ID')

    dist_2d_matrix = distance_2d(df_box, df_box, 'X', 'Y')
    dist_3d_matrix = distance_3d(df_box, df_box, 'X', 'Y', 'Elevation')

    costs_matrix = cost_matrix(df_box, dist_3d_matrix, line_bc)
    edges_matrix = costs_matrix.copy()
    for i in branch_points:
        if i[0] in costs_matrix.index.values and \
                i[1] in costs_matrix.index.values:
            # reduce to zero the cost to be filtered later, but leaving
            # the distance to be considered by the routing algorithm
            costs_matrix.loc[i[0], i[1]] = 0.001
            costs_matrix.loc[i[1], i[0]] = 0.001
            edges_matrix.loc[i[0], i[1]] = dist_3d_matrix.loc[i[0], i[1]]
            edges_matrix.loc[i[1], i[0]] = dist_3d_matrix.loc[i[0], i[1]]

    length_limit = resolution * 1.5
    edges_matrix[dist_2d_matrix > math.ceil(length_limit)] = 0
    # removing connections between road points
    edges_matrix.iloc[n:n + n_roads, n:n + n_roads] = 0
    edges_matrix_sparse = sparse.csr_matrix(edges_matrix)
    graph = nx.from_scipy_sparse_matrix(edges_matrix_sparse)

    for x in range(df_box_segments.shape[0]):
        # re-add segment of the road to the graph, with weight=distance[km]
        graph.add_edge(
            df_box.index[df_box['ID'] == df_box_segments.loc[x, 'ID1']][0],
            df_box.index[df_box['ID'] == df_box_segments.loc[x, 'ID2']][0],
            weight=df_box_segments.loc[x, 'length']*line_bc)

    # taking all cluster points inside the box (terminal nodes)
    gdf_cluster_in_box = gpd.GeoDataFrame(crs=geo_df.crs, geometry=[])
    for i in gdf_cluster_pop.ID:
        point = df_box.loc[df_box['ID'] == i]
        gdf_cluster_in_box = pd.concat([gdf_cluster_in_box, point], sort=True)
    terminal_nodes = list(gdf_cluster_in_box.index)

    # df_box_roads.to_file('roads_box')
    # df_box_segments.to_file('roads_segments')

    tree = steiner_tree(graph, terminal_nodes, weight='weight')
    path = list(tree.edges)

    # Creating the shapefile
    c_grid, c_grid_points = edges_to_line(path, df_box, costs_matrix)
    c_grid_cost = int(c_grid['Cost'].sum(axis=0))
    c_grid['Length'] = c_grid.length.astype(int)
    c_grid_length = c_grid['Length'].sum(axis=0)

    final_time = time.time()
    total_time = final_time - start_time
    print("The total time required by the Steiner's tree algorithm was: "
          + str(round(total_time, 4)) + " seconds")

    return c_grid, c_grid_cost, c_grid_length, c_grid_points

