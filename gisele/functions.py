"""
GIS For Electrification (GISEle)
Developed by the Energy Department of Politecnico di Milano
Supporting Code

Group of supporting functions used inside all the process of GISEle algorithm
"""
#test comment
import os
import requests
import pandas as pd
import geopandas as gpd
import numpy as np
import json
import shapely.ops
import iso8601
from scipy.spatial import distance_matrix
from scipy.spatial.distance import cdist
from shapely.geometry import Point, box, LineString, MultiPoint
from shapely.ops import split
from gisele.michele.michele import start
from gisele.data_import import import_pv_data, import_wind_data


def l():
    """Print long separating lines."""
    print('-' * 100)


def s():
    """Print short separating lines."""
    print("-" * 40)


def nearest(row, df, src_column=None):
    """
    Find the nearest point and return the value from specified column.
    :param row: Iterative row of the first dataframe
    :param df: Second dataframe to be found the nearest value
    :param src_column: Column of the second dataframe that will be returned
    :return value: Value of the desired src_column of the second dataframe
    """

    # Find the geometry that is closest
    nearest_p = df['geometry'] == shapely.ops.nearest_points(row['geometry'],
                                                             df.unary_union)[1]
    # Get the corresponding value from df2 (matching is based on the geometry)
    value = df.loc[nearest_p, src_column].values[0]
    return value


def distance_2d(df1, df2, x, y):
    """
    Find the 2D distance matrix between two datasets of points.
    :param df1: first point dataframe
    :param df2: second point dataframe
    :param x: column representing the x coordinates (longitude)
    :param y: column representing the y coordinates (latitude)
    :return value: 2D Distance matrix between df1 and df2
    """

    d1_coordinates = {'x': df1[x], 'y': df1[y]}
    df1_loc = pd.DataFrame(data=d1_coordinates)
    df1_loc.index = df1['ID']

    d2_coordinates = {'x': df2[x], 'y': df2[y]}
    df2_loc = pd.DataFrame(data=d2_coordinates)
    df2_loc.index = df2['ID']

    value = distance_matrix(df1_loc, df2_loc)
    return value


def distance_3d(df1, df2, x, y, z):
    """
    Find the 3D euclidean distance matrix between two datasets of points.
    :param df1: first point dataframe
    :param df2: second point dataframe
    :param x: column representing the x coordinates (longitude)
    :param y: column representing the y coordinates (latitude)
    :param z: column representing the z coordinates (Elevation)
    :return value: 3D Distance matrix between df1 and df2
    """

    d1_coordinates = {'x': df1[x], 'y': df1[y], 'z': df1[z]}
    df1_loc = pd.DataFrame(data=d1_coordinates)
    df1_loc.index = df1['ID']

    d2_coordinates = {'x': df2[x], 'y': df2[y], 'z': df2[z]}
    df2_loc = pd.DataFrame(data=d2_coordinates)
    df2_loc.index = df2['ID']

    value = pd.DataFrame(cdist(df1_loc.values, df2_loc.values, 'euclidean'),
                         index=df1_loc.index, columns=df2_loc.index)
    return value


def cost_matrix(gdf, dist_3d_matrix, line_bc):
    """
    Creates the cost matrix in €/km by finding the average weight between
    two points and then multiplying by the distance and the line base cost.
    :param gdf: Geodataframe being analyzed
    :param dist_3d_matrix: 3D distance matrix of all points [meters]
    :param line_bc: line base cost for line deployment [€/km]
    :return value: Cost matrix of all the points present in the gdf [€]
    """
    # Altitude distance in meters
    weight = gdf['Weight'].values
    n = gdf['X'].size
    weight_columns = np.repeat(weight[:, np.newaxis], n, 1)
    weight_rows = np.repeat(weight[np.newaxis, :], n, 0)
    total_weight = (weight_columns + weight_rows) / 2

    # 3D distance
    value = (dist_3d_matrix * total_weight) * line_bc / 1000

    return value


def line_to_points(line, df):
    """
    Finds all the points of a linestring geodataframe correspondent to a
    point geodataframe.
    :param line: Linestring geodataframe being analyzed
    :param df: Point geodataframe where the linestring nodes will be referenced
    :return nodes_in_df: Point geodataframe containing all nodes of linestring
    """
    nodes = list(line.ID1.astype(int)) + list(line.ID2.astype(int))
    nodes = list(dict.fromkeys(nodes))
    nodes_in_df = gpd.GeoDataFrame(crs=df.crs, geometry=[])
    for i in nodes:
        nodes_in_df = nodes_in_df.append(df[df['ID'] == i], sort=False)
    nodes_in_df.reset_index(drop=True, inplace=True)

    return nodes_in_df


def create_roads(gdf_roads, geo_df):
    '''
    Creates two geodataframes
    :param gdf_roads: geodataframe with all roads in the area, as imported from OSM
    :param geo_df: geodataframe with the grid of points
    :return:line_gdf: point geodataframe containing verteces of the roads (in all the area)
            segments: geodataframe containing all the roads segments (in all the area)
    the GeoDataframes are also saves as shapefiles

    '''
    w = geo_df.shape[0]
    line_vertices = pd.DataFrame(
        index=pd.Series(range(w, w + len(gdf_roads.index))),
        columns=['ID', 'X', 'Y', 'ID_line', 'Weight', 'Elevation'], dtype=int)
    # create geodataframe with all the segments that compose the road
    segments = gpd.GeoDataFrame(columns=['geometry', 'ID1', 'ID2'])
    k = 0

    x = 0
    for i, row in gdf_roads.iterrows():
        for j in list(row['geometry'].coords):
            line_vertices.loc[w, 'X'] = j[0]
            line_vertices.loc[w, 'Y'] = j[1]
            line_vertices.loc[w, 'ID_line'] = k
            line_vertices.loc[w, 'ID'] = w
            line_vertices.loc[w, 'Weight'] = 1
            w = w + 1
        k = k + 1
        points_to_split = MultiPoint(
            [Point(x, y) for x, y in row['geometry'].coords[1:]])
        splitted = split(row['geometry'], points_to_split)
        for j in splitted:
            segments.loc[x, 'geometry'] = j
            segments.loc[x, 'length'] = segments.loc[
                                            x, 'geometry'].length / 1000
            segments.loc[x, 'ID1'] = line_vertices[
                (line_vertices['X'] == j.coords[0][0]) & (
                        line_vertices['Y'] == j.coords[0][1])][
                'ID'].values[0]
            segments.loc[x, 'ID2'] = line_vertices[
                (line_vertices['X'] == j.coords[1][0]) & (
                        line_vertices['Y'] == j.coords[1][1])][
                'ID'].values[0]
            x = x + 1
    line_vertices.loc[:, 'Elevation'] = geo_df.Elevation.mean()
    # line_vertices.loc[:, 'Elevation'] = 300
    geometry = [Point(xy) for xy in
                zip(line_vertices['X'], line_vertices['Y'])]
    line_gdf = gpd.GeoDataFrame(line_vertices, crs=geo_df.crs,
                                geometry=geometry)
    line_gdf.to_file('Output/Datasets/Roads/gdf_roads.shp')
    segments.to_file('Output/Datasets/Roads/roads_segments.shp')
    return line_gdf, segments


def create_box(limits, df):
    """
    Creates a delimiting box around a geodataframe.
    :param limits: Linestring geodataframe being analyzed
    :param df: Point geodataframe to be delimited
    :return df_box: All points of df that are inside the delimited box
    """
    x_min = min(limits.X)
    x_max = max(limits.X)
    y_min = min(limits.Y)
    y_max = max(limits.Y)

    dist = Point(x_min, y_min).distance(Point(x_max, y_max))
    if dist < 5000:
        extension = dist
    elif dist < 15000:
        extension = dist * 0.6
    else:
        extension = dist / 4

    bubble = box(minx=x_min - extension, maxx=x_max + extension,
                 miny=y_min - extension, maxy=y_max + extension)
    df_box = df[df.within(bubble)]
    df_box.index = pd.Series(range(0, len(df_box.index)))

    return df_box


def edges_to_line(path, df, edges_matrix):
    """
    Transforms a list of NetworkX graph edges into a linestring geodataframe
    based on a input point geodataframe
    :param path: NetworkX graph edges sequence
    :param df: Point geodataframe to be used as reference
    :param edges_matrix: Matrix containing the cost to connect a pair of points
    :return line: Linestring geodataframe containing point IDs and its cost
    :return line_points: All points of df that are part of the linestring
    """
    steps = len(path)
    line = gpd.GeoDataFrame(index=range(0, steps),
                            columns=['ID1', 'ID2', 'Cost', 'geometry'],
                            crs=df.crs)
    line_points = []
    for h in range(0, steps):
        line.at[h, 'geometry'] = LineString(
            [(df.loc[path[h][0], 'X'],
              df.loc[path[h][0], 'Y']),
             (df.loc[path[h][1], 'X'],
              df.loc[path[h][1], 'Y'])])

        # int here is necessary to use the command .to_file
        line.at[h, 'ID1'] = int(df.loc[path[h][0], 'ID'])
        line.at[h, 'ID2'] = int(df.loc[path[h][1], 'ID'])
        line.at[h, 'Cost'] = int(edges_matrix.loc[df.loc[path[h][0], 'ID'],
                                                  df.loc[path[h][1], 'ID']])
        line_points.append(list(df.loc[path[h], 'ID']))
    line.drop(line[line['Cost'] == 0].index, inplace=True)
    line.Cost = line.Cost.astype(int)
    return line, line_points


def load(clusters_list, grid_lifetime, input_profile):
    """
    Reads the input daily load profile from the input csv. Reads the number of
    years of the project and the demand growth from the data.json file of
    Micehele. Then it multiplies the load profile by the Clusters' peak load
    and append values to create yearly profile composed of n representative
    days.
    :param grid_lifetime: Number of years the grid will operate
    :param clusters_list: List of clusters ID numbers
    :return load_profile: Cluster load profile for the whole period
    :return years: Number of years the microgrid will operate
    :return total_energy: Energy provided by the grid in its lifetime [kWh]
    """
    print("5. Microgrid Sizing")
    print(os.getcwd())
    with open('gisele/michele/Inputs/data.json') as f:
        input_michele = json.load(f)
    os.chdir(r'Input//')
    print("Creating load profile for each cluster..")
    daily_profile = pd.DataFrame(index=range(1, 25),
                                 columns=clusters_list.Cluster)
    for column in daily_profile:
        daily_profile.loc[:, column] = \
            (input_profile.loc[:, 'Hourly Factor']
             * float(clusters_list.loc[column, 'Load [kW]'])).values
    rep_days = input_michele['num_days']
    grid_energy = daily_profile.append([daily_profile] * 364,
                                       ignore_index=True)
    #  append 11 times since we are using 12 representative days in a year
    load_profile = daily_profile.append([daily_profile] * (rep_days - 1),
                                        ignore_index=True)

    years=input_michele['num_years']
    demand_growth=input_michele['demand_growth']
    daily_profile_new = daily_profile
    #  appending for all the years considering demand growth
    for i in range(grid_lifetime - 1):
        daily_profile_new = daily_profile_new.multiply(1 + demand_growth)
        if i < (years - 1):
            load_profile = load_profile.append([daily_profile_new] * rep_days,
                                               ignore_index=True)
        grid_energy = grid_energy.append([daily_profile_new] * 365,
                                         ignore_index=True)
    total_energy = pd.DataFrame(index=clusters_list.Cluster,
                                columns=['Energy'])
    for cluster in clusters_list.Cluster:
        total_energy.loc[cluster, 'Energy'] = \
            grid_energy.loc[:, cluster].sum().round(2)
    os.chdir('..')
    print("Load profile created")
    total_energy.to_csv(r'Output/Microgrids/Grid_energy.csv')
    return load_profile, years, total_energy


def shift_timezone(df, shift):
    """
    Move the values of a dataframe with DateTimeIndex to another UTC zone,
    adding or removing hours.
    :param df: Dataframe to be analyzed
    :param shift: Amount of hours to be shifted
    :return df: Input dataframe with values shifted in time
    """
    if shift > 0:
        add_hours = df.tail(shift)
        df = pd.concat([add_hours, df], ignore_index=True)
        df.drop(df.tail(shift).index, inplace=True)
    elif shift < 0:
        remove_hours = df.head(abs(shift))
        df = pd.concat([df, remove_hours], ignore_index=True)
        df.drop(df.head(abs(shift)).index, inplace=True)
    return df


def sizing(load_profile, clusters_list, geo_df_clustered, wt, years,rivers,hydro_turbines,crs,line_base_cost):
    """
    Imports the solar and wind production from the RenewablesNinja api and then
    Runs the optimization algorithm MicHEle to find the best microgrid
    configuration for each Cluster.
    :param load_profile: Load profile of all clusters during all years
    :param clusters_list: List of clusters ID numbers
    :param geo_df_clustered: Point geodataframe with Cluster identification
    :param wt: Wind turbine model used for computing the wind velocity
    :param years: Number of years the microgrid will operate (project lifetime)
    :return mg: Dataframe containing the information of the Clusters' microgrid
    """



    geo_df_clustered = geo_df_clustered.to_crs(4326)
    mg = pd.DataFrame(index=clusters_list.index,
                      columns=['PV [kW]', 'Wind [kW]','Hydro [kW]', 'Diesel [kW]',
                               'BESS [kWh]', 'Inverter [kW]',
                               'Investment Cost [k€]', 'OM Cost [k€]',
                               'Replace Cost [k€]', 'Total Cost [k€]',
                               'Energy Produced [MWh]',
                               'Energy Demand [MWh]', 'LCOE [€/kWh]'],
                      dtype=float)

    # save useful values from michele input data
    with open('gisele/michele/Inputs/data.json') as f:
        input_michele = json.load(f)
    proj_lifetime = input_michele['num_years']
    num_typ_days = input_michele['num_days']

    max_dist_ht = input_michele['max_ht_dist']


    # exclude rivers that are too big or too small for putting mini hydro
    if not rivers.empty:
        rivers_filtered = rivers.loc[
             (rivers['P [kW]'] < input_michele['max_ht_power']) & (rivers['P [kW]'] > input_michele['min_ht_power'])

             & (rivers['annual_disch'] < input_michele['max_flow_rate']), :]


    for cluster_n in clusters_list['Cluster'].astype(int):
        l()
        print('Creating the optimal Microgrid for Cluster ' + str(cluster_n))
        l()
        try: # in some cases it is reading them as strings
            load_profile_cluster = load_profile.loc[:, cluster_n]
        except:
            load_profile_cluster = load_profile.loc[:, str(cluster_n)]
        lat = geo_df_clustered[geo_df_clustered['Cluster']
                               == cluster_n].geometry.y.values[0]
        lon = geo_df_clustered[geo_df_clustered['Cluster']
                               == cluster_n].geometry.x.values[0]
        all_angles = pd.read_csv('Input/TiltAngles.csv')
        tilt_angle = abs(all_angles.loc[abs(all_angles['lat'] - lat).idxmin(),
                                        'opt_tilt'])
        pv_prod = import_pv_data(lat, lon, tilt_angle)
        wt_prod = import_wind_data(lat, lon, wt)
        utc = pv_prod.local_time[0]
        if type(utc) is pd.Timestamp:
            time_shift = utc.hour
        else:
            utc = iso8601.parse_date(utc)
            time_shift = int(utc.tzinfo.tzname(utc).split(':')[0])
        # pv_avg = pv_prod.groupby([pv_prod.index.month,
        #                           pv_prod.index.hour]).mean()
        # pv_avg = pv_avg.append([pv_avg] * (years - 1), ignore_index=True)
        div_round = 8760 // (num_typ_days * 24)
        length = num_typ_days * 24
        new_length = length * div_round
        # pv_avg = pv_prod.groupby([pv_prod.index.month,
        #                           pv_prod.index.hour]).mean()

        pv_avg_new = np.zeros(24 * num_typ_days)
        pv_avg = pv_prod.values[0:new_length, 1].reshape(24,
                                                         div_round * num_typ_days,
                                                         order='F')
        wt_avg_new = np.zeros(24 * num_typ_days)
        wt_avg = wt_prod.values[0:new_length].reshape(24,
                                                      div_round * num_typ_days,
                                                      order='F')
        for i in range(num_typ_days):
            pv_avg_new[i * 24:(i + 1) * 24] = pv_avg[:,
                                              div_round * i:div_round * (
                                                          i + 1)].mean(axis=1)

            wt_avg_new[i * 24:(i + 1) * 24] = wt_avg[:,
                                              div_round * i:div_round * (
                                                      i + 1)].mean(axis=1)

        pv_avg = pd.DataFrame(pv_avg_new)
        pv_avg = pv_avg.append([pv_avg] * (proj_lifetime - 1),
                               ignore_index=True)

        pv_avg.reset_index(drop=True, inplace=True)
        pv_avg = shift_timezone(pv_avg, time_shift)

        # wt_prod = import_wind_data(lat, lon, wt)
        # wt_avg = wt_prod.groupby([wt_prod.index.month,
        #                           wt_prod.index.hour]).mean()
        # wt_avg = wt_avg.append([wt_avg] * (years - 1), ignore_index=True)
        wt_avg = pd.DataFrame(wt_avg_new)
        wt_avg = wt_avg.append([wt_avg] * (proj_lifetime - 1),
                               ignore_index=True)
        wt_avg.reset_index(drop=True, inplace=True)
        wt_avg = shift_timezone(wt_avg, time_shift)
        if rivers.empty and hydro_turbines.empty:
            ht_avg = wt_avg #fake number just so that the code can work without too many if/else clauses
            input_michele['ht_max_units'][str(i + 1)] = 0
        else:
            if os.path.exists('Output\Grids\Grid_' + str(cluster_n) + '.shp'):

                grid = gpd.read_file('Output\Grids\Grid_' + str(cluster_n) + '.shp')

                buffer = grid.geometry.buffer(max_dist_ht).unary_union
            elif os.path.exists('Output\Branches\Branch_' + str(cluster_n) + '.shp') or \
                os.path.exists('Output\Branches\Collateral_' + str(cluster_n) + '.shp'):

                try:
                    Branches = gpd.read_file('Output\Branches\Branch_' + str(cluster_n) + '.shp')
                    try:
                        Collaterals = gpd.read_file('Output\Branches\Colleteral_' + str(cluster_n) + '.shp')
                    except:
                        Collaterals = gpd.GeoDataFrame()
                except:
                    Branches = gpd.GeoDataFrame()
                    Collaterals = gpd.read_file('Output\Branches\Colleteral_' + str(cluster_n) + '.shp')

                grid = Branches.append(Collaterals)
                buffer = grid.geometry.buffer(max_dist_ht).unary_union
            else:
                buffer = geo_df_clustered[geo_df_clustered['Cluster']==cluster_n].buffer(max_dist_ht).unary_union
                grid = gpd.GeoDataFrame()

            rivers_inters = rivers_filtered[rivers_filtered.intersects(buffer)]

            rivers_inters.sort_values('P [kW]', inplace=True, ascending=False)

            flow_rate = rivers_inters[['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']]

            days_rounded = int(np.floor(12 / num_typ_days))

            num_rivers = len(rivers_inters['P [kW]'])

            rivers_inters.reset_index(inplace=True)
            if not grid.empty:
                grid_cluster = line_to_points(grid, geo_df_clustered)
            else: #this is a questionable fix in the case that the cluster has only one node - there could be errors
                grid_cluster = geo_df_clustered[geo_df_clustered['Cluster']==cluster_n]


            dist = []

            if num_rivers > 0:
                if num_rivers > 3:
                    ht_avg = pd.DataFrame(columns=[0, 1, 2], index=range(24 * num_typ_days))
                    max_riv = 3
                else:
                    ht_avg = pd.DataFrame(index=range(24 * num_typ_days))
                    max_riv = num_rivers
                input_michele['ht_types'] = max_riv
                for i in range(max_riv):

                    dist = []

                    flow_rate_river = flow_rate.iloc[i, :]

                    for j in range(num_typ_days):
                        ht_avg.loc[j * 24:(j + 1) * 24, i] = flow_rate_river[
                                                             days_rounded * j:days_rounded * (j + 1)].mean()

                    ht_avg[i] = ht_avg[i] * rivers_inters.loc[i, 'head [m]'] * 9.8
                    p_nom = rivers_inters.loc[i, 'P [kW]']
                    # select the turbine with highest capacity among those with pnom < nominal river power
                    dist = [point.distance(rivers_inters.loc[i, 'geometry']) for point in
                            grid_cluster.to_crs(crs).geometry]
                    dist = min(dist)
                    turbines = hydro_turbines[hydro_turbines['nominal_capacity'] < p_nom]
                    turbine = turbines.iloc[-1, :]
                    input_michele['ht_nominal_capacity'][str(i + 1)] = turbine['nominal_capacity']
                    input_michele['ht_investment_cost'][str(i + 1)] = turbine['investment_cost']
                    input_michele['ht_connection_cost'][str(i + 1)] = dist * line_base_cost/ 1000
                    input_michele['ht_OM_cost'][str(i + 1)] = turbine['OM_cost']
                    input_michele['ht_life'][str(i + 1)] = turbine['life']
                    input_michele['ht_unav'][str(i + 1)] = turbine['unav']
                    input_michele['ht_P_min'][str(i + 1)] = turbine['P_min']
                    input_michele['ht_efficiency'][str(i + 1)] = turbine['efficiency']
                    input_michele['ht_max_units'][str(i + 1)] = turbine['max_units']

            else:
                ht_avg = pd.DataFrame(index=range(24 * num_typ_days))
                for i in range(len(input_michele['ht_nominal_capacity'])):
                    ht_avg[i] = 0
                input_michele['ht_max_units'][str(1)] = 0


            ht_avg = ht_avg.append([ht_avg] * (proj_lifetime - 1), ignore_index=True)

        if not os.path.exists(r'Output/Microgrids/average_profiles'):
            os.makedirs(r'Output/Microgrids/average_profiles')
        with open('gisele\michele\Inputs\data.json',
                  'w') as fp:
            json.dump(input_michele, fp, indent=4)
        ht_avg.to_csv(r'Output/Microgrids/average_profiles/ht_avg_'+str(cluster_n)+'.csv')
        wt_avg.to_csv(r'Output/Microgrids/average_profiles/wt_avg_' + str(cluster_n) + '.csv')
        pv_avg.to_csv(r'Output/Microgrids/average_profiles/pv_avg_' + str(cluster_n) + '.csv')


        inst_pv, inst_wind, inst_dg,inst_hydro, inst_bess, inst_inv, init_cost, \
        rep_cost, om_cost, salvage_value, gen_energy, load_energy, emissions = \
            start(load_profile_cluster, pv_avg, wt_avg,input_michele,ht_avg)

        mg.loc[cluster_n, 'PV [kW]'] = inst_pv
        mg.loc[cluster_n, 'Wind [kW]'] = inst_wind
        mg.loc[cluster_n, 'Diesel [kW]'] = inst_dg
        mg.loc[cluster_n, 'Hydro [kW]'] = inst_hydro
        mg.loc[cluster_n, 'BESS [kWh]'] = inst_bess
        mg.loc[cluster_n, 'Inverter [kW]'] = inst_inv
        mg.loc[cluster_n, 'Investment Cost [k€]'] = init_cost
        mg.loc[cluster_n, 'OM Cost [k€]'] = om_cost
        mg.loc[cluster_n, 'Replace Cost [k€]'] = rep_cost
        mg.loc[cluster_n, 'Total Cost [k€]'] = rep_cost + om_cost + init_cost-salvage_value
        mg.loc[cluster_n, 'Energy Produced [MWh]'] = gen_energy
        mg.loc[cluster_n, 'Energy Demand [MWh]'] = load_energy
        mg.loc[cluster_n, 'LCOE [€/kWh]'] = (
                                                    rep_cost + om_cost + init_cost-salvage_value) / gen_energy
        print(mg)
    mg = mg.round(decimals=4)
    mg.to_csv('Output/Microgrids/microgrids.csv', index_label='Cluster')

    return mg


def download_url(url, out_path, chunk_size=128):
    """
    Download zip file from specified url and save it into a defined folder
    Note: check chunk_size parameter
    """
    r = requests.get(url, stream=True)
    with open(out_path, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=chunk_size):
            fd.write(chunk)


def download_tif(area, crs, scale, image, out_path):
    """
    Download data from Earth Engine
    :param area: GeoDataFrame with the polygon of interest area
    :param crs: str with crs of the project
    :param scale: int with pixel size in meters
    :param image: image from the wanted database in Earth Image
    :param out_path: str with output path
    :return:
    """
    min_x, min_y, max_x, max_y = area.geometry.total_bounds
    path = image.getDownloadUrl({
        'scale': scale,
        'crs': 'EPSG:' + str(crs),
        'region': [[min_x, min_y], [min_x, max_y], [max_x, min_y],
                   [max_x, max_y]]
    })
    print(path)
    download_url(path, out_path)
    return


# def lcoe_analysis(clusters_list, total_energy, grid_resume, mg, coe,
#                   grid_ir, grid_om, grid_lifetime):
#     """
#      Computes the LCOE of the on-grid and off-grid and compares both of them
#      to find the best solution.
#      :param clusters_list: List of clusters ID numbers
#      :param total_energy: Energy provided by the grid in its lifetime [kWh]
#      :param grid_resume: Table summarizing grid and connection costs
#      :param mg: Table summarizing all the microgrids and its costs.
#      :param coe: Cost of electricity in the market [€/kWh]
#      :param grid_ir: Inflation rate for the grid investments [%]
#      :param grid_om: Operation and maintenance cost of grid [% of invest cost]
#      :param grid_lifetime: Number of years the grid will operate
#      :return final_lcoe: Table summary of all LCOEs and the proposed solution
#      """
#
#     final_lcoe = pd.DataFrame(index=clusters_list.Cluster,
#                               columns=['Grid NPC [k€]', 'MG NPC [k€]',
#                                        'Grid Energy Consumption [MWh]',
#                                        'MG LCOE [€/kWh]',
#                                        'Grid LCOE [€/kWh]'],
#                               dtype=float)
#     for i in clusters_list.Cluster:
#         final_lcoe.at[i, 'Grid Energy Consumption [MWh]'] = \
#             total_energy.loc[i, 'Energy'] / 1000
#
#         # finding the npv of the cost of O&M for the whole grid lifetime
#
#         total_grid_om = grid_om * (grid_resume.loc[i, 'Grid Cost [k€]'] +
#                                    grid_resume.loc
#                                    [i, 'Connection Cost [k€]']) * 1000
#         total_grid_om = [total_grid_om] * grid_lifetime
#         total_grid_om = np.npv(grid_ir, total_grid_om)
#
#         cluster_grid_om = grid_om * grid_resume.loc[i, 'Grid Cost [k€]'] * 1000
#         cluster_grid_om = [cluster_grid_om] * grid_lifetime
#         cluster_grid_om = np.npv(grid_ir, cluster_grid_om)
#         cluster_grid_npc = cluster_grid_om / 1000 + \
#                            grid_resume.loc[i, 'Grid Cost [k€]']
#         cluster_grid_lcoe = \
#             cluster_grid_npc / final_lcoe.loc[
#                 i, 'Grid Energy Consumption [MWh]']
#         final_lcoe.at[i, 'Grid NPC [k€]'] = \
#             (grid_resume.loc[i, 'Grid Cost [k€]'] +
#              grid_resume.loc[i, 'Connection Cost [k€]']) \
#             + total_grid_om / 1000
#
#         final_lcoe.at[i, 'MG NPC [k€]'] = mg.loc[i, 'Total Cost [k€]']
#         final_lcoe.at[i, 'MG LCOE [€/kWh]'] = mg.loc[i, 'LCOE [€/kWh]'] + \
#                                               cluster_grid_lcoe
#
#         grid_lcoe = final_lcoe.loc[i, 'Grid NPC [k€]'] / final_lcoe.loc[
#             i, 'Grid Energy Consumption [MWh]'] + coe
#
#         final_lcoe.at[i, 'Grid LCOE [€/kWh]'] = grid_lcoe
#
#         if mg.loc[i, 'LCOE [€/kWh]'] + cluster_grid_lcoe > grid_lcoe:
#             ratio = grid_lcoe / (mg.loc[i, 'LCOE [€/kWh]'] + cluster_grid_lcoe)
#             if ratio < 0.95:
#                 proposal = 'ON-GRID'
#             else:
#                 proposal = 'BOTH'
#
#         else:
#             ratio = (mg.loc[i, 'LCOE [€/kWh]'] + cluster_grid_lcoe) / grid_lcoe
#             if ratio < 0.95:
#                 proposal = 'OFF-GRID'
#             else:
#                 proposal = 'BOTH'
#
#         final_lcoe.at[i, 'Best Solution'] = proposal
#     final_lcoe = final_lcoe.round(decimals=4)
#     l()
#     print(final_lcoe)
#
#     final_lcoe.to_csv(r'Output/Microgrids/LCOE_Analysis.csv')
#
#     return final_lcoe
