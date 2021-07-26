.. _clustering:

============================
Clustering
============================

The goal of this step is to cluster the population do find dense areas (communities).
The algorithm used is DBSCAN, which requires 2 input parameters:

* eps: it is the radius [meters] where to look for populated points
* min_points: it is the minimum number of people within a eps radius of a point to consider it a core point

The algorithm selectes some clusters and some outliers, that will be considered as points not to be connected to the grid (electrified with SAS)

**Options**

* Sensitivity analysis: select the range for eps and min_points. DBSCAN will be run changing those values with a defined span (the smaller, the higher number of combinations). As a results, a table showing the number of clusters and the percentage of people electrified will be shown
* Run: after selecting the final eps and min_points, DBSCAN is run. the resulting clusters are shown on the map
* Merge: if, after running DBSCAN, two clusters appear to be too close and it is better to merge them, it is possible to do so by inserting the number of the clusters to be merged


.. note::

    The higher the number of clusters, the faster will be the grid routing process, but the microgrids creation and npc optimization phases will take longer.