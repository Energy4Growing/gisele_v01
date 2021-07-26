.. _introduction:

============================
About Gisele
============================

Gisele (GIS for electrification) is a tool aimed to select and design the optimal
electrification strategy for a given rural area.
In particular, given a defined geographical region, it allows to indentify densely populated areas,
cluster them into small communities, size for each of them a hybrid microgrid, create internal grid and decide whether to connect to the inplace electric grid or electrify with a off-grid systems through a cost minimization

The flowchart showing the logical steps of the procedure is reported in the
following figure

.. figure:: images/Flowchart.*
   :alt: Gisele flowchart

The steps are:

* GIS data collection and processing
* Population clustering
* Cluster analysis:
    * Microgrid sizing
    * Internal grid routing
* Connections design
* Electrification strategy optimization
