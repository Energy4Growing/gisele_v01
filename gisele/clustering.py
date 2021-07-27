"""
GIS For Electrification (GISEle)
Developed by the Energy Department of Politecnico di Milano
Clustering Code

Code for performing the sensitivity analysis in order to help the user to
choose the two parameters MinPts and Eps (Neighbourhood), and then running the
DBSCAN algorithm with the possibility of merging clusters.
"""

import os
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.cluster import DBSCAN
import plotly.graph_objs as go
from gisele.functions import l, s


def sensitivity(resolution, pop_points, geo_df, eps, pts, spans):
    """
    Sensitivity analysis performed to help the user chose the clustering
    parameters, from a range of values run the DBSCAN several times and exports
    a table containing useful information.
    :param resolution: resolution of the dataframe df
    :param pop_points: array containing the 3 coordinates of all points
    :param geo_df: Input Geodataframe of points
    """
    s()
    print("2.Clustering - Sensitivity Analysis")
    span_eps = []
    span_pts = []

    for j in range(1, spans + 1):
        if spans != 1:
            eps_ = int(eps[0] + (eps[1] - eps[0]) / (spans - 1) * (j - 1))
        else:
            eps_ = int(eps[0] + (eps[1] - eps[0]) / spans * (j - 1))
        span_eps.append(eps_)
    for i in range(1, spans + 1):
        if spans != 1:
            pts_ = int(pts[0] + (pts[1] - pts[0]) / (spans - 1) * (i - 1))
        else:
            pts_ = int(pts[0] + (pts[1] - pts[0]) / spans * (i - 1))
        span_pts.append(pts_)

    tab_area = pd.DataFrame(index=span_eps, columns=span_pts)
    tab_people = pd.DataFrame(index=span_eps, columns=span_pts)
    tab_people_area = pd.DataFrame(index=span_eps, columns=span_pts)
    tab_cluster = pd.DataFrame(index=span_eps, columns=span_pts)
    total_people = int(geo_df['Population'].sum(axis=0))

    for eps in span_eps:
        for pts in span_pts:
            db = DBSCAN(eps=eps, min_samples=pts, metric='euclidean'). \
                fit(pop_points, sample_weight=geo_df['Population'])
            labels = db.labels_
            n_clusters_ = int(len(set(labels)) -
                              (1 if -1 in labels else 0))
            geo_df['clusters'] = labels
            gdf_pop_noise = geo_df[geo_df['clusters'] == -1]
            noise_people = round(sum(gdf_pop_noise['Population']), 0)
            clustered_area = (len(geo_df) - len(gdf_pop_noise)) * \
                             (resolution/1000)**2
            perc_area = int(clustered_area / len(geo_df) * 100)
            clustered_people = int((1 - noise_people / total_people) * 100)
            if clustered_area != 0:  # check to avoid crash by divide zero
                people_area = (total_people - noise_people) \
                              / clustered_area
            else:
                people_area = 0
            tab_cluster.at[eps, pts] = n_clusters_
            tab_people.at[eps, pts] = clustered_people
            tab_area.at[eps, pts] = perc_area
            tab_people_area.at[eps, pts] = people_area
    print(
        "Number of clusters - columns MINIMUM POINTS - rows NEIGHBOURHOOD")
    print(tab_cluster)
    l()
    print(
        "% of clustered people - columns MINIMUM POINTS - rows "
        "NEIGHBOURHOOD")
    print(tab_people)
    l()
    print(
        "% of clustered area - columns MINIMUM POINTS - rows "
        "NEIGHBOURHOOD")
    print(tab_area)
    l()
    print("People per area - columns MINIMUM POINTS - rows NEIGHBOURHOOD")
    print(tab_people_area)
    l()
    plt_sens = pd.DataFrame(index=range(tab_people_area.size),
                            columns=['Eps', 'MinPts', 'People/km²',
                                     '% of Clustered People',
                                     'Electrification Filter',
                                     'Number of Clusters',
                                     '% of Area Clustered'],
                            dtype=float)
    count = 0
    for i, row in tab_people_area.iterrows():
        for j in row:
            plt_sens.loc[count, 'Eps'] = i
            plt_sens.loc[count, 'MinPts'] = int(row.index[row == j][0])
            plt_sens.loc[count, 'People/km²'] = round(j, 4)
            plt_sens.loc[count, '% of Clustered People'] = \
                tab_people.loc[i, row.index[row == j]].values[0]
            plt_sens.loc[count, 'Number of Clusters'] = \
                tab_cluster.loc[i, row.index[row == j]].values[0]
            plt_sens.loc[count, '% of Area Clustered'] = \
                tab_area.loc[i, row.index[row == j]].values[0]
            if plt_sens.loc[count, '% of Clustered People'] > 95:
                plt_sens.loc[count, 'Electrification Filter'] = 'Over 95%'
                count += 1
                continue

            if plt_sens.loc[count, '% of Clustered People'] > 85:
                plt_sens.loc[count, 'Electrification Filter'] = '85-95%'
                count += 1
                continue
            if plt_sens.loc[count, '% of Clustered People'] > 75:
                plt_sens.loc[count, 'Electrification Filter'] = '75-85%'
                count += 1
                continue
            else:
                plt_sens.loc[count, 'Electrification Filter'] = 'Under 75%'
                count += 1

    fig = px.scatter_3d(plt_sens, x='Eps', y='MinPts',
                        z='People/km²',
                        color='Number of Clusters',
                        symbol='Electrification Filter',
                        hover_data=["Number of Clusters",
                                    '% of Clustered People',
                                    '% of Area Clustered']
                        )
    fig.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ))
    if not os.path.exists('Output/Clusters/Sensitivity'):
        os.makedirs('Output/Clusters/Sensitivity')
    tab_cluster.to_csv(r"Output/Clusters/Sensitivity/n_clusters.csv")
    tab_people.to_csv(r"Output/Clusters/Sensitivity/%_peop.csv")
    tab_area.to_csv(r"Output/Clusters/Sensitivity/%_area.csv")
    tab_people_area.to_csv(r"Output/Clusters/Sensitivity/people_area.csv")
    print("Clustering sensitivity process completed.\n"
          "You can check the tables in the Output folder.")
    l()

    return fig


def analysis(pop_points, geo_df, pop_load, eps, pts):
    """
    Running of the DBSCAN algorithm with specific parameters and the
    possibility of merging clusters by the user.
    :param pop_points: array containing the 3 coordinates of all points
    :param geo_df: Input Geodataframe of points
    :param pop_load: Estimated load per capita [kW/person]
    :return geo_df_clustered: Input Geodataframe of points with every point
            having a cluster assigned to it.
            (Cluster attribute = -1 means points outside of clustered areas.)
    :return clusters_list: List of all Clusters' ID
    """
    db = DBSCAN(eps=eps, min_samples=pts, metric='euclidean').fit(
        pop_points, sample_weight=geo_df['Population'])
    labels = db.labels_
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)  # ignore noise
    clusters_list = pd.DataFrame(index=range(n_clusters),
                                 columns=['Cluster', 'Population',
                                          'Load [kW]'])
    clusters_list.loc[:, 'Cluster'] = np.arange(n_clusters)
    print('Initial number of clusters: %d' % n_clusters)

    geo_df_clustered = geo_df
    geo_df_clustered['Cluster'] = labels

    for cluster in clusters_list.Cluster:
        clusters_list.loc[cluster, 'Population'] = \
            round(sum(geo_df_clustered.loc[geo_df_clustered
                                           ['Cluster'] == cluster,
                                           'Population']))
        clusters_list.loc[cluster, 'Load [kW]'] = \
            round(clusters_list.loc[cluster, 'Population'] * pop_load, 2)

    return geo_df_clustered, clusters_list


def plot_clusters(geo_df_clustered, clusters_list):

    gdf_clustered_clean = geo_df_clustered[
        geo_df_clustered['Cluster'] != -1]

    fig = go.Figure()

    for cluster_n in clusters_list.Cluster:
        plot_cluster = gdf_clustered_clean[gdf_clustered_clean
                                           ['Cluster'] == cluster_n]
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
                color=cluster_n,
                opacity=0.9
            ),
            text=plot_cluster.Cluster,
            hoverinfo='text',
            below="''"
        ))
        fig.update_layout(mapbox_style="carto-positron",
                          mapbox_zoom=8.5)
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0},
                          mapbox_center={"lat": plot_cluster.Y.values[0],
                                         "lon": plot_cluster.X.values[0]})

        fig.update_layout(clickmode='event+select')
        # fig.show()
    plot_population = geo_df_clustered[geo_df_clustered
                                       ['Population'] > 0]
    plot_population = plot_population.to_crs(epsg=4326)
    plot_population.X = plot_population.geometry.x
    plot_population.Y = plot_population.geometry.y
    fig.add_trace(go.Scattermapbox(
        lat=plot_population.Y,
        lon=plot_population.X,
        mode='markers',
        name='Populated points',
        marker=go.scattermapbox.Marker(
            size=5,
            color='black',
            opacity=0.5
        ),
        text=plot_population.Population,
        hoverinfo='text',
        below="''"
    ))

    print("Cluster plot created")
    return fig

