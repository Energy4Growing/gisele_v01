from gisele.functions import*
import networkx as nx
import math
from scipy import sparse


def dijkstra_connection(geo_df, connecting_point, assigned_substation,
                        c_grid_points, line_bc, resolution,branch_points=None):

    connection = gpd.GeoDataFrame()
    connection_cost = 0
    connection_length = 0
    pts = []

    dist = assigned_substation.unary_union.distance(connecting_point.
                                                    unary_union)
    if dist > 50 * resolution:
        print('Connection distance too long to use Dijkstra')
        connection_cost = 999999
        connection_length = 999999
        connection = gpd.GeoDataFrame()
        return connection, connection_cost, connection_length, pts

    df_box = create_box(pd.concat([assigned_substation, connecting_point]),
                        geo_df)
    dist_2d_matrix = distance_2d(df_box, df_box, 'X', 'Y')
    dist_3d_matrix = distance_3d(df_box, df_box, 'X', 'Y', 'Elevation')

    if np.any(dist_2d_matrix):

        edges_matrix = cost_matrix(df_box, dist_3d_matrix, line_bc)
        length_limit = resolution * 1.5
        edges_matrix[dist_2d_matrix > math.ceil(length_limit)] = 0

        #  reduces the weights of edges already present in the cluster grid
        for i in c_grid_points:
            if i[0] in edges_matrix.index.values and \
                    i[1] in edges_matrix.index.values:
                edges_matrix.loc[i[0], i[1]] = 0.001
                edges_matrix.loc[i[1], i[0]] = 0.001
        for i in branch_points:
            if i[0] in edges_matrix.index.values and \
                    i[1] in edges_matrix.index.values:
                edges_matrix.loc[i[0], i[1]] = 0.001
                edges_matrix.loc[i[1], i[0]] = 0.001

        edges_matrix_sparse = sparse.csr_matrix(edges_matrix)
        graph = nx.from_scipy_sparse_matrix(edges_matrix_sparse)
        source = df_box.loc[df_box['ID'] == int(assigned_substation['ID']), :]
        source = int(source.index.values)
        target = df_box.loc[df_box['ID'] == int(connecting_point['ID']), :]
        target = int(target.index.values)

        if nx.is_connected(graph):
            path = nx.dijkstra_path(graph, source, target, weight='weight')
        else:
            connection = pd.DataFrame()
            connection_cost = 999999
            connection_length = 999999
            return connection, connection_cost, connection_length, pts

        steps = len(path)
        new_path = []
        for i in range(0, steps - 1):
            new_path.append(path[i + 1])

        path = list(zip(path, new_path))

        # Creating the shapefile

        connection, pts = edges_to_line(path, df_box, edges_matrix)

        connection['Length'] = connection.length.astype(int)
        connection_cost = int(connection['Cost'].sum(axis=0))
        connection_length = connection['Length'].sum(axis=0)

    return connection, connection_cost, connection_length, pts


def dijkstra_connection_roads(geo_df, connecting_point, assigned_substation,
                              c_grid_points, line_bc, resolution, gdf_roads,
                              roads_segments,branch_points=None):

    connection = gpd.GeoDataFrame()
    connection_cost = 0
    connection_length = 0
    pts = []

    dist = assigned_substation.unary_union.distance(connecting_point.
                                                    unary_union)
    if dist > 50 * resolution:
        print('Connection distance too long to use Dijkstra')
        connection_cost = 999999
        connection_length = 999999
        connection = gpd.GeoDataFrame()
        return connection, connection_cost, connection_length, pts

    df_box = create_box(pd.concat([assigned_substation, connecting_point]),
                        geo_df)
    n = df_box.shape[0]

    df_box_roads = create_box(pd.concat([assigned_substation,
                                         connecting_point]), gdf_roads)
    df_box_roads.index = pd.Series(range(df_box.index.shape[0],
                                         df_box.index.shape[0] +
                                         df_box_roads.index.shape[0]))
    n_roads = df_box_roads.shape[0]
    df_box_segments = create_box(pd.concat([assigned_substation,
                                            connecting_point]), roads_segments)

    df_box = df_box.append(df_box_roads)
    df_box = df_box.drop_duplicates('ID')

    dist_2d_matrix = distance_2d(df_box, df_box, 'X', 'Y')
    dist_3d_matrix = distance_3d(df_box, df_box, 'X', 'Y', 'Elevation')
    if branch_points!=None:
        for i in branch_points:
            for j, row in df_box_segments.iterrows():
                if i[0] == row.ID1 and i[1] == row.ID2:
                    df_box_segments.loc[j,'length'] = 0.001
                elif i[0] == row.ID2 and i[1] == row.ID1:
                    df_box_segments.loc[j,'length'] = 0.001

    if np.any(dist_2d_matrix):

        costs_matrix = cost_matrix(df_box, dist_3d_matrix, line_bc)
        edges_matrix = costs_matrix.copy()
        #  reduces the weights of edges already present in the cluster grid
        for i in c_grid_points:
            if i[0] in costs_matrix.index.values and \
                    i[1] in costs_matrix.index.values:
                # reduce to zero the cost to be filtered later, but leaving
                # the distance to be considered by the routing algorithm
                costs_matrix.loc[i[0], i[1]] = 0.001
                costs_matrix.loc[i[1], i[0]] = 0.001
                edges_matrix.loc[i[0], i[1]] = dist_3d_matrix.loc[i[0], i[1]]
                edges_matrix.loc[i[1], i[0]] = dist_3d_matrix.loc[i[0], i[1]]
        if branch_points != None:
            for i in branch_points:
                if i[0] in edges_matrix.index.values and \
                        i[1] in edges_matrix.index.values:
                    edges_matrix.loc[i[0], i[1]] = 0.001
                    edges_matrix.loc[i[1], i[0]] = 0.001
                    costs_matrix.loc[i[0], i[1]] = 0.001
                    costs_matrix.loc[i[1], i[0]] = 0.001

        length_limit = resolution * 1.5
        edges_matrix[dist_2d_matrix > math.ceil(length_limit)] = 0
        edges_matrix.iloc[n:n + n_roads, n:n + n_roads] = 0

        edges_matrix_sparse = sparse.csr_matrix(edges_matrix)
        graph = nx.from_scipy_sparse_matrix(edges_matrix_sparse)
        for x in range(df_box_segments.shape[0]):
            # re-add segment of the road to the graph, with weight=distance[km]
            graph.add_edge(
                df_box.index[df_box['ID'] == int(df_box_segments.loc[x, 'ID1'])][0],
                df_box.index[df_box['ID'] == int(df_box_segments.loc[x, 'ID2'])][0],
                weight=df_box_segments.loc[x, 'length']*line_bc)

        source = df_box.loc[df_box['ID'] == int(assigned_substation['ID']), :]
        source = int(source.index.values)
        target = df_box.loc[df_box['ID'] == int(connecting_point['ID']), :]
        target = int(target.index.values)

        if nx.is_connected(graph):
            path = nx.dijkstra_path(graph, source, target, weight='weight')
        else:
            # se grafo non è connesso tolgo le parti del grafo che non contengono source e target
            #potrebbero essere nodi delle strade tagliati e rimasti dentro
            for component in list(nx.connected_components(graph)):
                if source not in component or target not in component:
                    for node in component:
                        graph.remove_node(node)
            if nx.is_empty(graph): #possibile che in questo modo grafo venga svuotato totalmente,
                # aggiungo questo pezzo per evitare errori
                connection = pd.DataFrame()
                connection_cost = 999999
                connection_length = 999999
                return connection, connection_cost, connection_length, pts
            elif nx.is_connected(graph):
                path = nx.dijkstra_path(graph, source, target, weight='weight')
            else:
                connection = pd.DataFrame()
                connection_cost = 999999
                connection_length = 999999
                return connection, connection_cost, connection_length, pts

        steps = len(path)
        new_path = []
        for i in range(0, steps-1):
            new_path.append(path[i+1])

        path = list(zip(path, new_path))

        # Creating the shapefile

        connection, pts = edges_to_line(path, df_box, costs_matrix)

        connection['Length'] = connection.length.astype(int)
        connection_cost = int(connection['Cost'].sum(axis=0))
        connection_length = connection['Length'].sum(axis=0)

    return connection, connection_cost, connection_length, pts
