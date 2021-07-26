.. _introduction:

============================
Grid routing
============================

The goal of this step is to route the internal grid of each cluster.
There are two different algorithms used, based on graph theory and on shortest path:

* Steinerman: it uses the MST approximation of the Steiner tree problem.
* Spiderman: it first runs the MST alogrithm and then it redesignes only the "long lines", lines longer than the resolution with Dijsktra algorithm

It is also possible to create a more realistic grid topology, designing a main branch and collaterals. In this case the grid routing procedure is run twice, with two different resolutions of the grid, to design in cascade the principal feeder (main branch) and the collaterals connected to it. In this way two cable types could be deployed.


**Options**


* Total electrification: after creating the grids inside clusters, also outliers are connected with a least cost path
* Population thresholds [-]: connect all the points with a number of people at least equal to this number
* Line base cost [€/km]: is the cost per unit length of the lines, that is then multiplied by the weights
* Load per capita [kW]: is the peak load associated to each person
* Branch strategy: selecting this option, the algorithms design a main branch and collaterals for each cluster

  * Population threshold (main branches) [-]: the minimum number of people necessary to connect a point when designing the main branch
  * Line base cost (collaterals) [€/km]: is the cost per unit length of the collateral lines (smaller than main branch)


.. warning::
    Running the options for the branches creation and for total electrification may require time and memory.

