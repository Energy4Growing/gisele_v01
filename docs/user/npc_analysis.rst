.. _npc_analysis:

============================
NPC analysis
============================
The goal of this step is to find and design the optimal electrification solution
for the area. A MILP algorithm finds which clusters to connect to the national grid and which to electrify with the hybrid microgrids.
The Net Present Cost is minimized considering lifetime of the project equal to microgrid lifetime.
By default it is based on 'gurobi' solver, that can be changed inside the code.

**Files to be loaded**

* Substations: csv files with the coordinates of the possible points of connection to the national grid, with their power associated and cost

**Options**

* Cost of electricity: the wholesale cost of electricity from the national grid
* Inflation rate [0-1]
* Grid lifetime [years]: expected lifetime of the grid infrastructure
* Grid O&M [0-1]: percentage with respect to investment cost
* Max power along lines [kW]: maximum power flow on grid lines

**Output**

Results are visualized in the map and in the table
Path of the final MV lines connecting clusters and grid (vector layer)
Table with costs for each cluster (csv file)
