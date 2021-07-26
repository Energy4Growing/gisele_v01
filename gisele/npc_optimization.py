from __future__ import division

from pyomo.opt import SolverFactory
from pyomo.core import AbstractModel
from pyomo.dataportal.DataPortal import DataPortal
from pyomo.environ import *

import pandas as pd
import numpy as np
from datetime import datetime


def cost_optimization(p_max_lines, coe):
    # Initialize model
    model = AbstractModel()
    data = DataPortal()

    # Define sets
    model.N = Set()  # Set of all nodes, clusters and substations
    data.load(filename=r'Output/NPC/set.csv', set=model.N)

    model.clusters = Set()  # Set of clusters
    data.load(filename='Output/NPC/clusters.csv', set=model.clusters)

    model.substations = Set()  # Set of substations
    data.load(filename='Output/NPC/subs.csv', set=model.substations)

    model.links = Set(dimen=2,
                      within=model.N * model.N)  # in the csv the values must be delimited by commas
    data.load(filename='Output/NPC/possible_links.csv', set=model.links)

    # Nodes are divided into two sets, as suggested in https://pyomo.readthedocs.io/en/stable/pyomo_modeling_components/Sets.html:
    # NodesOut[nodes] gives for each node all nodes that are connected to it via outgoing links
    # NodesIn[nodes] gives for each node all nodes that are connected to it via ingoing links

    def NodesOut_init(model, node):
        retval = []
        for (i, j) in model.links:
            if i == node:
                retval.append(j)
        return retval

    model.NodesOut = Set(model.N, initialize=NodesOut_init)

    def NodesIn_init(model, node):
        retval = []
        for (i, j) in model.links:
            if j == node:
                retval.append(i)
        return retval

    model.NodesIn = Set(model.N, initialize=NodesIn_init)

    #####################Define parameters#####################

    # Electric power in the nodes (injected (-) or absorbed (+))
    model.p_clusters = Param(model.clusters)
    data.load(filename='Output/NPC/c_power.csv', param=model.p_clusters)

    # Maximum power supplied by sustations
    model.p_max_substations = Param(model.substations)
    data.load(filename='Output/NPC/sub_power.csv',
              param=model.p_max_substations)

    # Total net present cost of microgrid to supply each cluster
    model.c_microgrids = Param(model.clusters)
    data.load(filename='Output/NPC/c_npc.csv',
              param=model.c_microgrids)

    # Total net present cost of substations
    model.c_substations = Param(model.substations)
    data.load(filename='Output/NPC/sub_npc.csv',
              param=model.c_substations)

    # Connection cost of the possible links
    model.c_links = Param(model.links)
    data.load(filename='Output/NPC/milp_links.csv', param=model.c_links)

    # Energy consumed by each cluster in grid lifetime
    model.energy = Param(model.clusters)
    data.load(filename='Output/NPC/energy.csv', param=model.energy)

    # poximum power flowing on lines
    # model.p_max_lines = Param()  # max power flowing on MV lines
    # data.load(filename='Input/data_procedure2.dat')

    #####################Define variables#####################

    # binary variable x[i,j]: 1 if the connection i,j is present, 0 otherwise,initialize=x_rule
    model.x = Var(model.links, within=Binary)
    # binary variable y[i]: 1 if a substation is installed in node i, 0 otherwise,initialize=y_rule
    model.y = Var(model.substations, within=Binary)
    # binary variable z[i]: 1 if a microgrid is installed in node i, 0 otherwise,initialize=z_rule
    model.z = Var(model.clusters, within=Binary)
    # power[i,j] is the power flow of connection i-j
    model.P = Var(model.links)
    # power[i] is the power provided by substation i
    model.p_substations = Var(model.substations, within=PositiveReals)

    #####################Define constraints###############################

    def Radiality_rule(model):
        return summation(model.x) == len(model.clusters) - summation(model.z)

    model.Radiality = Constraint(
        rule=Radiality_rule)  # all the clusters are either connected to the MV grid or powered by microgrid

    def Power_flow_conservation_rule(model, node):
        return (sum(model.P[j, node] for j in model.NodesIn[node]) - sum(
            model.P[node, j]
            for j in model.NodesOut[node])) == +model.p_clusters[node] * (
                           1 - model.z[node])

    model.Power_flow_conservation = Constraint(model.clusters,
                                               rule=Power_flow_conservation_rule)  # when the node is powered by SHS all the power is transferred to the outgoing link

    def PS_Power_flow_conservation_rule(model, node):
        return (sum(model.P[j, node] for j in model.NodesIn[node]) - sum(
            model.P[node, j]
            for j in model.NodesOut[node])) == -model.p_substations[node]

    model.PS_Power_flow_conservation = Constraint(model.substations,
                                                  rule=PS_Power_flow_conservation_rule)  # outgoing power from PS to connected links

    def Power_upper_bounds_rule(model, i, j):
        return model.P[i, j] <= p_max_lines * model.x[i, j]

    model.upper_Power_limits = Constraint(model.links,
                                          rule=Power_upper_bounds_rule)  # limit to power flowing on MV lines

    def Power_lower_bounds_rule(model, i, j):
        return model.P[i, j] >= -p_max_lines * model.x[i, j]

    model.lower_Power_limits = Constraint(model.links,
                                          rule=Power_lower_bounds_rule)

    def Primary_substation_upper_bound_rule(model, i):
        return model.p_substations[i] <= model.p_max_substations[i] * model.y[
            i]

    model.Primary_substation_upper_bound = Constraint(model.substations,
                                                      rule=Primary_substation_upper_bound_rule)  # limit to power of PS

    ####################Define objective function##########################

    # minimize total npc over microgrid lifetime
    def ObjectiveFunction(model):
        return summation(model.c_microgrids, model.z) + summation(model.c_substations, model.y) + \
               summation(model.c_links, model.x) + sum(model.energy[i] * (1-model.z[i]) for i in model.clusters) * coe

    model.Obj = Objective(rule=ObjectiveFunction, sense=minimize)

    #############Solve model##################
    instance = model.create_instance(data)
    print('Instance is constructed:', instance.is_constructed())
    # opt = SolverFactory('cplex',executable=r'C:\Users\silvi\IBM\ILOG\CPLEX_Studio1210\cplex\bin\x64_win64\cplex')
    # opt = SolverFactory('glpk')
    opt = SolverFactory('gurobi')
    opt.options['mipgap'] = 0.01
    print('Starting optimization process')
    time_i = datetime.now()
    opt.solve(instance, tee=True)
    time_f = datetime.now()
    print('Time required for optimization is', time_f - time_i)
    links = instance.x
    power = instance.P
    microgrids = instance.z
    connections_output = pd.DataFrame(columns=[['id1', 'id2']])
    microgrids_output = pd.DataFrame(columns=['ID'])
    power_output = pd.DataFrame(columns=[['id1', 'id2', 'P']])
    k = 0
    for index in links:
        if int(round(value(links[index]))) == 1:
            connections_output.loc[k, 'id1'] = index[0]
            connections_output.loc[k, 'id2'] = index[1]
            k = k + 1
    k = 0
    for index in microgrids:
        if int(round(value(microgrids[index]))) == 1:
            microgrids_output.loc[k, 'ID'] = index
            k = k + 1
    k = 0
    for index in power:
        if value(power[index]) != 0:
            power_output.loc[k, 'id1'] = index[0]
            power_output.loc[k, 'id2'] = index[1]
            power_output.loc[k, 'P'] = value(power[index])
            k = k + 1

    connections_output.to_csv('Output/NPC/MV_connections_output.csv', index=False)
    microgrids_output.to_csv('Output/NPC/MV_SHS_output.csv', index=False)
    power_output.to_csv('Output/NPC/MV_power_output.csv', index=False)
    return microgrids_output, connections_output
