import pandapower as pp
import geopandas as gpd
import pandas as pd
import os
from pandapower.plotting.plotly.mapbox_plot import set_mapbox_token
from pandapower.plotting import simple_plot,simple_plotly
from functions import nearest
from pyproj import Transformer
import pandas.testing as pdt
from shapely.geometry import Point
import shapely
import os
import plotly
""" DEFINE VOLTAGE LEVELS AND CUSTOM LINE TYPES """
vn=13.8
linetypes = {"Alumoweld 4 AWG - 25 mm2": {"r_ohm_per_km": 0.01, "x_ohm_per_km": 0.02, "c_nf_per_km": 5, "max_i_ka": 0.145}}

set_mapbox_token('pk.eyJ1IjoibmExMjAzMTMyIiwiYSI6ImNrYW9qYThxMzFvb3cyc3A2cWJyaHdhdTMifQ.bfRDDy-DV4-VuVWjDNzodg')
all_clusters_together=False # this variable decides if we will create 1 grid (true) or separate grids for each cluster
""" STEP 1 - LOAD the nodes, find which clusters are grid-connected and filter the nodes from those clusters only"""
os.chdir('..')
substations=pd.read_csv('Input/Substations-Cavalcante.csv')
config = pd.read_csv('Input/Configuration.csv') # this part will be changed when this becomes a function,
# the parameter will be automatically taken as an input
#pop_load = float(config.iloc[6, 1])
pop_load = 0.4
Nodes=gpd.read_file('Output/Clusters/geo_df_clustered.json')
print(Nodes['ID'][0])
grid_resume_opt=pd.read_csv('Output/Branches/grid_resume_opt.csv')
grid_resume_opt=grid_resume_opt[grid_resume_opt['Connection Type']!='Microgrid']
grid_resume_opt['Substation ID']=grid_resume_opt['Substation ID'].astype(int)
grid_resume_opt['Cluster']=grid_resume_opt['Cluster'].astype(int)
counter=0
if all_clusters_together:
# create the pp network)
    network = pp.create_empty_network()
    pp.create_std_types(network, data=linetypes, element="line")
for col_name,row in substations.iterrows():
    pomm = grid_resume_opt[grid_resume_opt['Substation ID']==row.ID]
    pom=pomm['Cluster'].tolist()
    if not pom and not pom==9:
        continue
    else:
        pomm.reset_index(drop=True, inplace=True)
        if pomm.iloc[0][9]==0:
            create_substation_node=False
        else:
            create_substation_node=True
        counter=counter+1
        print('substation '+str(row.ID)+' needs to be connected to cluster/s '+str(pom))
        Main_branches=[]
        Collaterals=[]
        if not all_clusters_together:
        # create the pp network)
            network = pp.create_empty_network()
            pp.create_std_types(network, data=linetypes, element="line")
        for j in pom: #this for cycle is because multiple grids could be connected to one single substation
            # this part corelates the substation with the grid of points ( finds the closest point )
            substation_point=Point(row.X,row.Y)
            nearest_p = Nodes['geometry'] == shapely.ops.nearest_points(substation_point,  Nodes.unary_union)[1]
            # Get the corresponding value from df2 (matching is based on the geometry)
            value = Nodes.loc[nearest_p].values[0]
            #substation_point = Nodes[Nodes['ID']==value[0]]
            substation_point=value[0]
            substation_point_X=value[1]
            substation_point_Y=value[2]
            print(substation_point)
            #substation_point['ID']=substation_point['ID'].astype(int)
            #substation_point.set_index('ID',inplace=True)
            bool1 = os.path.isfile('Output/Branches/Branch_' + str(j) + '.shp')
            bool2 = os.path.isfile('Output/Branches/Collateral_' + str(j) + '.shp')
            if bool1:
                Main_branches = gpd.read_file('Output/Branches/Branch_'+ str(j)+'.shp')
                Main_branches['ID1'] = Main_branches['ID1'].astype(int)
                Main_branches['ID2'] = Main_branches['ID2'].astype(int)
            if bool2:
                Collaterals = gpd.read_file('Output/Branches/Collateral_' + str(j) + '.shp')
                Collaterals['ID1'] = Collaterals['ID1'].astype(int)
                Collaterals['ID2'] = Collaterals['ID2'].astype(int)
            if bool1 and bool2:
                Network_nodes=Nodes[Nodes['ID'].isin(Main_branches.ID1) | Nodes['ID'].isin(Main_branches.ID2) \
                | Nodes['ID'].isin(Collaterals.ID1) | Nodes['ID'].isin(Collaterals.ID2)]
            elif bool1:
                Network_nodes = Nodes[Nodes['ID'].isin(Main_branches.ID1) | Nodes['ID'].isin(Main_branches.ID2)]
            elif bool2:
                Network_nodes=Nodes[Nodes['ID'].isin(Collaterals.ID1) | Nodes['ID'].isin(Collaterals.ID2)]
            else:
                skip=True # i don't think this can happen, a cluster without any branches


            Network_nodes.reset_index(inplace=True)


            Network_nodes = Network_nodes.to_crs(epsg=32723)
            Network_nodes.X=Network_nodes.geometry.x
            Network_nodes.Y=Network_nodes.geometry.y

            # Create nodes, main branches and collaterals
            for col_name, node in Network_nodes.iterrows():
                pp.create_bus(net=network,vn_kv=vn,name=str(node.ID),index=node.ID,geodata=(node.X,node.Y))
            if bool1:
                for col_name, main_branch in Main_branches.iterrows():
                    pp.create_line(net=network,from_bus=main_branch.ID1,to_bus=main_branch.ID2,length_km=main_branch.Length/1000
                               ,std_type='94-AL1/15-ST1A 10.0') #Inom=140A

            if bool2:
                for col_name, collateral in Collaterals.iterrows():
                    pp.create_line(net=network, from_bus=collateral.ID1, to_bus=collateral.ID2,
                                length_km=collateral.Length / 1000, std_type='34-AL1/6-ST1A 10.0')#Inom=105A
            for col_name, node in Network_nodes.iterrows():
                pp.create_load(net=network, bus=node.ID,p_mw=node.Population*pop_load/1000,
                               q_mvar=0.5*node.Population*pop_load/1000)

            if create_substation_node: # Check if new nodes need to be added, in case multiple lines exist.
                if substation_point in Network_nodes.ID:
                    pp.create_bus(net=network, vn_kv=vn, name=str(substation_point), index=substation_point,
                                geodata=(substation_point_X, substation_point_Y))
                Connection = gpd.read_file('Output/Branches/Connection_' + str(j) + '.shp')
                Connection['ID1'] = Connection['ID1'].astype(int)
                Connection['ID2'] = Connection['ID2'].astype(int)
                for col_name, connection in Connection.iterrows():
                    pp.create_line(net=network,from_bus=connection.ID1,to_bus=connection.ID2,length_km=connection.Length/1000
                               ,std_type='94-AL1/15-ST1A 10.0')
            pp.create_ext_grid(net=network, bus=substation_point, s_sc_max_mva=10000)

            #print(network)
            if not all_clusters_together:
                pp.runpp(network, algorithm='nr')
            #transformer = Transformer.from_crs(4326, 32723)
                plot=simple_plotly(network,on_map=True,projection='epsg:32723')
                plotly.offline.plot(plot, filename='Cluster'+str(j)+'.html')
                pp.to_excel(network, 'Resuts_cluster'+str(j)+'.xlsx')
                #simple_plot(network)
                pp.plotting.plot_voltage_profile(network)
                pp.plotting.plotly.pf_res_plotly(network,
                                                 filename='Results_cluster'+str(j)+'.html',climits_volt=(0.85, 1.15))
            # plt.show()
            #pf_res_plotly(network)
if all_clusters_together:
    pp.runpp(network, algorithm='nr')
    plot=simple_plotly(network,on_map=True,projection='epsg:32723')
    pp.plotting.plot_voltage_profile(network)
    pp.to_excel(network, "results_powerflow_all_clusters.xlsx")
    plotly.offline.plot(plot, filename='All Clusters.html')
    pp.plotting.plotly.pf_res_plotly(network,climits_volt=(0.8,1.15),bus_size=4,line_width=2)
    #Another way to plot results
    #bt = pp.plotting.plotly.create_bus_trace(network, cmap=True)
    #lt = pp.plotting.plotly.create_line_trace(network, cmap=True)
    #pp.plotting.plotly.draw_traces(lt + bt, showlegend=False)

