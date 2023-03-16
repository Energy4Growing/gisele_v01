import os
import math
import networkx as nx
from shapely.geometry import Point, Polygon
from gisele.grid import *
from gisele import Steinerman


def routing(geo_df_clustered, geo_df, clusters_list, resolution,
            pop_thresh, input_sub, line_bc, limit_hv, limit_mv,
            pop_load, gdf_lr, pop_thresh_lr, line_bc_col, full_ele='no'):
    s()
    print("4. Main Branch and Collateral's")
    s()

    grid_resume = pd.DataFrame(index=clusters_list.Cluster,
                               columns=['Branch Length [km]',
                                        'Branch Cost [k€]',
                                        'Collateral Length [km]',
                                        'Collateral Cost [k€]',
                                        'Grid Length [km]', 'Grid Cost [k€]'])
    grid_resume = clusters_list.join(grid_resume)

    #  IMPORTING SUBSTATIONS
    substations = pd.read_csv(r'Input/' + input_sub + '.csv')
    geometry = [Point(xy) for xy in zip(substations['X'], substations['Y'])]
    substations = gpd.GeoDataFrame(substations, geometry=geometry,
                                   crs=geo_df.crs)
    roads = gpd.read_file(r'Output/Datasets/Roads/roads.shp')
    roads = roads[roads.geometry != None]
    # roads = roads[
    #     (roads.fclass != 'residential') & (roads.fclass != 'path') & (
    #                 roads.fclass != 'footway')]

    gdf_roads, roads_segments = create_roads(roads, geo_df)

    os.chdir(r'Output//Branches')

    grid_resume = main_branch(gdf_lr, geo_df_clustered, clusters_list,
                              resolution, pop_thresh_lr, line_bc, grid_resume,
                              gdf_roads, roads_segments, geo_df)

    grid_resume, all_collateral = collateral(geo_df_clustered, geo_df,
                                             clusters_list,
                                             resolution, pop_thresh,
                                             line_bc_col,
                                             grid_resume, pop_load, gdf_roads,
                                             roads_segments)

    if full_ele == 'yes':
        links(geo_df_clustered, geo_df, all_collateral, resolution, line_bc,
              grid_resume, gdf_roads, roads_segments)
    elif full_ele == 'no':
        grid_resume.to_csv('grid_resume.csv', index=False)
    os.chdir(r'..//..')
    return grid_resume, substations, gdf_roads, roads_segments


def main_branch(gdf_lr, geo_df_clustered, clusters_list, resolution,
                pop_thresh_lr, line_bc, grid_resume, gdf_roads, roads_segments,
                geo_df):
    all_branch = pd.DataFrame()
    for i in clusters_list.Cluster:

        gdf_cluster_only = geo_df_clustered[geo_df_clustered['Cluster'] == i]
        gdf_lr_pop = gdf_lr[gdf_lr['Cluster'] == i]

        gdf_lr_pop = gdf_lr_pop[gdf_lr_pop['Population'] >= pop_thresh_lr]

        points_to_electrify = int(len(gdf_lr_pop))
        l()
        print("Creating main branch for Cluster n." + str(i) + " of "
              + str(len(clusters_list.Cluster)))
        l()
        # lr = int(
        #     (((math.sqrt(clusters_list.Size.min())) / 3) + 1) * resolution)
        lr=resolution*3 #how much power more can the main branch supply
        if points_to_electrify > 1:
            #  cluster gdf is given instead of total gdf to force internal mb

            # branch, branch_cost, branch_length, branch_points = Steinerman. \
            #     steiner_roads(geo_df, gdf_lr_pop, line_bc,
            #             resolution, gdf_roads, roads_segments)
            if points_to_electrify < lr / 5 and gdf_cluster_only.length.size < 500:
                branch, branch_cost, branch_length, branch_points = Steinerman. \
                    steiner(gdf_cluster_only, gdf_lr_pop, line_bc, resolution)
            else:
                print('Cluster too big to use Steiner, use Spider')
                branch, branch_cost, branch_length, branch_points = Spiderman. \
                    spider(gdf_cluster_only, gdf_lr_pop, line_bc, resolution, gdf_roads,
                           roads_segments)

            print("Cluster main branch created")

            grid_resume.at[i, 'Branch Length [km]'] = branch_length / 1000
            grid_resume.at[i, 'Branch Cost [k€]'] = branch_cost / 1000
            branch.to_file("Branch_" + str(i) + '.shp')
            all_branch = gpd.GeoDataFrame(pd.concat([all_branch, branch],
                                                    sort=True))
        else:
            print('Main branch for Cluster ' + str(i) + ' not necessary')
            grid_resume.at[i, 'Branch Length [km]'] = 0
            grid_resume.at[i, 'Branch Cost [k€]'] = 0

    all_branch.crs = geo_df_clustered.crs
    if not all_branch.empty:
        all_branch.to_file('all_branch')

    return grid_resume


def collateral(geo_df_clustered, geo_df, clusters_list,
               resolution, pop_thresh, line_bc_col, grid_resume, pop_load, gdf_roads, roads_segments):

    all_connections = pd.DataFrame()
    all_collateral = pd.DataFrame()
    for i in clusters_list.Cluster:

        gdf_cluster = geo_df_clustered[geo_df_clustered['Cluster'] == i]
        gdf_clusters_pop = gdf_cluster[gdf_cluster
                                            ['Population'] >= pop_thresh]
        l()
        print("Creating collateral's for Cluster " + str(i))
        l()

        if grid_resume.loc[i, 'Branch Length [km]'] == 0:

            # col, col_cost, col_length, col_points = \
            #     Steinerman.steiner_roads(geo_df, gdf_clusters_pop, line_bc,
            #                              resolution, gdf_roads,
            #                              roads_segments)
            if gdf_clusters_pop['Population'].size < resolution / 5 and gdf_cluster.length.size < 500:
                col, col_cost, col_length, col_points = \
                    Steinerman.steiner(geo_df, gdf_clusters_pop, line_bc_col,
                                       resolution, branch_points)
            else:
                print('Cluster too big to use Steiner')
                col, col_cost, col_length, col_points = \
                    Spiderman.spider(gdf_cluster, gdf_clusters_pop, line_bc_col,
                                       resolution, gdf_roads,
                           roads_segments,branch_points)

            col['Power'] = clusters_list.loc[i, 'Load [kW]']
            col['id'] = 1

            col.to_file("Branch_" + str(i) + '.shp')
            grid_resume.loc[i, 'Collateral Length [km]'] = col_length / 1000
            grid_resume.loc[i, 'Collateral Cost [k€]'] = col_cost / 1000
            all_collateral = gpd.GeoDataFrame(pd.concat([all_collateral,
                                                         col], sort=True))
            # if not connection.empty:
            #     connection.to_file('Connection_' + str(i) + '.shp')
            #     all_connections = gpd.GeoDataFrame(pd.concat(
            #         [all_connections, connection], sort=True))
            # grid_resume.loc[i, 'Connection Type'] = connection_type
            # grid_resume.loc[i, 'Substation ID'] = connection_id
            grid_resume.loc[i, 'Grid Cost [k€]'] = \
                grid_resume.loc[i, 'Collateral Cost [k€]'] + \
                grid_resume.loc[i, 'Branch Cost [k€]']
            grid_resume.loc[i, 'Grid Length [km]'] = \
                grid_resume.loc[i, 'Collateral Length [km]'] + \
                grid_resume.loc[i, 'Branch Length [km]']


            continue

        # ----- ASSIGNING WEIGHT EQUAL TO 0 TO THE MAIN BRANCH ---------------

        branch = gpd.read_file("Branch_" + str(i) + ".shp")
        branch_points = list(zip(branch.ID1.astype(int),
                                 branch.ID2.astype(int)))

        # col, col_cost, col_length, col_points = \
        #     Steinerman.steiner_roads(geo_df, gdf_clusters_pop, line_bc_col,
        #                        resolution, gdf_roads, roads_segments,
        #                        branch_points)
        if gdf_clusters_pop[
            'Population'].size < resolution / 5 and gdf_cluster.length.size < 500:
            col, col_cost, col_length, col_points = \
                Steinerman.steiner(geo_df, gdf_clusters_pop, line_bc_col,
                                   resolution, branch_points)
        else:
            print('Cluster too big to use Steiner')
            col, col_cost, col_length, col_points = \
                Spiderman.spider(gdf_cluster, gdf_clusters_pop, line_bc_col,
                                 resolution, gdf_roads,
                                 roads_segments, branch_points)


        col = collateral_sizing(geo_df_clustered, col, pop_load)

        print('Assigning to the nearest 5 substations.. ')
        # assigned_substations, connecting_points = \
        #     substation_assignment(i, geo_df, branch_points,
        #                           substations, clusters_list)

        # assigned_substations, connecting_points = \
        #     substation_assignment(i, geo_df, branch_points, substations,
        #                           clusters_list)
        #
        # print('Connecting to the substation.. ')
        # connection, connection_cost, connection_length, connection_type, \
        #     connection_id = substation_connection(geo_df, substations,
        #                                           assigned_substations,
        #                                           connecting_points,
        #                                           branch_points,
        #                                           line_bc, resolution,
        #                                           sub_cost_hv, sub_cost_mv,
        #                                           gdf_roads, roads_segments)
        # print("Substation connection created")

        # if not connection.empty:
        #     connection.to_file('Connection_' + str(i) + '.shp')
        #     all_connections = gpd.GeoDataFrame(pd.concat(
        #         [all_connections, connection], sort=True))
        #
        # grid_resume.loc[i, 'Connection Length [km]'] = connection_length / 1000
        # grid_resume.loc[i, 'Connection Cost [k€]'] = connection_cost / 1000
        # grid_resume.loc[i, 'Connection Type'] = connection_type
        # grid_resume.loc[i, 'Substation ID'] = connection_id
        grid_resume.loc[i, 'Collateral Cost [k€]'] = col_cost / 1000
        grid_resume.loc[i, 'Collateral Length [km]'] = col_length / 1000
        grid_resume.loc[i, 'Grid Cost [k€]'] = \
            grid_resume.loc[i, 'Collateral Cost [k€]'] + \
            grid_resume.loc[i, 'Branch Cost [k€]']
        grid_resume.loc[i, 'Grid Length [km]'] = \
            grid_resume.loc[i, 'Collateral Length [km]'] + \
            grid_resume.loc[i, 'Branch Length [km]']
        if not col.empty:
            col.to_file("Collateral_" + str(i) + '.shp')
            all_collateral = gpd.GeoDataFrame(pd.concat([all_collateral, col],
                                                        sort=True))

    all_collateral.crs = all_connections.crs = geo_df.crs
    if not all_collateral.empty:
        all_collateral.to_file('all_collateral')
    # all_connections.to_file('all_connections')
    return grid_resume, all_collateral


def collateral_sizing(geo_df_clustered, col, pop_load):

    col_sized = pd.DataFrame()
    #in this way, it removes the collateral point belonging to the main branches
    col.drop(col[col['Cost'] < 100].index, inplace=True)
    col.reset_index(drop=True, inplace=True)
    count = 1
    graph = nx.Graph()
    graph.add_edges_from([*zip(list(col.ID1), list(col.ID2))])

    components = list(nx.algorithms.components.connected_components(graph))

    for i in components:
        points = np.array(list(i))
        pop_col = 0
        for j in points.astype(int):
            if j in geo_df_clustered['ID']: #road points do not belong to the geodataframe but they do not have population either
                col.loc[col['ID1'] == j, 'id'] = count
                col.loc[col['ID2'] == j, 'id'] = count
                pop_col = pop_col + geo_df_clustered[geo_df_clustered['ID'] == j].\
                    Population.values[0]
        col.loc[col['id'] == count, 'Power'] = int(pop_col) * pop_load
        count += 1

    col_sized = gpd.GeoDataFrame(pd.concat([col_sized, col], sort=True))
    col_sized.crs = geo_df_clustered.crs

    return col_sized


def reduce_resolution(input_csv, geo_df, resolution, geo_df_clustered,
                      clusters_list):

    if os.path.isfile(r'Output/Branches/' + input_csv + '_lr.csv'):
        csv_lr = pd.read_csv(r'Output/Branches/' + input_csv + '_lr.csv')
        geometry = [Point(xy) for xy in zip(csv_lr['X'], csv_lr['Y'])]
        gdf_lr = gpd.GeoDataFrame(csv_lr, geometry=geometry, crs=geo_df.crs)
        print('Lower resolution geodataframe imported')
        return gdf_lr

    print('Creating a lower resolution geodataframe..')
    min_x, min_y, max_x, max_y = geo_df.geometry.total_bounds
    for i in clusters_list.Cluster:
        size = geo_df_clustered[geo_df_clustered['Cluster'] == i].__len__()
        clusters_list.loc[i, 'Size'] = size
    lr = int((((math.sqrt(clusters_list.Size.min())) / 3) + 1) * resolution)
    length = lr
    wide = lr
    cols = list(
        range(int(np.floor(min_x - lr)), int(np.ceil(max_x + lr)), wide))
    rows = list(
        range(int(np.floor(min_y - lr)), int(np.ceil(max_y + lr)), length))
    rows.reverse()
    polygons = []
    for x in cols:
        for y in rows:
            polygons.append(Polygon(
                [(x, y), (x + wide, y), (x + wide, y - length),
                 (x, y - length)]))

    gdf_lr = gpd.GeoDataFrame({'geometry': polygons}, crs=geo_df.crs)
    for i in gdf_lr.iterrows():

        if geo_df.geometry.within(i[1][0]).any():
            inner_points = geo_df_clustered[
                geo_df_clustered.geometry.within(i[1][0])]
            gdf_lr.loc[i[0], 'Population'] = inner_points.Population.sum()
            gdf_lr.loc[i[0], 'Elevation'] = inner_points.Population.mean()
            gdf_lr.loc[i[0], 'Weight'] = inner_points.Population.mean()
            if not inner_points[inner_points.Cluster != -1].empty:
                nearest_p = shapely.ops.\
                    nearest_points(i[1][0].centroid,
                                   inner_points[inner_points.Cluster != -1]
                                   .unary_union)
                cluster = inner_points[inner_points.geometry == nearest_p[1]]
                gdf_lr.loc[i[0], 'Cluster'] = cluster.Cluster.values[0]
                gdf_lr.loc[i[0], 'ID'] = cluster.ID.values[0]
            else:
                gdf_lr.loc[i[0], 'Cluster'] = -1
        else:
            gdf_lr.loc[i[0], 'Population'] = 0
            gdf_lr.loc[i[0], 'Elevation'] = 0
            gdf_lr.loc[i[0], 'Weight'] = 0
    gdf_lr['geometry'] = gdf_lr['geometry'].centroid
    gdf_lr.dropna(subset=["Cluster"], inplace=True)
    gdf_lr['X'] = gdf_lr.geometry.x
    gdf_lr['Y'] = gdf_lr.geometry.y

    gdf_lr.to_csv(r'Output/Branches/' + input_csv + '_lr.csv', index=False)
    gdf_lr.to_file(r'Output/Branches/' + input_csv + '_lr.shp')
    print('Lower resolution geodataframe created and exported')

    return gdf_lr
