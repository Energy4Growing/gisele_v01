#-----------------OBJECTIVE FUNTION

def total_net_present_cost(model):
      return  model.initial_investment + model.OM_cost + model.replacement_cost - model.salvage_value

def total_initial_investment(model):
    return  model.initial_investment== 0.001 * (
            +sum(model.dg_units[g]*model.dg_investment_cost[g] for g in model.dg) \
            +sum(model.ht_units[ht] * model.ht_investment_cost[ht] for ht in model.ht) \
            +sum(model.ht_units[ht] * model.ht_connection_cost[ht] for ht in model.ht) \
            +sum(model.pv_units[p]*model.pv_investment_cost[p] for p in model.pv) \
            +sum(model.wt_units[w]*model.wt_investment_cost[w] for w in model.wt) \
            +sum(model.bess_units[b]*model.bess_investment_cost[b] for b in model.bess)
            +sum(model.bess_power_max[b]*model.inverter_cost for b in model.bess) \
    )

def total_replacement_cost(model):
    return  model.replacement_cost == 0.001 * (
        +sum(sum(model.discount_rate[h]*model.h_weight*model.bess_wear_cost[b]*model.bess_dis_power[h,b] for b in model.bess) for h in model.hours) \
        +sum(sum(model.discount_rate[h]*model.h_weight*model.dg_units_on[h,g]*model.dg_repl_cost[g] for g in model.dg) for h in model.hours) \
    )

def total_OM_cost(model):
    return  model.OM_cost == 0.001 * (
        +sum(sum(model.discount_rate[h]*model.h_weight*model.fuel_cost*model.dg_fuel_consumption[h,g] for g in model.dg)for h in model.hours) \
        +sum(sum(model.discount_rate[h]*model.h_weight*model.dg_OM_cost[g]*model.dg_units_on[h,g] for g in model.dg) for h in model.hours) \
        +sum(sum(model.discount_rate[h]*model.pv_units[p]*model.pv_OM_cost[p] for p in model.pv) for h in model.hours_last) \
        +sum(sum(model.discount_rate[h]*model.wt_units[w]*model.wt_OM_cost[w] for w in model.wt) for h in model.hours_last) \
        +sum(sum(model.discount_rate[h]*model.bess_units[b]*model.bess_OM_cost[b] for b in model.bess) for h in model.hours_last)
        + sum(sum(model.discount_rate[h] * model.ht_units[ht] * model.ht_OM_cost[ht] for ht in model.ht) for h in model.hours_last) \
        #+sum(model.discount_rate[h]*model.lost_load[h]*model.lost_load_value for h in model.hours) \
    )

def total_salvage_value(model):
    return model.salvage_value == 0.001 * model.derating_factor * (
        +sum((1 / (1+model.ir)**model.num_years)*model.pv_units[p]*model.pv_investment_cost[p]*\
             (model.pv_life[p]-model.num_years)/model.pv_life[p] for p in model.pv) \
        +sum((1 / (1+model.ir)**model.num_years)*model.wt_units[w]*model.wt_investment_cost[w]*\
             (model.wt_life[w]-model.num_years)/model.wt_life[w] for w in model.wt) \
        +sum((1 / (1+model.ir)**model.num_years)*model.bess_power_max[b]*model.inverter_cost*\
             (model.inverter_life-model.num_years)/model.inverter_life for b in model.bess) \
        + sum((1 / (1 + model.ir) ** model.num_years) * model.ht_units[ht] * model.ht_investment_cost[ht] * \
              (model.ht_life[ht] - model.num_years) / model.ht_life[ht] for ht in model.ht) \
        )



#------------------------------CONSTRAINTS

#this constraint defines the hourly demand, subject to a linear growth rate starting from the second year
def total_load(model,h):
    if h<=(model.num_days*24):
        return model.Load[h] == model.input_load[h]
    else:
        return model.Load[h] == model.Load[h-(model.num_days*24)]*(1+model.demand_growth)

# this group of constraints limits the number of units installed
def pv_installed(model,p):
    return model.pv_units[p] <= model.pv_max_units[p]

def wt_installed(model,w):
    return model.wt_units[w] <= model.wt_max_units[w]
def ht_installed(model,ht):
    return model.ht_units[ht] <= model.ht_max_units[ht]

def bess_installed(model,b):
    return model.bess_units[b] <= model.bess_max_units[b]

def dg_installed(model, g):
    return model.dg_units[g] <= model.dg_max_units[g]

# this constraint defines the maximum power produced by renewables
def res_energy(model,h):
    return model.total_power_res[h] <= sum(model.pv_units[p]*model.input_pv_prod[h,p] for p in model.pv) + sum(model.wt_units[w]*model.input_wt_prod[h,w] for w in model.wt)
# this constraints expresses the balance of the system
def system_balance(model,h):
    return model.Load[h] == model.total_power_res[h] + sum(model.dg_power[h,g] for g in model.dg)+ sum(model.ht_power[h,ht]
            for ht in model.ht)  + model.lost_load[h]+\
           sum(model.bess_dis_power[h,b]*model.bess_dis_efficiency_nom[b]-model.bess_ch_power[h,b]/model.bess_ch_efficiency_nom[b] for b in model.bess)

# these constraints define the maximum allowable yearly unmet demand
def total_energy_req(model,h):
    if h==1:
        return model.load_total[h] == model.Load[h]
    else:
        return model.load_total[h] == model.load_total[h-1] + model.Load[h]

def total_lost_load(model,h):
    if h==1:
        return model.lost_load_total[h] == model.lost_load[h]
    else:
        return model.lost_load_total[h] == model.lost_load_total[h-1] + model.lost_load[h]

def limit_lost_load(model,h):
    if h<=(model.num_days*24):
        return model.lost_load_total[h]<= model.load_total[h]*model.lost_load_max
    else:
        return model.lost_load_total[h] - model.lost_load_total[h-(model.num_days*24)] <= (model.load_total[h]- model.load_total[h-(model.num_days*24)])*model.lost_load_max

# these constraints set the reserve requirement and its allocation among DG and BESS
def total_reserve_req(model,h):
    return model.reserve[h] == model.load_forecast_error*model.Load[h]+model.pv_forecast_error*sum(model.pv_units[p]*model.input_pv_prod[h,p] for p in model.pv)\
           +model.wt_forecast_error*sum(model.wt_units[w]*model.input_wt_prod[h,w] for w in model.wt)

def reserve_allocation(model,h):
    return sum(model.reserve_dg[h,g] for g in model.dg)+sum(model.reserve_bess[h,b] for b in model.bess) >= model.reserve[h]

#########################################
# constraints related to diesel generators

def fuel_consumption_curve(model,h,g): #linear characteristic
    return model.dg_fuel_consumption[h,g] == model.dg_cost_coeff_A[g]*model.dg_units_on[h,g]+model.dg_cost_coeff_B[g]*model.dg_power[h,g]

def dg_power_max(model,h,g):
    # with reserve
    return model.dg_power[h,g]+model.reserve_dg[h,g] <= model.dg_nominal_capacity[g]*model.dg_units_on[h,g]
    # without reserve
    # return model.dg_power[h,g] <= model.dg_nominal_capacity[g]*model.dg_units_on[h,g]

def dg_power_min(model,h,g):
    return model.dg_power[h,g] >= model.dg_nominal_capacity[g]*model.dg_P_min[g]*model.dg_units_on[h,g]

def dg_online(model,h,g):
    return model.dg_units_on[h,g] <= model.dg_units[g]

###########################################
# constraints related to batteries
def battery_power_max(model,h,b): #maximum power flowing through batteries, to size converters
    return model.bess_dis_power[h,b]*model.bess_dis_efficiency_nom[b]+model.bess_ch_power[h,b]/model.bess_ch_efficiency_nom[b] <= model.bess_power_max[b]

# following two constraints to avoid charging and discharging at the same time
def bess_condition1(model,h,b):
    return model.bess_ch_power[h,b] <= model.bess_bin[h,b]*model.M

def bess_condition2(model,h,b):
    return model.bess_dis_power[h,b] <= (1 - model.bess_bin[h,b])*model.M

def bess_charging_level(model,h,b):
    if h==1:
        return model.bess_total_energy[h,b] ==  model.bess_units[b]*model.bess_nominal_capacity[b]*model.bess_initial_SOC[b]+model.bess_ch_power[h,b]-model.bess_dis_power[h,b]
#    elif h==model.project_duration:
#        return model.bess_total_energy[h,b] == 0.5*model.bess_units[b]*model.bess_nominal_capacity[b]*model.bess_initial_SOC[b]
    else:
        return model.bess_total_energy[h,b] == model.bess_total_energy[h-1,b]+model.bess_ch_power[h,b]-model.bess_dis_power[h,b]

def bess_charging_level_min(model, h, b):
    return model.bess_total_energy[h, b] >= model.bess_units[b]*model.bess_nominal_capacity[b]*(1-model.bess_depth_of_discharge[b])+model.reserve_bess[h,b]

def bess_charging_level_max(model, h, b):
    return model.bess_total_energy[h, b] <= model.bess_units[b]*model.bess_nominal_capacity[b]

# maximum charging and discharging power depending on the P-ratio
def bess_ch_power_max(model, h, b):
    return model.bess_ch_power[h, b] <= model.bess_units[b]*model.bess_nominal_capacity[b]*model.bess_P_ratio_max[b]

def bess_dis_power_max(model,h,b):
    return model.bess_dis_power[h,b] <= model.bess_units[b]*model.bess_nominal_capacity[b]*model.bess_P_ratio_max[b]


# constraints related to hydro turbine
# max power given by technological limits (size of the turbine)
def ht_power_max(model, h, ht):
    return model.ht_power[h, ht] <= model.ht_nominal_capacity[ht] * model.ht_units_on[h, ht]

# max power given by resource limits (max flow rate of the river)
def ht_power_river(model, h, ht):
    return model.ht_power[h, ht] <= model.input_hydro_res[h, ht] * model.ht_efficiency[ht]

def ht_power_min(model, h, ht):
    return model.ht_power[h, ht] >= model.ht_nominal_capacity[ht] * model.ht_P_min[ht] * model.ht_units_on[h, ht]

def ht_online(model, h, ht):
    return model.ht_units_on[h, ht] <= model.ht_units[ht]
