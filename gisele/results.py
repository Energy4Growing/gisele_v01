import os
import pandas as pd
import geopandas as gpd
import plotly.graph_objs as go


def graph(df, clusters_list, branch, grid_resume_opt, pop_thresh,
          full_ele='no', substations=False):
    '''
    Create graph for the Grid Routing Tab and for the NPC analysis tab
    :param df:
    :param clusters_list:
    :param branch:
    :param grid_resume_opt:
    :param substations: geodataframe with substations point. If subs are not yet
    provided, it is not given and hence set to False
    :param pop_thresh:
    :param full_ele:
    :return:
    '''
    print('Plotting results..')
    # todo -> study area must be created at the beginning
    if os.path.isfile(r'Input/study_area.shp'):
        study_area = gpd.read_file(r'Input/study_area.shp')
        study_area = study_area.to_crs(epsg=4326)
        area = study_area.boundary.unary_union.xy
    else:
        study_area = pd.DataFrame()
        area = ['', '']
    # study_area = gpd.read_file(r'Input/Cavalcante_4326.geojson')
    # study_area = gpd.read_file(r'Input/Namanjavira_4326.geojson')

    if branch == 'yes':
        os.chdir(r'Output//Branches')
    else:
        os.chdir(r'Output//Grids')

    if type(substations)==gpd.GeoDataFrame:
        substations = substations.to_crs(epsg=4326)
    df = df.to_crs(epsg=4326)
    clusters = df[df['Cluster'] != -1]

    if full_ele == 'no':
        terminal_nodes = clusters[clusters['Population'] >= pop_thresh]
    elif full_ele == 'yes':
        terminal_nodes = df[df['Population'] >= pop_thresh]

    fig = go.Figure()
    fig.add_trace(go.Scattermapbox(name='Study Area',
                                   lat=list(area[1]),
                                   lon=list(area[0]),
                                   mode='lines',
                                   marker=go.scattermapbox.Marker(
                                       size=10,
                                       color='black',
                                       opacity=1
                                   ),
                                   text='Study Area',
                                   hoverinfo='text',
                                   below="''",
                                   ))

    fig.add_trace(go.Scattermapbox(name='Clusters',
                                   lat=clusters.geometry.y,
                                   lon=clusters.geometry.x,
                                   mode='markers',
                                   marker=go.scattermapbox.Marker(
                                       size=10,
                                       color='gray',
                                       opacity=0.5
                                   ),
                                   text=clusters.Cluster,
                                   hoverinfo='text',
                                   below="''"
                                   ))
    if type(substations)== gpd.GeoDataFrame:
        fig.add_trace(go.Scattermapbox(name='Substations',
                                       lat=substations.geometry.y,
                                       lon=substations.geometry.x,
                                       mode='markers',
                                       marker=go.scattermapbox.Marker(
                                           size=12,
                                           color='black',
                                           opacity=0.8,
                                       ),
                                       text=list(
                                           zip(substations.ID, substations.Type,
                                               substations.PowerAvailable)),
                                       hoverinfo='text',
                                       below="''",
                                       ))

    fig.add_trace(go.Scattermapbox(name='Terminal Nodes',
                                   lat=terminal_nodes.geometry.y,
                                   lon=terminal_nodes.geometry.x,
                                   mode='markers',
                                   marker=go.scattermapbox.Marker(
                                       size=6,
                                       color='yellow',
                                       opacity=1
                                   ),
                                   text=terminal_nodes.Population.round(0),
                                   hoverinfo='text',
                                   below="''"
                                   ))
    #line_break('all_connections_opt', fig, 'black')

    for cluster_n in clusters_list.Cluster:

        if branch == 'yes':
            if os.path.isfile('Branch_' + str(cluster_n) + '.shp'):
                line_break('Branch_'+ str(cluster_n), fig, 'red')
            if grid_resume_opt.loc[cluster_n, 'Branch Length [km]'] != 0:
                line_break('Collateral_'+ str(cluster_n), fig, 'black')

            # if os.path.isfile('Connection_' + str(cluster_n) + '.shp'):
            #    line_break('Connection_'+ str(cluster_n), fig, 'blue')

        else:
            if os.path.isfile('Grid_'+ str(cluster_n) + '.shp'):
                line_break('Grid_'+ str(cluster_n), fig, 'red')

            # if os.path.isfile('Connection_' + str(cluster_n) + '.shp'):
            #     line_break('Connection_'+ str(cluster_n), fig, 'blue')

    if full_ele == 'yes':
        # line_break(r'all_link/', 'all_link', fig, 'green')
        line_break('all_link/all_link', fig, 'green')

    fig.update_layout(mapbox_style="carto-positron",
                      mapbox_zoom=8.5)
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0},
                      mapbox_center={"lat": df.geometry.y[0],
                                     "lon": df.geometry.x[0]})
    fig.update_layout(clickmode='event+select')
    fig.update_layout(showlegend=True)

    # plot(fig)
    print('Results successfully plotted')
    os.chdir(r'..//..')

    return fig


def line_break(file, fig, color):
    lines = gpd.read_file(file + '.shp')
    lines = lines.to_crs(epsg=4326)
    coordinates = pd.DataFrame(columns=['x', 'y'], dtype='int64')
    count = 0
    for i in lines.iterrows():
        coordinates.loc[count, 'x'] = i[1].geometry.xy[0][0]
        coordinates.loc[count, 'y'] = i[1].geometry.xy[1][0]
        count += 1
        coordinates.loc[count, 'x'] = i[1].geometry.xy[0][1]
        coordinates.loc[count, 'y'] = i[1].geometry.xy[1][1]
        coordinates = coordinates.append(pd.Series(), ignore_index=True)
        count += 2

    fig.add_trace(go.Scattermapbox(name=file,
                                   lat=list(coordinates.y),
                                   lon=list(coordinates.x),
                                   mode='lines',
                                   marker=go.scattermapbox.Marker(
                                       size=5,
                                       color=color,
                                       opacity=1
                                   ),
                                   text=file,
                                   hoverinfo='text',
                                   below="''"
                                   ))

    return


def graph_mg(mg,geo_df_clustered, clusters_list):
    '''
    Create graph for the Microgrids tab
    :param df:
    :param clusters_list:
    :param branch:
    :param grid_resume_opt:
    :param substations:
    :param pop_thresh:
    :param full_ele:
    :return:
    '''
    print('Plotting microgrid results..')
    gdf_clustered_clean = geo_df_clustered[
        geo_df_clustered['Cluster'] != -1]
    gdf_clustered_clean['NPC']=pd.Series()
    fig = go.Figure()

    for cluster_n in clusters_list.Cluster:
        gdf_clustered_clean.loc[gdf_clustered_clean['Cluster']==cluster_n,'NPC']=mg.loc[cluster_n,'Total Cost [k€]']
    plot_cluster = gdf_clustered_clean
    plot_cluster = plot_cluster.to_crs(epsg=4326)
    plot_cluster.X = plot_cluster.geometry.x
    plot_cluster.Y = plot_cluster.geometry.y
    fig.add_trace(go.Scattermapbox(
        lat=plot_cluster.Y,
        lon=plot_cluster.X,
        mode='markers',
        name='Cluster ' + str(cluster_n),
        marker=go.scattermapbox.Marker(
            size=10,
            color=plot_cluster['NPC'],
            opacity=0.9,
            colorbar=dict(title='NPC [k$]')
        ),
        text=list(
            zip(plot_cluster.Cluster, plot_cluster.NPC)),
        hoverinfo='text',
        below="''"
    ))
    fig.update_layout(mapbox_style="carto-positron",
                      mapbox_zoom=8.5)
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0},
                      mapbox_center={"lat": plot_cluster.Y.values[0],
                                     "lon": plot_cluster.X.values[0]})

    fig.update_layout(clickmode='event+select')

    return fig