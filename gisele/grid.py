from gisele.functions import *
from gisele import Steinerman, Spiderman, dijkstra


def routing(geo_df_clustered, geo_df, clusters_list, resolution,
            pop_thresh, input_sub, line_bc, sub_cost_hv, sub_cost_mv,
            full_ele):
    s()
    print("3. Grid Creation")
    s()
    total_grid = total_connection = pd.DataFrame()
    grid_resume = pd.DataFrame(index=clusters_list.index,
                               columns=['Grid Length [km]', 'Grid Cost [k€]',
                                        'Connection Length [km]',
                                        'Connection Cost [k€]',
                                        'Connection Type', 'Substation ID'])

    os.chdir(r'Input//')
    # substations = pd.read_csv(input_sub + '.csv')
    # substations.index = substations['ID'].values
    # geometry = [Point(xy) for xy in zip(substations['X'], substations['Y'])]
    # substations = gpd.GeoDataFrame(substations, geometry=geometry,
    #                                crs=geo_df.crs)

    # roads = gpd.read_file(r'roads_namanjavira.shp')
    # roads = gpd.read_file(r'roads_cavalcante.shp')
    # roads = roads[roads.geometry != None]
    # roads = roads[(roads.fclass != 'residential') & (roads.fclass != 'path') &
    #               (roads.fclass != 'footway')]
    os.chdir(r'..')
    roads = gpd.read_file('Output/Datasets/Roads/roads.shp')
    print('create points along roads')
    # todo -> insert a check: if there are not terminal nodes, it is not useful
    gdf_roads, roads_segments = create_roads(roads, geo_df)
    os.chdir(r'Output//Grids')

    for cluster_n in clusters_list.Cluster:

        gdf_cluster = geo_df_clustered[
            geo_df_clustered['Cluster'] == cluster_n]
        gdf_cluster_pop = gdf_cluster[
            gdf_cluster['Population'] >= pop_thresh]

        n_terminal_nodes = int(len(gdf_cluster_pop))

        if n_terminal_nodes > 1:

            l()
            print("Creating grid for Cluster n." + str(cluster_n) + " of "
                  + str(len(clusters_list.Cluster)))
            l()

            c_grid, c_grid_cost, c_grid_length, c_grid_points = \
                cluster_grid(geo_df, gdf_cluster_pop, resolution,
                             line_bc, n_terminal_nodes, gdf_cluster, gdf_roads,
                             roads_segments)


            # print('Assigning to the nearest 5 substations.. ')
            # assigned_substations, connecting_points = \
            #     substation_assignment(cluster_n, geo_df, c_grid_points,
            #                           substations, clusters_list)
            #
            # print('Connecting to the substation.. ')
            #
            # connection, connection_cost, connection_length, connection_type, \
            # connection_id = substation_connection(geo_df, substations,
            #                                       assigned_substations,
            #                                       connecting_points,
            #                                       c_grid_points,
            #                                       line_bc, resolution,
            #                                       sub_cost_hv, sub_cost_mv,
            #                                       gdf_roads,
            #                                       roads_segments)

            if not c_grid.empty:
                c_grid.to_file('Grid_' + str(cluster_n) + '.shp')
                total_grid = gpd.GeoDataFrame(
                    pd.concat([total_grid, c_grid], sort=True))
                print("Cluster grid created")
            #
            # if not connection.empty:
            #     connection.to_file('Connection_' + str(cluster_n) + '.shp')
            #     total_connection = gpd.GeoDataFrame(pd.concat(
            #         [total_connection, connection], sort=True))
            #
            # grid_resume.loc[cluster_n, 'Connection Type'] = connection_type
            # grid_resume.loc[cluster_n, 'Substation ID'] = connection_id
            grid_resume.loc[cluster_n, 'Grid Length [km]'] = \
                c_grid_length / 1000
            grid_resume.loc[cluster_n, 'Grid Cost [k€]'] = c_grid_cost / 1000
            # grid_resume.loc[
            #     cluster_n, 'Connection Length [km]'] = connection_length / 1000
            # grid_resume.loc[
            #     cluster_n, 'Connection Cost [k€]'] = connection_cost / 1000


        elif n_terminal_nodes == 0:

            grid_resume.at[cluster_n, 'Grid Length [km]'] = 0
            grid_resume.at[cluster_n, 'Grid Cost [k€]'] = 0
            grid_resume.at[cluster_n, 'Connection Length [km]'] = 0
            grid_resume.at[cluster_n, 'Connection Cost [k€]'] = 0

    grid_resume = clusters_list.join(grid_resume)
    if full_ele == 'yes':
        links(geo_df_clustered, geo_df, total_grid, resolution,
              line_bc, grid_resume, gdf_roads, roads_segments)
    elif full_ele == 'no':
        grid_resume.to_csv('grid_resume.csv', index=False)

    # total_connection.to_file('all_connections')
    if type(total_grid)==gpd.GeoDataFrame:
        total_grid.crs = total_connection.crs = geo_df.crs
    if not total_grid.empty:
        total_grid.to_file('all_cluster_grids')
    os.chdir(r'../..')
    return grid_resume, gdf_roads, roads_segments


def substation_assignment(cluster_n, geo_df, c_grid_points, substations,
                          clusters_list):
    substations = substations[substations['PowerAvailable']
                              > clusters_list.loc[cluster_n, 'Load [kW]']]
    substations = substations.assign(
        nearest_id=substations.apply(nearest, df=geo_df, src_column='ID',
                                     axis=1))

    sub_in_df = gpd.GeoDataFrame(crs=geo_df.crs, geometry=[])

    for i, row in substations.iterrows():
        sub_in_df = sub_in_df.append(
            geo_df[geo_df['ID'] == row['nearest_id']], sort=False)
    sub_in_df.reset_index(drop=True, inplace=True)

    grid_points = gpd.GeoDataFrame(crs=geo_df.crs, geometry=[])
    for i in np.unique(c_grid_points):
        grid_points = grid_points.append(
            geo_df[geo_df['ID'] == i], sort=False)

    dist = distance_3d(grid_points, sub_in_df, 'X', 'Y', 'Elevation')

    assigned_substations = dist.min().nsmallest(3).index.values

    connecting_points = dist.idxmin()
    connecting_points = connecting_points[
        connecting_points.index.isin(assigned_substations)].values

    assigned_substations = \
        sub_in_df[sub_in_df['ID'].isin(assigned_substations)]
    sub_ids = substations[substations['nearest_id'].isin(
        assigned_substations['ID'])].index.values
    assigned_substations = \
        assigned_substations.assign(sub_id=sub_ids)
    assigned_substations.reset_index(drop=True, inplace=True)

    print('Substation assignment complete')

    return assigned_substations, connecting_points


def cluster_grid(geo_df, gdf_cluster_pop, resolution, line_bc,
                 n_terminal_nodes, gdf_cluster, gdf_roads, roads_segments):
    c_grid = gdf_cluster_pop
    c_grid_cost = 0
    c_grid_length = 0
    c_grid_points = []

    if n_terminal_nodes < resolution / 5 and gdf_cluster.length.size < 500:

        c_grid2, c_grid_cost2, c_grid_length2, c_grid_points2 = Spiderman. \
            spider(geo_df, gdf_cluster_pop, line_bc, resolution, gdf_roads,
                   roads_segments)

        # c_grid1, c_grid_cost1, c_grid_length1, c_grid_points1 = Steinerman. \
        #     steiner_roads(geo_df, gdf_cluster_pop, line_bc, resolution,
        #                   gdf_roads, roads_segments)

        # c_grid2, c_grid_cost2, c_grid_length2, c_grid_points2 = Spiderman. \
        #     spider(geo_df, gdf_cluster_pop, line_bc, resolution, gdf_roads,
        #            roads_segments)
        #
        c_grid1, c_grid_cost1, c_grid_length1, c_grid_points1 = Steinerman. \
            steiner(geo_df, gdf_cluster_pop, line_bc, resolution)

        if c_grid_cost1 <= c_grid_cost2:
            print("Steiner algorithm has the better cost")
            c_grid = c_grid1
            c_grid_length = c_grid_length1
            c_grid_cost = c_grid_cost1
            c_grid_points = c_grid_points1

        elif c_grid_cost1 > c_grid_cost2:
            print("Spider algorithm has the better cost")
            c_grid = c_grid2
            c_grid_length = c_grid_length2
            c_grid_cost = c_grid_cost2
            c_grid_points = c_grid_points2

    else:
        print("Too many points to use Steiner, running Spider.")
        c_grid, c_grid_cost, c_grid_length, c_grid_points = Spiderman. \
            spider(geo_df, gdf_cluster_pop, line_bc, resolution, gdf_roads,
                   roads_segments)

    return c_grid, c_grid_cost, c_grid_length, c_grid_points


def substation_connection(geo_df, substations, assigned_substations,
                          connecting_point, c_grid_points, line_bc,
                          resolution, sub_cost_hv, sub_cost_mv, gdf_roads,
                          roads_segments):
    best_connection = pd.DataFrame()
    best_connection_cost = 0
    best_connection_length = 0
    best_connection_type = []
    best_connection_power = 0
    connection_id = []

    costs = np.full((1, len(assigned_substations)), 9999999)[0]
    for row in assigned_substations.iterrows():
        point = geo_df[geo_df['ID'] == connecting_point[row[0]]]
        sub = geo_df[geo_df['ID'] == row[1].ID]

        connection, connection_cost, connection_length, _ = \
            dijkstra.dijkstra_connection_roads(geo_df, sub, point,
                                               c_grid_points,
                                               line_bc, resolution, gdf_roads,
                                               roads_segments)
        #
        # connection, connection_cost, connection_length, _ = \
        #     dijkstra.dijkstra_connection(geo_df, sub, point, c_grid_points,
        #                                  line_bc, resolution)

        if substations.loc[row[1]['sub_id'], 'Exist'] == 'no':
            if substations.loc[row[1]['sub_id'], 'Type'] == 'HV':
                connection_cost = connection_cost + sub_cost_hv
            elif substations.loc[row[1]['sub_id'], 'Type'] == 'MV':
                connection_cost = connection_cost + sub_cost_mv
        costs[row[0]] = connection_cost
        connection_power = substations.loc[row[1]['sub_id'], 'PowerAvailable']
        if min(costs) == connection_cost:
            if (best_connection_cost - connection_cost) < 5000 \
                    and (best_connection_power - connection_power) > 100:
                continue
            best_connection = connection
            best_connection_cost = connection_cost
            best_connection_length = connection_length
            best_connection_type = substations.loc[row[1]['sub_id'], 'Type']
            best_connection_power = substations.loc[row[1]['sub_id'],
                                                    'PowerAvailable']
            connection_id = substations.loc[row[1]['sub_id'], 'ID']
    return best_connection, best_connection_cost, best_connection_length, \
        best_connection_type, connection_id


def links(geo_df_clustered, geo_df, all_collateral, resolution, line_bc,
          grid_resume, gdf_roads, roads_segments):
    all_link = pd.DataFrame()
    l()
    print('Connecting all the people outside the clustered area..')
    l()

    gdf_clusters_out = geo_df_clustered[geo_df_clustered['Cluster'] == -1]
    gdf_clusters_out = gdf_clusters_out[gdf_clusters_out['Population'] >= 1]

    grid_points = list(zip(all_collateral.ID1.astype(int),
                           all_collateral.ID2.astype(int)))
    all_points = line_to_points(all_collateral, geo_df)
    gdf_clusters_out = gdf_clusters_out.assign(
        nearest_id=gdf_clusters_out.apply(nearest, df=all_points,
                                          src_column='ID', axis=1))

    for row in gdf_clusters_out.iterrows():
        p1 = geo_df_clustered[geo_df_clustered['ID'] == row[1].ID]
        p2 = geo_df_clustered[geo_df_clustered['ID'] == row[1].nearest_id]

        link, link_cost, link_length, _ = \
            dijkstra.dijkstra_connection_roads(geo_df, p1, p2, grid_points,
                                               line_bc, resolution, gdf_roads,
                                               roads_segments)

        all_link = gpd.GeoDataFrame(pd.concat([all_link, link], sort=True))

    #  REMOVING DUPLICATIONS
    nodes = list(zip(all_link.ID1.astype(int), all_link.ID2.astype(int)))
    nodes = list(set(nodes))
    all_link.reset_index(drop=True, inplace=True)
    all_link_no_dup = pd.DataFrame()

    for pair in nodes:
        unique_line = all_link.loc[(all_link['ID1'] == pair[0]) & (
                all_link['ID2'] == pair[1])]
        unique_line = all_link[all_link.index ==
                               unique_line.first_valid_index()]
        all_link_no_dup = gpd.GeoDataFrame(pd.concat([all_link_no_dup,
                                                      unique_line], sort=True))

    #grid_resume.loc[
    #   0, 'Link Length [km]'] = all_link_no_dup.Length.sum() / 1000
    #grid_resume.loc[0, 'Link Cost [k€]'] = all_link_no_dup.Cost.sum() / 1000
    all_link_no_dup.crs = geo_df.crs
    all_link_no_dup.to_file('all_link')
    grid_resume.to_csv('grid_resume.csv', index=False)

    print('100% electrification achieved')

    return grid_resume
