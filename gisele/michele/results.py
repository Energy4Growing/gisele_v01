import pandas as pd
import numpy as np
import matplotlib.pyplot as plt



def Load_results(instance):
    '''
    This function loads the results that depend of the periods in to a dataframe and creates a excel file with it.

    :param instance: The instance of the project resolution created by PYOMO.

    :return: A dataframe called Time_series with the values of the variables that depend of the periods.
    '''

    

    # Load the variables that depend of the periods in python dictionaries a

    project_duration = int(instance.project_duration.extract_values()[None])
    num_days = int(instance.num_days.extract_values()[None])
    num_years = int(instance.num_years.extract_values()[None])
    h_weight = int(instance.h_weight.extract_values()[None])

    hours_last = []
    for h in range(1, project_duration + 1):
        if h % (num_days * 24) == 0:
            hours_last.append(h)

    res_tot = pd.DataFrame.from_dict(instance.total_power_res.get_values(), orient='index')
    dg_tot = pd.DataFrame.from_dict(instance.dg_power.get_values(), orient='index')
    ht_tot = pd.DataFrame.from_dict(instance.ht_power.get_values(), orient='index')
    bess_disch = pd.DataFrame.from_dict(instance.bess_dis_power.get_values(), orient='index')
    bess_ch = pd.DataFrame.from_dict(instance.bess_ch_power.get_values(), orient='index')
    lost_load = pd.DataFrame.from_dict(instance.lost_load.get_values(), orient='index')
    load = pd.DataFrame.from_dict(instance.Load.get_values(), orient='index')
    dg_fuel = pd.DataFrame.from_dict(instance.dg_fuel_consumption.get_values(), orient='index') #[L]

    load_tot_y=[] # list of yearly load [MWh]
    for y in range(num_years):
        load_y = 0.001 * h_weight * sum(load.iloc[(y*num_days*24+h),0] for h in range(num_days*24))
        load_tot_y.append(load_y)

    dg_tot_y=[] # list of yearly diesel dispatching [MWh]
    for y in range(num_years):
        dg_y = 0.001 * h_weight * sum(dg_tot.iloc[(y*num_days*24+h),0] for h in range(num_days*24))
        dg_tot_y.append(dg_y)

    res_tot_y=[] # list of yearly renewable dispatching [MWh]
    for y in range(num_years):
        res_y = 0.001 * h_weight * sum(res_tot.iloc[(y*num_days*24+h),0] for h in range(num_days*24))
        res_tot_y.append(res_y)

    lost_load_tot_y=[] # list of yearly lost load [MWh]
    for y in range(num_years):
        lost_load_y = 0.001 * h_weight * sum(lost_load.iloc[(y*num_days*24+h),0] for h in range(num_days*24))
        lost_load_tot_y.append(lost_load_y)

    gen_energy = sum(res_tot_y) + sum(dg_tot_y)
    load_energy = sum(load_tot_y)
    # graph on yearly dispatching of resources
    x=np.arange(1,num_years+1)
    y1=res_tot_y
    plt.bar(x, y1, color='#EEB422', label='RES')
    y2=dg_tot_y
    plt.bar(x, y2, bottom=y1, color='#008B8B', label='DG')
    y12=np.add(y1, y2).tolist()
    y3=lost_load_tot_y
    plt.bar(x, y3, bottom=y12, color='#CD6839', label='LOST')
    plt.plot(x, load_tot_y, color='black', label='LOAD')
    plt.xlabel('Years')
    plt.xticks(x)
    plt.ylabel('Dispatching of resources [MWh]')
    plt.legend(loc='upper left')
    # plt.show()


    # graph on dispatching of first day
    x = np.arange(1,25)
    y1=res_tot.iloc[0:24, 0].values
    y2=dg_tot.iloc[0:24, 0].values
    y12=np.add(y1, y2).tolist()
    y3=bess_disch.iloc[0:24, 0].values
    y123=np.add(y12, y3).tolist()
    y4=-bess_ch.iloc[0:24, 0].values
    y1234=np.add(y123, y4).tolist()
    y5=lost_load.iloc[0:24, 0].values
    plt.bar(x, y1, color='#EEB422', label='RES')
    plt.bar(x, y2, bottom=y1, color='#CD2626', label='DG')
    plt.bar(x, y3, bottom=y12, color='#008B8B', label='DISCH')
    plt.bar(x, y4, bottom=y123, color='#228B22', label='CH')
    plt.bar(x, y5, bottom=y1234, color='#CD6839', label='LOST')
    #y = [res_tot.iloc[0:24,0].values, dg_tot.iloc[0:24,0].values, bess_disch.iloc[0:24,0].values, -bess_ch.iloc[0:24,0].values, lost_load.iloc[0:24,0].values]
    #plt.stackplot(x, y, labels=['res', 'dg', 'disch', 'ch', 'lost'])
    plt.plot(x, load.iloc[0:24,0].values, color='black', label='LOAD')
    plt.xlabel('Hours')
    plt.xticks(x)
    plt.ylabel('Dispatching of resources [kWh]')
    plt.legend(loc='upper left')
    # plt.show()
    PV_types = instance.pv_types.extract_values()[None]
    WT_types = instance.wt_types.extract_values()[None]
    BESS_types = instance.bess_types.extract_values()[None]
    Generator_types = instance.dg_types.extract_values()[None]
    HT_types = instance.ht_types.extract_values()[None]

    inst_pv = 0
    inst_wind = 0
    inst_bess = 0
    inst_dg = 0
    inst_inv_bess = 0
    inst_hydro = 0

    for i in range(1, PV_types + 1):
        Number_PV = int(instance.pv_units.get_values()[str(i)])
        pv_nominal_capacity = float(
            instance.pv_nominal_capacity.extract_values()[str(i)])
        inst_pv = inst_pv + Number_PV * pv_nominal_capacity

    for i in range(1, WT_types + 1):
        Number_WT = int(instance.wt_units.get_values()[str(i)])
        wt_nominal_capacity = float(
            instance.wt_nominal_capacity.extract_values()[str(i)])
        inst_wind = inst_wind + Number_WT * wt_nominal_capacity

    for i in range(1, BESS_types + 1):
        Number_BESS = int(instance.bess_units.get_values()[str(i)])
        bess_nominal_capacity = float(
            instance.bess_nominal_capacity.extract_values()[str(i)])
        inst_bess = inst_bess + Number_BESS * bess_nominal_capacity

    for i in range(1, Generator_types + 1):
        Number_Generator = int(instance.dg_units.get_values()[str(i)])
        dg_nominal_capacity = float(
            instance.dg_nominal_capacity.extract_values()[str(i)])
        inst_dg = inst_dg + Number_Generator * dg_nominal_capacity

    for i in range(1, BESS_types + 1):
        Number_BESS = int(instance.bess_units.get_values()[str(i)])
        inv_bess_nominal_capacity = float(
            instance.bess_power_max.get_values()[str(i)])
        inst_inv_bess = inst_inv_bess + inv_bess_nominal_capacity

    for i in range(1, HT_types + 1):
        Number_HT = int(instance.ht_units.get_values()[str(i)])
        ht_nominal_capacity = float(
            instance.ht_nominal_capacity.extract_values()[str(i)])
        inst_hydro = inst_hydro + Number_HT*ht_nominal_capacity

    # Number_PV = int(instance.pv_units.get_values()[1])
    # Number_WT = int(instance.wt_units.get_values()[1])
    # Number_BESS=int(instance.bess_units.get_values()[1])
    # Number_Generator = int(instance.dg_units.get_values()[1])
    #
    # dg_nominal_capacity=float(instance.dg_nominal_capacity.extract_values()[1])
    # bess_nominal_capacity = float(instance.bess_nominal_capacity.extract_values()[1])
    # wt_nominal_capacity = float(instance.wt_nominal_capacity.extract_values()[1])
    # pv_nominal_capacity = float(instance.pv_nominal_capacity.extract_values()[1])
    # inv_nominal_capacity = float(instance.bess_power_max.extract_values()[1])+pv_nominal_capacity

    # unit_type=['DG', 'PV', 'WT', 'BESS']
    # installed_units=[Number_Generator*dg_nominal_capacity, Number_PV*pv_nominal_capacity, Number_WT*wt_nominal_capacity, Number_BESS*bess_nominal_capacity]
    # plt.bar(unit_type,installed_units)
    # # plt.show()

    init_cost = float(instance.initial_investment.get_values()[None])
    rep_cost = float(instance.replacement_cost.get_values()[None])
    om_cost = float(instance.OM_cost.get_values()[None])
    salvage_value = float(instance.salvage_value.get_values()[None])


    inst_inv = inst_inv_bess+inst_pv

    print('PV installed=' + str(inst_pv))
    print('wind installed=' + str(inst_wind))
    print('diesel installed=' + str(inst_dg))
    print('bess installed=' + str(inst_bess))
    print('inv installed=' + str(inst_inv))
    print('hydro installed=' + str(inst_hydro))

    print('initial investment='+str(init_cost))
    print('replacement cost='+str(rep_cost))
    print('OM cost='+str(om_cost))
    print('salvage value='+str(salvage_value))

    return inst_pv, inst_wind, inst_dg,inst_hydro, inst_bess, inst_inv, init_cost, \
        rep_cost, om_cost, salvage_value, gen_energy, load_energy, dg_fuel

    '''
    Number_Years = int(instance.project_duration.extract_values()[None]/8760)
    Number_Periods = int(instance.project_duration.extract_values()[None])
    PV_types=instance.pv_types.extract_values()[None]
    WT_types = instance.wt_types.extract_values()[None]
    BESS_types = instance.bess_types.extract_values()[None]
    Generator_types = instance.dg_types.extract_values()[None]

    #plot results
    pv_profile_input=pd.read_csv('Inputs\solarPV_Soroti_1.csv')

    fig,ax=plt.subplots()
    for i in range(PV_types):
        PV=instance.pv_units.get_values()[i]
        PV_profile=instance.input_pv_prod[i]*PV
        PV_profile.plot(ax=ax,label='PV'+str(i))

    for i in range(PV_types):
        PV=instance.pv_units.get_values()[i]
        PV_profile=instance.input_pv_prod[i]*PV
        PV_profile.plot(ax=ax,label='PV'+str(i))

    import plotly.graph_objects as go
    import numpy as np
    x = np.arange(Number_Periods)
    fig = go.Figure(data=go.Scatter(x=x, y=res_tot[0].values))
    fig.add_trace(go.Scatter(x=x, y=dg_tot[0].values))
    fig.show()

    dg_tot=pd.DataFrame(columns=range(Generator_types), index=range(1,Number_Periods+1))
    for i in range(Generator_types):
        dg_tot[i]=pd.DataFrame.from_dict(instance.dg_power.get_values()[i])
    '''

