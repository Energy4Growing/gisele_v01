import os
import shutil
import dash
import base64
import io
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon
import numpy as np
import dash_table
import dash_bootstrap_components as dbc
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
from dash.exceptions import PreventUpdate
from shapely.geometry import Point
from gisele.functions import load, sizing
from gisele import initialization, clustering, processing, collecting, \
    optimization, results, grid, branches
import pyutilib.subprocess.GlobalData

pyutilib.subprocess.GlobalData.DEFINE_SIGNAL_HANDLERS_DEFAULT = False

# creation of all global variables used in the algorithm
gis_columns = pd.DataFrame(columns=['ID', 'X', 'Y', 'Population', 'Elevation',
                                    'Weight'])

mg_columns = pd.DataFrame(columns=['Cluster', 'PV [kW]', 'Wind [kW]',
                                   'Diesel [kW]', 'BESS [kWh]',
                                   'Inverter [kW]', 'Investment Cost [k€]',
                                   'OM Cost [k€]', 'Replace Cost [k€]',
                                   'Total Cost [k€]', 'Energy Produced [MWh]',
                                   'Energy Demand [MWh]', 'LCOE [€/kWh]'])

npc_columns = pd.DataFrame(columns=['Cluster', 'Grid NPC [k€]', 'MG NPC [k€]',
                                     'Grid Energy Consumption [MWh]',
                                     'MG LCOE [€/kWh]',
                                     'Grid LCOE [€/kWh]', 'Best Solution'])

# breaking load profile in half for proper showing in the data table
input_profile = pd.read_csv(r'Input/Load Profile.csv').round(4)
load_profile = pd.DataFrame(columns=['Hour 0-12', 'Power [p.u.]',
                                     'Hour 12-24', 'Power (p.u.)'])
load_profile['Hour 0-12'] = pd.Series(np.arange(12)).astype(int)
load_profile['Hour 12-24'] = pd.Series(np.arange(12, 24)).astype(int)
load_profile['Power [p.u.]'] = input_profile.iloc[0:12, 0].values
load_profile['Power (p.u.)'] = input_profile.iloc[12:24, 0].values
lp_data = load_profile.to_dict('records')

# configuration file, eps and pts values separated by - since they are a range
config = pd.read_csv(r'Input/Configuration.csv')
# config.loc[21, 'Value'] = sorted(list(map(int,
#                                           config.loc[21, 'Value'].split('-'))))
# config.loc[20, 'Value'] = sorted(list(map(int,
#                                           config.loc[20, 'Value'].split('-'))))

# empty map to show as initual output
fig = go.Figure(go.Scattermapbox(
    lat=[''],
    lon=[''],
    mode='markers'))

fig.update_layout(mapbox_style="carto-positron")
fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

# study area definition
lon_point_list = [-65.07295675004093, -64.75263629329811, -64.73311537903679,
                  -65.06630189290638]
lat_point_list = [-17.880592240953966, -17.86581365258916, -18.065431449408248,
                  -18.07471050015602]
polygon_geom = Polygon(zip(lon_point_list, lat_point_list))
study_area = gpd.GeoDataFrame(index=[0], crs=4326,
                              geometry=[polygon_geom])

# initialization of the app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.MINTY])
app.layout = html.Div([
    html.Div([dbc.Row([
        dbc.Col(
            html.Img(
                src=app.get_asset_url("poli_horizontal.png"),
                id="polimi-logo",
                style={"height": "80px", "width": "auto",
                       'textAlign': 'center'},
                className='four columns'),
            width={"size": 2, "offset": 1}, align='center'),
        dbc.Col(
            html.H1('GISEle: GIS for Electrification',
                    style={'textAlign': 'center', 'color': '000000'}
                    ),
            width={"size": 5, "offset": 2}, align='center')

    ], ),
    ]),
    html.Div([dcc.Slider(id='step',
                         min=0,
                         max=5,
                         marks={0: 'Start',
                                1: 'GIS Data Processing', 2: 'Clustering',
                                3: 'Grid Routing', 4: 'Microgrid Sizing',
                                5: 'NPC Analysis'},
                         value=1,
                         )
              ], style={'textAlign': 'center', 'margin': '20px'}),

    html.Div(id='start_div', children=[
        dbc.Row([
            dbc.Col(html.Div(style={'textAlign': 'center'}, children=[
                html.H2(['Introduction'], style={'margin': '20px',
                                                 'color': "#55b298"}),
                dbc.Card([
                    dbc.CardBody(["The GIS for electrification (GISEle) "
                                  "is an open source Python-based tool that "
                                  "uses GIS and terrain analysis to model the "
                                  "area under study, groups loads using a "
                                  "density-based "
                                  "clustering algorithm called DBSCAN and "
                                  "then it uses graph theory to find the "
                                  "least-costly electric network topology "
                                  "that can connect all the people in the "
                                  "area."], style={'textAlign': 'justify'}),
                    dbc.CardFooter(
                        dbc.CardLink("Energy4Growing",
                                     href="http://www.e4g.polimi.it/")),
                ], className="mb-3", style={}),

                dbc.Row([
                    dbc.Col(
                        dbc.Button(
                            'NEXT',
                            size='lg',
                            color='primary',
                            id='next_step_start', n_clicks=0,
                            style={'textAlign': 'center', 'margin': '10px'},
                        ), width={"size": 6, "offset": 6}, align='center'),
                ], justify='around'),
            ]),
                    width={"size": 3, "offset": 0}),

            dbc.Col(html.Div([
                dcc.Graph(
                    id='output_start',
                    figure=fig,
                )
            ]), width={"size": 8, "offset": 0}, align='center'),

        ], justify="around"),
    ]),

    html.Div(id='gis_div', children=[
        dbc.Row([
            dbc.Col(html.Div(style={'textAlign': 'center'}, children=[
                html.H2(['GIS Data Analysis'], style={'color': "#55b298"}),
                dbc.Checklist(id='import_data', switch=True, inline=True,
                              options=[
                                  {'label': 'Download GIS Data',
                                   'value': 'y'},
                              ],
                              # value='y',
                              style={'margin': '15px'}
                              ),
                dbc.Collapse([
                    dbc.Label(['Study Area'], id='studyarea_label'),
                    dbc.Row([
                        dbc.Label('Y1'),
                        dbc.Col(
                            dbc.Input(
                                id='lat1',
                                debounce=True,
                                type='number',
                                value=-17.8805,
                                style={'margin': '1px'})
                        ),
                        dbc.Label('X1'),
                        dbc.Col(
                            dbc.Input(
                                id='lon1',
                                debounce=True,
                                type='number',
                                value=-65.0729,
                                style={'margin': '1px'})
                        ),
                    ]),
                    dbc.Row([
                        dbc.Label('Y2'),
                        dbc.Col(
                            dbc.Input(
                                id='lat2',
                                debounce=True,
                                type='number',
                                value=-17.8658,
                                style={'margin': '1px'})
                        ),
                        dbc.Label('X2'),
                        dbc.Col(
                            dbc.Input(
                                id='lon2',
                                debounce=True,
                                type='number',
                                value=-64.7526,
                                style={'margin': '1px'})
                        ),
                    ]),
                    dbc.Row([
                        dbc.Label('Y3'),
                        dbc.Col(
                            dbc.Input(
                                id='lat3',
                                debounce=True,
                                type='number',
                                value=-18.0654,
                                style={'margin': '1px'})
                        ),
                        dbc.Label('X3'),
                        dbc.Col(
                            dbc.Input(
                                id='lon3',
                                debounce=True,
                                type='number',
                                value=-64.7331,
                                style={'margin': '1px'})
                        ),
                    ]),
                    dbc.Row([
                        dbc.Label('Y4'),
                        dbc.Col(
                            dbc.Input(
                                id='lat4',
                                debounce=True,
                                type='number',
                                value=-18.0747,
                                style={'margin': '1px'})
                        ),
                        dbc.Label('X4'),
                        dbc.Col(
                            dbc.Input(
                                id='lon4',
                                debounce=True,
                                type='number',
                                value=-65.0663,
                                style={'margin': '1px'})
                        ),
                    ]),
                    dbc.Row([
                        dbc.Col(
                            dbc.Checklist(
                                options=[
                                    {"label": "Import Population", "value": 1},
                                ],
                                value=[1],
                                id="import_pop")
                        ),
                        dbc.Col(
                            dcc.Upload(
                                id='upload_pop',
                                children=html.Div([
                                    html.A('Select .csv File')
                                ]),
                                style={
                                    'width': '100%',
                                    'height': '30px',
                                    'lineHeight': '30px',
                                    'borderWidth': '1px',
                                    'borderStyle': 'dashed',
                                    'borderRadius': '5px',
                                    'textAlign': 'center',
                                    'margin': '10px',
                                },
                            ),
                        )
                    ], align='center'),

                ], id='collapse_gis'),
                dbc.Collapse([
                    dcc.Upload(
                        id='upload_csv',
                        children=html.Div([
                            html.A('Import points .csv file')
                        ]),
                        style={
                            'width': '100%',
                            'height': '100px',
                            'lineHeight': '100px',
                            'borderWidth': '2px',
                            'borderStyle': 'dashed',
                            'borderRadius': '8px',
                            'textAlign': 'center',
                            'margin': '10px',
                        },
                    ),
                    html.Div(id='upload_csv_out'),
                ], id='collapse_gis2'),
                dbc.Row([
                    dbc.Col([
                        dbc.Label('CRS'),
                        dbc.Input(
                            id='crs',
                            placeholder='EPSG code..',
                            debounce=True,
                            type='number',
                            value=''
                        ),
                    ]),
                    dbc.Col([
                        dbc.Label('Resolution [meters]'),
                        dbc.Input(
                            id='resolution',
                            placeholder='1000m',
                            debounce=True,
                            type='number',
                            min=100, step=50,
                            value='1000'
                        ),
                    ])
                ], style={'margin': '10px'}),

                html.Div([
                    dbc.Label('Landcover Dataset'),
                    dcc.Dropdown(
                        id='landcover_option',
                        options=[
                            {'label': 'Global Landcover GLC-2000',
                             'value': 'GLC'},
                            {'label': 'Copernicus CGLS-LC100',
                             'value': 'CGLS'},
                            {'label': 'ESACCI',
                             'value': 'ESACCI'},
                            {'label': 'Other',
                             'value': 'Other'},
                        ],
                        value='GLC'
                    )
                ], style={'margin': '15px'}),

                dbc.Row([
                    dbc.Col(
                        dbc.Button(
                            'RUN',
                            size='lg',
                            color='warning',
                            id='create_df', n_clicks=0,
                            style={'textAlign': 'center', 'margin': '10px'},
                        ), width={"size": 6, "offset": 0}, align='center'),
                    dbc.Col(
                        dbc.Button(
                            'NEXT',
                            size='lg',
                            color='primary',
                            id='next_step_gis', n_clicks=0,
                            style={'textAlign': 'center', 'margin': '10px'},
                        ), width={"size": 6, "offset": 0}, align='center'),
                ], justify='around'),
            ]),
                    width={"size": 3, "offset": 0}),

            dbc.Col(html.Div([
                dbc.Spinner(size='lg', color="#4ead84", children=[
                    dbc.Tabs([
                        dbc.Tab(label='Map', label_style={"color": "#55b298"},
                                children=[
                                    dcc.Graph(
                                        id='output_gis',
                                        figure=fig,
                                    )]
                                ),
                        dbc.Tab(label='Table',
                                label_style={"color": "#55b298"},
                                children=[
                                    dash_table.DataTable(
                                        id='datatable_gis',
                                        columns=[
                                            {"name": i, "id": i} for i in
                                            gis_columns.columns
                                        ],
                                        style_table={'height': '450px'},
                                        page_count=1,
                                        page_current=0,
                                        page_size=13,
                                        page_action='custom')]
                                ),
                    ]),
                ])
            ]), width={"size": 8, "offset": 0}, align='center'),

        ], justify="around"),
    ]),

    html.Div(id='cluster_div', children=[
        dbc.Row([
            dbc.Col(html.Div(style={'textAlign': 'center'}, children=[

                html.H5(['Cluster Sensitivity'], style={'margin': '5px',
                                                        'color': "#55b298"},
                        id='cluster_sens_header'),

                dbc.Label('Limits for the MINIMUM POINTS'),
                dcc.RangeSlider(
                    id='pts',
                    allowCross=False,
                    min=10,
                    max=2000,
                    marks={10: '10', 200: '200', 400: '400', 600: '600',
                           800: '800', 1000: '1000', 1200: '1200',
                           1400: '1400,', 1600: '1600', 1800: '1800',
                           2000: '2000'},
                    step=10,
                    value=[300, 700]
                ),

                dbc.Label('Limits for the NEIGHBOURHOOD [meters]'),
                dcc.RangeSlider(
                    id='eps',
                    allowCross=False,
                    min=100,
                    max=5000,
                    marks={100: '100', 500: '500', 1000: '1000', 1500: '1500',
                           2000: '2000', 2500: '2500', 3000: '3000',
                           3500: '3500,', 4000: '4000', 4500: '4500',
                           5000: '5000'},
                    step=100,
                    value=[1200, 1700]
                ),
                dbc.Row([
                    dbc.Col([
                        dbc.Label('Spans'),
                        dbc.Input(
                            debounce=True,
                            bs_size='sm',
                            id='spans',
                            placeholder='',
                            type='number',
                            min=0, max=20, step=1,
                            value='5'),
                    ], width={"size": 4, "offset": 0}, align='center'),
                    dbc.Col([
                        dbc.Button(
                            'Sensitivity',
                            # size='sm',
                            color='warning',
                            id='bt_cluster_sens', n_clicks=0, disabled=False,
                            style={'textAlign': 'center', 'margin': '10px'},
                            className='button-primary'),
                    ], width={"size": 6, "offset": 0}, align='end')
                ], justify="around"),

                html.H5(['Cluster Analysis'], style={'margin': '5px',
                                                     'color': "#55b298"}),
                dbc.Row([
                    dbc.Col([
                        dbc.Label('Final EPS'),
                        dbc.Input(
                            debounce=True,
                            bs_size='sm',
                            id='eps_final',
                            placeholder='',
                            type='number',
                            min=0, max=10000, step=1,
                            value=1500),
                    ]),
                    dbc.Col([
                        dbc.Label('Final minPTS'),
                        dbc.Input(
                            debounce=True,
                            bs_size='sm',
                            id='pts_final',
                            placeholder='..',
                            type='number',
                            min=0, max=10000, step=1,
                            value=500),
                    ])
                ]),
                dbc.Collapse(id='collapse_merge', children=[
                    html.H6(['Choose two clusters to merge'],
                            style={'textAlign': 'center',
                                   'color': "#55b298",
                                   'margin': '5px'}),
                    dbc.Row([
                        dbc.Col([
                            # dbc.Label('Cluster to merge'),
                            dbc.Input(
                                debounce=True,
                                bs_size='sm',
                                id='c1_merge',
                                placeholder='',
                                type='number',
                                min=0, max=99, step=1,
                                value=''),
                        ], width={"size": 3, "offset": 0}, align='center'),
                        dbc.Col([
                            # dbc.Label('Cluster'),
                            dbc.Input(
                                debounce=True,
                                bs_size='sm',
                                id='c2_merge',
                                placeholder='',
                                type='number',
                                min=0, max=99, step=1,
                                value=''),
                        ], width={"size": 3, "offset": 0}, align='center'),
                        dbc.Col([
                            dbc.Button(
                                'Merge',
                                # size='sm',
                                color='warning',
                                id='bt_merge_clusters', n_clicks=0,
                                disabled=False,
                                style={'textAlign': 'center',
                                       'margin': '0px'},
                                className='button-primary'),
                        ], width={"size": 4, "offset": 0}, align='center')
                    ], justify="around", style={'height': -100}),
                ]),
                dbc.Row([
                    dbc.Col(
                        dbc.Button(
                            'RUN',
                            size='lg',
                            color='warning',
                            id='cluster_analysis', n_clicks=0,
                            style={'textAlign': 'center', 'margin': '10px'},
                        ), width={"size": 6, "offset": 0}, align='center'),
                    dbc.Col(
                        dbc.Button(
                            'NEXT',
                            size='lg',
                            color='primary',
                            id='next_step_cluster', n_clicks=0,
                            style={'textAlign': 'center', 'margin': '10px'},
                        ), width={"size": 6, "offset": 0}, align='center'),
                ], justify='around'),
            ]), width={"size": 3, "offset": 0}),

            dbc.Col(html.Div([
                dbc.Spinner(size='lg', color="#55b298", children=[
                    dbc.Tabs([
                        dbc.Tab(label='Map', label_style={"color": "#55b298"},
                                children=[
                                    dcc.Graph(
                                        id='output_cluster',
                                        figure=fig,
                                    )]
                                ),
                        dbc.Tab(label='Sensitivity',
                                label_style={"color": "#55b298"}, children=[
                                dcc.Graph(
                                    id='output_sens',
                                    figure=fig,
                                )]
                                ),
                    ]),
                ])
            ]), width={"size": 8, "offset": 0}, align='center'),

        ], justify="around"),
    ]),

    html.Div(id='grid_div', children=[
        dbc.Row([
            dbc.Col(html.Div(style={'textAlign': 'center'}, children=[
                html.H2(['Grid Routing'], style={'color': "#55b298"}),
                dbc.Checklist(id='full_ele', switch=True, inline=True,
                              options=[
                                  {'label': 'Total Electrification',
                                   'value': 'y'},
                              ],
                              value=[],
                              style={'textAlign': 'center', 'margin': '15px'},
                              ),
                dbc.Row([
                    dbc.Col([
                        dbc.Label('Population Threshold'),
                        dbc.Input(
                            id='pop_thresh',
                            placeholder='',
                            debounce=True,
                            type='number',
                            min=0, max=1000, step=1,
                            value='100')
                    ]),
                    dbc.Col([
                        dbc.Label('Line Base Cost'),
                        dbc.Input(
                            id='line_bc',
                            placeholder='[€/km]',
                            debounce=True,
                            type='number',
                            value='')
                    ]),
                    dbc.Col([
                        dbc.Label('Load per Capita'),
                        dbc.Input(
                            id='pop_load',
                            placeholder='[kW]',
                            debounce=True,
                            type='number',
                            value='')
                    ])
                ]),
                # dbc.Row([
                #     dbc.Col([
                #         # dbc.Label(['HV/MV Substation cost'], style={'textSize': '1px'}),
                #         html.Div(['HV/MV Substation cost'],
                #                  style={'font-size ': '1px'}),
                #         dbc.Input(
                #             id='sub_cost_HV',
                #             placeholder='Enter a value [€]..',
                #             debounce=True,
                #             min=0, max=999999999,
                #             type='number',
                #             value=''
                #         ),
                #     ]),
                #     dbc.Col([
                #         dbc.Label('MV/LV Substation cost'),
                #         dbc.Input(
                #             id='sub_cost_MV',
                #             placeholder='Enter a value [€]..',
                #             debounce=True,
                #             min=0, max=999999999,
                #             type='number',
                #             value=''
                #         ),
                #     ])
                # ]),
                dbc.Checklist(id='branch', switch=True, inline=True,
                              options=[
                                  {'label': 'Branch Strategy',
                                   'value': 'y'},
                              ],
                              value=[],
                              style={'margin': '15px'}
                              ),

                dbc.Collapse(id='collapse_branch', children=[
                    dbc.Row([
                        dbc.Col([
                            dbc.Label(
                                'Population Treshold (Main Branches)'),
                            dbc.Input(
                                debounce=True,
                                id='pop_thresh_lr',
                                type='number',
                                min=0, max=1000, step=10,
                                value='200'),
                        ]),
                        dbc.Col([
                            dbc.Label(
                                'Line base cost (Collaterals)'),
                            dbc.Input(
                                debounce=True,
                                id='line_bc_col',
                                placeholder='[€/km]',
                                type='number',
                                value='')
                        ]),
                    ]),
                ]),

                dbc.Row([
                    dbc.Col(
                        dbc.Button(
                            'RUN',
                            size='lg',
                            color='warning',
                            id='grid_routing', n_clicks=0,
                            style={'textAlign': 'center', 'margin': '10px'},
                        ), width={"size": 6, "offset": 0}, align='center'),
                    dbc.Col(
                        dbc.Button(
                            'NEXT',
                            size='lg',
                            color='primary',
                            id='next_step_routing', n_clicks=0,
                            style={'textAlign': 'center', 'margin': '10px'},
                        ), width={"size": 6, "offset": 0}, align='center'),
                ], justify='around'),
            ]),
                    width={"size": 3, "offset": 0}, align='center'),

            dbc.Col(html.Div([
                dbc.Spinner(size='lg', color="#55b298", children=[
                    dbc.Tabs([
                        dbc.Tab(label='Map', label_style={"color": "#55b298"},
                                children=[
                                    dcc.Graph(
                                        id='output_grid',
                                        figure=fig,
                                    )]
                                ),
                        dbc.Tab(label='Table',
                                label_style={"color": "#55b298"},
                                children=[
                                    dash_table.DataTable(
                                        id='datatable_grid',
                                        columns=[],
                                        style_header={
                                            'whiteSpace': 'normal',
                                            'height': 'auto',
                                            'width': '30px',
                                            'textAlign': 'center'},
                                        style_table={'height': '450px'},
                                        page_count=1,
                                        page_current=0,
                                        page_size=13,
                                        page_action='custom',

                                        sort_action='custom',
                                        sort_mode='single',
                                        sort_by=[])]
                                ),
                    ]),
                ])
            ]), width={"size": 8, "offset": 0}, align='center'),

        ], justify="around"),
    ]),

    html.Div(id='mg_div', children=[
        dbc.Row([
            dbc.Col(html.Div(style={'textAlign': 'center'}, children=[
                html.H2(['Microgrid Sizing'], style={'color': "#55b298"}),
                dbc.Checklist(id='import_res', switch=True, inline=True,
                              options=[
                                  {'label': 'Download RES data',
                                   'value': 'y'},
                              ],
                              value='y',
                              style={'textAlign': 'center', 'margin': '15px'},
                              ),

                dbc.Row([
                    dbc.Col([
                        dbc.Label('Upload a Daily Load Profile'),
                        dcc.Upload(
                            id='upload_loadprofile',
                            children=html.Div([
                                'Drag and Drop or ',
                                html.A('Select File')
                            ]),
                            style={
                                'width': '100%',
                                'height': '60px',
                                'lineHeight': '60px',
                                'borderWidth': '1px',
                                'borderStyle': 'dashed',
                                'borderRadius': '5px',
                                'textAlign': 'center',
                                'margin': '10px'
                            },
                        ),
                    ])
                ]),
                html.Div([
                    dbc.Label('Wind Turbine Model'),
                    dcc.Dropdown(
                        id='wt',
                        options=[
                            {'label': 'Nordex N27 150',
                             'value': 'Nordex N27 150'},
                            {'label': 'Alstom Eco 80',
                             'value': 'Alstom Eco 80'},
                            {'label': 'Enercon E40 500',
                             'value': 'Enercon E40 500'},
                            {'label': 'Vestas V27 225',
                             'value': 'Vestas V27 225'}
                        ],
                        value='Nordex N27 150'
                    )
                ], style={'margin': '15px'}),

                dbc.Row([
                    dbc.Col(
                        dbc.Button(
                            'RUN',
                            size='lg',
                            color='warning',
                            id='mg_sizing', n_clicks=0,
                            style={'textAlign': 'center', 'margin': '10px'},
                        ), width={"size": 6, "offset": 0}, align='center'),
                    dbc.Col(
                        dbc.Button(
                            'NEXT',
                            size='lg',
                            color='primary',
                            id='next_step_mg', n_clicks=0,
                            style={'textAlign': 'center', 'margin': '10px'},
                        ), width={"size": 6, "offset": 0}, align='center'),
                ], justify='around'),
            ]),
                    width={"size": 3, "offset": 0}, align='center'),

            dbc.Col(html.Div([
                dbc.Spinner(size='lg', color="#55b298", children=[
                    dbc.Tabs([
                        dbc.Tab(label='Map', label_style={"color": "#55b298"},
                                children=[
                                    dcc.Graph(
                                        id='output_mg',
                                        figure=fig,
                                    )]
                                ),
                        dbc.Tab(label='Microgrids',
                                label_style={"color": "#55b298"},
                                children=[
                                    dash_table.DataTable(
                                        id='datatable_mg',
                                        columns=[
                                            {"name": i, "id": i} for i in
                                            mg_columns.columns
                                        ],
                                        style_header={
                                            'whiteSpace': 'normal',
                                            'height': 'auto',
                                            'width': '30px',
                                            'textAlign': 'center'
                                        },
                                        style_table={'height': '450px'},
                                        page_count=1,
                                        page_current=0,
                                        page_size=13,
                                        page_action='custom',
                                        sort_action='custom',
                                        sort_mode='single',
                                        sort_by=[])
                                ]),
                        dbc.Tab(label='Load Profile',
                                label_style={"color": "#55b298"},
                                children=[
                                    dbc.Row([
                                        dbc.Col([
                                            dash_table.DataTable(
                                                id='datatable_load_profile',
                                                columns=[{"name": i, "id": i}
                                                         for i in
                                                         load_profile.columns],
                                                data=lp_data,
                                                editable=True,
                                                style_header={
                                                    'whiteSpace': 'normal',
                                                    'height': 'auto',
                                                    'width': '30px',
                                                    'textAlign': 'center'
                                                },
                                                style_table={
                                                    'height': '450px'},
                                                page_count=1,
                                                page_current=0,
                                                page_size=13,
                                                page_action='custom'),
                                        ], width={"size": 5, "offset": 0},
                                            align='center'),
                                        dbc.Col([
                                            dcc.Graph(id='load_profile_graph')
                                        ], width={"size": 7, "offset": 0},
                                            align='center'),
                                    ])

                                ]),
                    ]),
                ])
            ]), width={"size": 8, "offset": 0}, align='center'),

        ], justify="around"),

    ]),

    html.Div(id='npc_div', children=[
        dbc.Row([
            dbc.Col(html.Div(style={'textAlign': 'center'}, children=[
                html.H2(['NPC Analysis'], style={'color': "#55b298"}),
                dbc.Row([
                    dbc.Col([
                        dbc.Label('Cost of Electricity'),
                        dbc.Input(
                            id='coe',
                            placeholder='[€/kWh]',
                            debounce=True,
                            min=0, max=9999,step=0.01,
                            type='number',
                            value=''
                        ),
                    ]),
                    dbc.Col([
                        dbc.Label('Inflation Rate'),
                        dbc.Input(
                            id='grid_ir',
                            placeholder='[%/year]',
                            debounce=True,
                            min=0, max=1, step=0.01,
                            type='number',
                            value='0.01'
                        ),
                    ])
                ]),

                dbc.Row([
                    dbc.Col([
                        dbc.Label('Grid Lifetime'),
                        dbc.Input(
                            id='grid_lifetime',
                            placeholder='[y]',
                            debounce=True,
                            min=1, max=100, step=1,
                            type='number',
                            value='40'
                        ),
                    ]),
                    dbc.Col([
                        dbc.Label('Grid O&M Costs'),
                        dbc.Input(
                            debounce=True,
                            id='grid_om',
                            placeholder='[% of total]',
                            min=0, max=1, step=0.01,
                            type='number',
                            value='0.01'
                        ),
                    ])
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Label('Max Power along lines'),
                        dbc.Input(
                            id='p_max_lines',
                            placeholder='[kW]',
                            debounce=True,
                            min=0, max=9999,step=0.01,
                            type='number',
                            value=''
                        ),
                    ]),
    ]),
                dcc.Upload(
                    id='upload_subs',
                    children=html.Div([
                        html.A('Import substations .csv file')
                    ]),
                    style={
                        'width': '100%',
                        'height': '30px',
                        'lineHeight': '30px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'margin': '10px',
                    },
                ),

                html.Div(id='upload_subs_out'),


                dbc.Row([
                    dbc.Col(
                        dbc.Button(
                            'RUN',
                            size='lg',
                            color='warning',
                            id='npc_btn', n_clicks=0,
                            style={'textAlign': 'center', 'margin': '10px'},
                        ), width={"size": 6, "offset": 0}, align='center'),
                ], justify='start'),
            ]),
                    width={"size": 3, "offset": 0}, align='center'),

            dbc.Col(html.Div([
                dbc.Spinner(size='lg', color="#55b298", children=[
                    dbc.Tabs([
                        dbc.Tab(label='Map', label_style={"color": "#55b298"},
                                children=[
                                    dcc.Graph(
                                        id='output_npc',
                                        figure=fig,
                                    )]
                                ),

                        dbc.Tab(label='Table',
                                label_style={"color": "#55b298"},
                                children=[
                                    dash_table.DataTable(
                                        id='datatable_grid_final',
                                        columns=[]
                                        ,
                                        style_header={
                                            'whiteSpace': 'normal',
                                            'height': 'auto',
                                            'width': '30px',
                                            'textAlign': 'center'
                                        },
                                        style_table={'height': '450px'},
                                        page_count=1,
                                        page_current=0,
                                        page_size=13,
                                        page_action='custom',
                                        sort_action='custom',
                                        sort_mode='single',
                                        sort_by=[]
                                    )

                                ]
                                ),
                    ]),
                ])
            ]), width={"size": 8, "offset": 0}, align='center'),

        ], justify="around"),

    ]),
    html.P(id='config_out', style={'display': 'none'}),
    html.P(id='upload_pop_out', style={'display': 'none'}),
    html.P(id='studyarea_out', style={'display': 'none'}),
    dbc.Tooltip(
        "WARNING: This option could greatly increases the computation time, ",
        target="full_ele",
    ),
    dbc.Tooltip(
        "WARNING: This option could greatly increases the computation time, ",
        target="branch",
    ),
    dbc.Tooltip(
        "Select a range of values for the input parameters and the number"
        "of spans between this interval to show in the sensitivity graph."
        "The goal should be to maximize the % of clustered people maintaining "
        "a high value of people/km²."
        ,
        target="cluster_sens_header",
    ),
    dbc.Tooltip(
        "Provide a set of four points, with coordinates in degrees (EPSG:4326)"
        ", which will form a rectangular polygon that limits the area under "
        "analysis."
        ,
        target="studyarea_label",
    ),
])


@app.callback(Output('step', 'value'),
              [Input('next_step_start', 'n_clicks'),
               Input('next_step_gis', 'n_clicks'),
               Input('next_step_cluster', 'n_clicks'),
               Input('next_step_routing', 'n_clicks'),
               Input('next_step_mg', 'n_clicks')])
def go_next_step(next_step_start, next_step_gis, next_step_cluster,
                 next_step_routing, next_step_mg):
    """ Changes the value of the step selection according to which NEXT button
    that was pressed"""
    button_pressed = dash.callback_context.triggered[0]['prop_id'].split('.')[
        0]
    if button_pressed == 'next_step_start':
        return 1
    if button_pressed == 'next_step_gis':
        return 2
    if button_pressed == 'next_step_cluster':
        return 3
    if button_pressed == 'next_step_routing':
        return 4
    if button_pressed == 'next_step_mg':
        return 5
    else:
        return 0


@app.callback(Output('start_div', 'style'),
              [Input('step', 'value')])
def change_interface(step):
    """ Changes the html.Div of whole page according to the step selected """
    if step == 0:
        return {'textAlign': 'center'}
    else:
        return {'display': 'none'}


@app.callback(Output('gis_div', 'style'),
              [Input('step', 'value')])
def change_interface(step):
    """ Changes the html.Div of whole page according to the step selected """
    if step == 1:
        return {'textAlign': 'center'}
    else:
        return {'display': 'none'}


@app.callback(Output('cluster_div', 'style'),
              [Input('step', 'value')])
def change_interface(step):
    """ Changes the html.Div of whole page according to the step selected """
    if step == 2:
        return {'textAlign': 'center'}
    else:
        return {'display': 'none'}


@app.callback(Output('grid_div', 'style'),
              [Input('step', 'value')])
def change_interface(step):
    """ Changes the html.Div of whole page according to the step selected """
    if step == 3:
        return {'textAlign': 'center'}
    else:
        return {'display': 'none'}


@app.callback(Output('mg_div', 'style'),
              [Input('step', 'value')])
def change_interface(step):
    """ Changes the html.Div of whole page according to the step selected """
    if step == 4:
        return {'textAlign': 'center'}
    else:
        return {'display': 'none'}


@app.callback(Output('npc_div', 'style'),
              [Input('step', 'value')])
def change_interface(step):
    """ Changes the html.Div of whole page according to the step selected """
    if step == 5:
        return {'textAlign': 'center'}
    else:
        return {'display': 'none'}


@app.callback([Output('pop_thresh_lr', 'disabled'),
               Output('line_bc_col', 'disabled')],
              [Input('branch', 'value')])
def branch_options(branch):
    """ Enables or not the options for branch technique according to switch"""
    if not branch:
        return True, True
    else:
        return False, False


@app.callback(Output("collapse_gis", "is_open"),
              [Input("import_data", "value")])
def toggle_collapse_gis(value):
    if isinstance(value, list):
        if not value:
            return False
        elif value[0] == 'y':
            return True
    return False


@app.callback(Output("collapse_gis2", "is_open"),
              [Input("import_data", "value")])
def toggle_collapse_gis(value):
    if isinstance(value, list):
        if not value:
            return True
        elif value[0] == 'y':
            return False
    return True


@app.callback(Output("collapse_merge", "is_open"),
              [Input("cluster_analysis", "n_clicks")])
def toggle_collapse_merge(n_clicks):
    if n_clicks >= 1:
        return True
    return False


@app.callback(Output("collapse_branch", "is_open"),
              [Input("branch", "value")])
def toggle_collapse_merge(value):
    if isinstance(value, list):
        if not value:
            return False
        elif value[0] == 'y':
            return True
    return False


@app.callback(Output('upload_pop', 'disabled'),
              [Input('import_pop', 'value')])
def disable_upload_pop(value):
    if value:
        return False
    else:
        return True


@app.callback(Output('upload_pop_out', 'children'),
              [Input('upload_pop', 'contents')])
def read_upload_pop(contents):
    if contents is not None:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        df.to_csv(r'Input/imported_pop.csv', index=False)
    return '_'


@app.callback(Output('upload_csv_out', 'children'),
              [Input('upload_csv', 'contents')],
              [State('upload_csv', 'filename')])
def read_upload_csv(contents, filename):
    if dash.callback_context.triggered:
        if contents is not None:
            if not 'csv' in filename:
                return html.P('The selected file is not a CSV table.')
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            df.to_csv(r'Input/imported_csv.csv', index=False)
            return html.P('CSV file successfully imported.')
        return html.P('No files selected.')
    return html.P('No files selected.')


@app.callback(Output('upload_subs_out', 'children'),
              [Input('upload_subs', 'contents')],
              [State('upload_subs', 'filename')])
def read_upload_csv(contents, filename):
    if dash.callback_context.triggered:
        if contents is not None:
            if not 'csv' in filename:
                return html.P('The selected file is not a CSV table.')
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            df.to_csv(r'Input/imported_subs.csv', index=False)
            return html.P('CSV file successfully imported.')
        return html.P('No files selected.')
    return html.P('No files selected.')


@app.callback(Output('studyarea_out', 'children'),
              [Input('lat1', 'value'), Input('lat2', 'value'),
               Input('lat3', 'value'), Input('lat4', 'value'),
               Input('lon1', 'value'), Input('lon2', 'value'),
               Input('lon3', 'value'), Input('lon4', 'value')])
def create_study_area(lat1, lat2, lat3, lat4, lon1, lon2, lon3, lon4):
    if dash.callback_context.triggered:
        lat_points = [lat1, lat2, lat3, lat4]
        lon_points = [lon1, lon2, lon3, lon4]
        study_area.geometry = [Polygon(zip(lon_points, lat_points))]
        study_area.to_file(r'Input/study_area.shp')
    return '_'


@app.callback(Output('config_out', 'children'),
              [Input('import_data', 'value'),
               Input('crs', 'value'),
               Input('resolution', 'value'),
               Input('pop_thresh', 'value'),
               Input('line_bc', 'value'),
               Input('pop_load', 'value'),
               Input('branch', 'value'),
               Input('pop_thresh_lr', 'value'),
               Input('line_bc_col', 'value'),
               Input('full_ele', 'value'),
               Input('wt', 'value'),
               Input('coe', 'value'),
               Input('grid_ir', 'value'),
               Input('grid_om', 'value'),
               Input('grid_lifetime', 'value'),
               Input('eps', 'value'),
               Input('pts', 'value'),
               Input('spans', 'value'),
               Input('eps_final', 'value'),
               Input('pts_final', 'value'),
               Input('c1_merge', 'value'),
               Input('c2_merge', 'value'),
               Input('landcover_option', 'value'),
               Input('p_max_lines','value')])
def configuration(import_data, crs, resolution,
                  pop_thresh, line_bc, pop_load,
                  branch, pop_thresh_lr, line_bc_col, full_ele, wt, coe,
                  grid_ir, grid_om, grid_lifetime, eps, pts, spans, eps_final,
                  pts_final, c1_merge, c2_merge, landcover_option,p_max_lines):
    """ Reads every change of input in the UI and updates the configuration
    file accordingly """
    ctx = dash.callback_context
    if ctx.triggered[0]['value'] is not None:
        para_index = config[config['Parameter'] ==
                            ctx.triggered[0]['prop_id'].split('.')[0]].index

        if isinstance(ctx.triggered[0]['value'], list): #if this is just for eps and pts it is substituted by the  lines after and can be removed

            if not ctx.triggered[0]['value']:
                config.loc[para_index, 'Value'] = 'no'
            elif ctx.triggered[0]['value'][0] == 'y':
                config.loc[para_index, 'Value'] = 'yes'
            elif isinstance(ctx.triggered[0]['value'][0], int):
                config.values[para_index[0], 1] = ctx.triggered[0]['value']
        else:
            config.loc[para_index, 'Value'] = ctx.triggered[0]['value']
        if ctx.triggered[0]['prop_id'] =='eps.value':
            config.iloc[20,1] == ctx.triggered[0]['value'][0]
            config.iloc[20,2] == ctx.triggered[0]['value'][1]

        elif ctx.triggered[0]['prop_id'] =='pts.value':
            config.iloc[21,1] == ctx.triggered[0]['value'][0]
            config.iloc[21,2] == ctx.triggered[0]['value'][1]

        msg = 'Parameter changed: ' + str(
            ctx.triggered[0]['prop_id'].split('.')[0])
        print(config)
        # todo -> update config csv file, need to check parameters are saved properly
        config.to_csv('Input/Configuration.csv',index=False)
    else:
        raise PreventUpdate
    return html.Div(msg)


@app.callback(
    Output('datatable_gis', 'page_count'),
              [Input('create_df', 'n_clicks')],
              [State('import_pop', 'value')])
def create_dataframe(create_df, import_pop_value):
    """ Runs the functions for creating the geodataframe when the button RUN
    present in the GIS interface is pressed """
    data_import = config.iloc[0, 1]
    input_csv = 'imported_csv'
    crs = int(config.iloc[3, 1])
    resolution = float(config.iloc[4, 1])
    landcover_option = (config.iloc[27, 1])
    unit = 1
    step = 1
    if dash.callback_context.triggered[0]['prop_id'] == 'create_df.n_clicks':
        ##### remove all files from previous run ######
        for file in os.listdir('Output'):
            shutil.rmtree('Output/'+file, ignore_errors=True)
        ###create new directories ####
        os.makedirs('Output/Datasets')
        os.makedirs('Output/Clusters')
        if data_import == 'yes':
            collecting.data_gathering(crs, study_area)
            landcover_option = 'CGLS'
            if not import_pop_value:
                df = processing.create_mesh(study_area, crs, resolution)
            else:
                imported_pop = pd.read_csv(r'Input/imported_pop.csv')
                df = processing.create_mesh(study_area, crs, resolution,
                                            imported_pop)
            df_weighted = initialization.weighting(df, resolution,
                                                   landcover_option)

            geo_df, pop_points = \
                initialization.creating_geodataframe(df_weighted, crs,
                                                     unit, input_csv, step)
            geo_df['Weight'] = geo_df['Weight'].astype('float') #sometimes it is saved as strings
            geo_df.to_file(r"Output/Datasets/geo_df_json",
                           driver='GeoJSON')
        else:
            df = pd.read_csv(r'Input/' + input_csv + '.csv', sep=',')
            print("Input files successfully imported.")
            df_weighted = initialization.weighting(df, resolution,
                                                   landcover_option)
            geo_df, pop_points = \
                initialization.creating_geodataframe(df_weighted, crs,
                                                     unit, input_csv, step)
            geo_df.to_file(r"Output/Datasets/geo_df_json", driver='GeoJSON')
            initialization.roads_import(geo_df,crs)
        geo_df = geo_df.to_crs(epsg=4326)
        # fig2 = go.Figure(go.Scattermapbox(
        #
        #     name='GeoDataFrame',
        #     lat=geo_df.geometry.y,
        #     lon=geo_df.geometry.x,
        #     mode='markers',
        #     marker=go.scattermapbox.Marker(
        #         size=10,
        #         showscale=True,
        #         color=geo_df.Population,
        #         opacity=0.8,
        #         colorbar=dict(title='People')
        #     ),
        #     text=list(
        #         zip(geo_df.ID, geo_df.Weight, geo_df.Population.round(1))),
        #     hoverinfo='text',
        #     below="''"
        # ))
        # fig2.update_layout(mapbox_style="carto-positron")
        # fig2.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        # fig2.update_layout(mapbox_zoom=8.5,
        #                    mapbox_center={"lat": geo_df.geometry.y[
        #                        (int(geo_df.shape[0] / 2))],
        #                                   "lon": geo_df.geometry.x[
        #                                       (int(geo_df.shape[0] / 2))]})

        return  round(geo_df.shape[0] / 13, 0) + 1
    else:
        return 1


@app.callback(Output('output_sens', 'figure'),
              [Input('bt_cluster_sens', 'n_clicks')])
def cluster_sensitivity(bt_cluster_sens):
    """ Checks if the button SENSITIVITY was pressed, if yes run the code and
     and changes the bt_out to a value that will call the change_interface
     function """
    if bt_cluster_sens > 0:
        resolution = float(config.iloc[4, 1])
        eps_1=float(config.iloc[20, 1])
        eps_2 = float(config.iloc[20, 2])
        pts_1=float(config.iloc[21, 1])
        pts_2 = float(config.iloc[21, 2])
        # eps = list(config.iloc[20, 1])
        # pts = list(config.iloc[21, 1])
        eps =list([eps_1,eps_2])
        pts=list([pts_1,pts_2])
        spans = int(config.iloc[22, 1])

        geo_df = gpd.read_file(r"Output/Datasets/geo_df_json")
        loc = {'x': geo_df['X'], 'y': geo_df['Y'], 'z': geo_df['Elevation']}
        pop_points = pd.DataFrame(data=loc).values
        fig_sens = clustering.sensitivity(resolution, pop_points, geo_df, eps,
                                          pts,
                                          int(spans))
        return fig_sens
    raise PreventUpdate


@app.callback(Output('output_cluster', 'figure'),
              [Input('cluster_analysis', 'n_clicks'),
               Input('bt_merge_clusters', 'n_clicks'),
               Input('step' , 'value')])
def analysis(cluster_analysis, bt_merge_clusters,step):
    """ Checks if the button RUN GISELE was pressed, if yes run the code and
     and changes the bt_out to a value that will call the change_interface
     function """
    eps_final = int(config.iloc[23, 1])
    pts_final = int(config.iloc[24, 1])
    c1_merge = int(config.iloc[25, 1])
    c2_merge = int(config.iloc[26, 1])
    button_pressed = [p['prop_id'] for p in dash.callback_context.triggered][0]
    pop_load = float(config.iloc[6, 1])
    #todo -> improve this visualization, not loading the graph each time this page is entered
    if 'cluster_analysis' in button_pressed:
        for file in os.listdir('Output'):
            if file!='Datasets' and file!='Clusters':
                shutil.rmtree('Output/'+file, ignore_errors=True)
        geo_df = gpd.read_file(r"Output/Datasets/geo_df_json")
        loc = {'x': geo_df['X'], 'y': geo_df['Y'], 'z': geo_df['Elevation']}
        pop_points = pd.DataFrame(data=loc).values

        geo_df_clustered, clusters_list = \
            clustering.analysis(pop_points, geo_df, pop_load,
                                eps_final, pts_final)

        fig_clusters = clustering.plot_clusters(geo_df_clustered,
                                                clusters_list)
        clusters_list.to_csv(r"Output/Clusters/clusters_list.csv",
                             index=False)
        geo_df_clustered.to_file(r"Output/Clusters/geo_df_clustered.json",
                                 driver='GeoJSON')
        return fig_clusters

    elif 'bt_merge_clusters' in button_pressed:
        geo_df_clustered = \
            gpd.read_file(r"Output/Clusters/geo_df_clustered.json")
        geo_df_clustered.loc[geo_df_clustered['Cluster'] ==
                             c2_merge, 'Cluster'] = c1_merge

        clusters_list = pd.read_csv(r"Output/Clusters/clusters_list.csv")
        drop_index = \
            clusters_list.index[clusters_list['Cluster'] == c2_merge][0]
        clusters_list = clusters_list.drop(index=drop_index)

        fig_merged = clustering.plot_clusters(geo_df_clustered,
                                              clusters_list)

        clusters_list.to_csv(r"Output/Clusters/clusters_list.csv",
                             index=False)
        geo_df_clustered.to_file(r"Output/Clusters/geo_df_clustered.json",
                                 driver='GeoJSON')
        return fig_merged

    elif step ==2:
        if os.path.isfile(r'Output/Clusters/geo_df_clustered.json') and os.path.isfile(r'Output/Clusters/clusters_list.csv'):
            geo_df_clustered = \
                gpd.read_file(r"Output/Clusters/geo_df_clustered.json")
            clusters_list = pd.read_csv(r"Output/Clusters/clusters_list.csv")

            fig_clusters = clustering.plot_clusters(geo_df_clustered,
                                                  clusters_list)
            return fig_clusters


    raise PreventUpdate


@app.callback(Output('output_grid', 'figure'),
              [Input('grid_routing', 'n_clicks')])
def routing(grid_routing):
    if grid_routing >= 1:
        for file in os.listdir('Output'):
            if file not in ('Datasets','Clusters','Grids','Branches'):
                shutil.rmtree('Output/' + file, ignore_errors=True)

        input_csv = 'imported_csv'
        input_sub = 'imported_subs'
        resolution = float(config.iloc[4, 1])
        pop_load = float(config.iloc[6, 1])
        pop_thresh = float(config.iloc[7, 1])
        line_bc = float(config.iloc[8, 1])
        sub_cost_hv = float(config.iloc[9, 1])
        sub_cost_mv = float(config.iloc[10, 1])
        branch = config.iloc[11, 1]
        pop_thresh_lr = float(config.iloc[12, 1])
        line_bc_col = float(config.iloc[13, 1])
        full_ele = config.iloc[14, 1]
        geo_df = gpd.read_file(r"Output/Datasets/geo_df_json")
        geo_df_clustered = \
            gpd.read_file(r"Output/Clusters/geo_df_clustered.json")
        clusters_list = pd.read_csv(r"Output/Clusters/clusters_list.csv")
        clusters_list.index = clusters_list.Cluster.values

        if branch == 'no':
            shutil.rmtree('Output/Grids', ignore_errors=True)
            os.makedirs('Output/Grids')
            grid_resume, gdf_roads, roads_segments = \
                grid.routing(geo_df_clustered, geo_df, clusters_list,
                             resolution, pop_thresh, line_bc,
                              full_ele)

            # grid_resume_opt = optimization.connections(geo_df, grid_resume,
            #                                            resolution, line_bc,
            #                                            branch, input_sub,
            #                                            gdf_roads,
            #                                            roads_segments)

            fig_grid = results.graph(geo_df_clustered, clusters_list, branch,
                                     grid_resume,  pop_thresh,
                                     full_ele)

        elif branch == 'yes':
            shutil.rmtree('Output/Branches', ignore_errors=True)
            os.makedirs('Output/Branches')
            gdf_lr = branches.reduce_resolution(input_csv, geo_df, resolution,
                                                geo_df_clustered,
                                                clusters_list)

            grid_resume, substations, gdf_roads, roads_segments = \
                branches.routing(geo_df_clustered, geo_df, clusters_list,
                                 resolution, pop_thresh, input_sub, line_bc,
                                 sub_cost_hv, sub_cost_mv, pop_load, gdf_lr,
                                 pop_thresh_lr, line_bc_col, full_ele)

            # grid_resume_opt = optimization.connections(geo_df, grid_resume,
            #                                            resolution, line_bc,
            #                                            branch, input_sub,
            #                                            gdf_roads,
            #                                            roads_segments)

            fig_grid = results.graph(geo_df_clustered, clusters_list, branch,
                                     grid_resume, pop_thresh,
                                     full_ele)

        return fig_grid
    else:
        return fig


@app.callback(Output('output_mg', 'figure'),
              [Input('mg_sizing', 'n_clicks')])
def microgrid_size(mg_sizing):
    grid_lifetime = int(config.iloc[19, 1])
    wt = (config.iloc[15, 1])

    if mg_sizing > 0:
        for file in os.listdir('Output'):
            if file not in ('Datasets','Clusters','Grids','Branches'):
                shutil.rmtree('Output/' + file, ignore_errors=True)
        os.makedirs('Output/Microgrids')

        geo_df_clustered = \
            gpd.read_file(r"Output/Clusters/geo_df_clustered.json")

        clusters_list = pd.read_csv(r"Output/Clusters/clusters_list.csv")
        clusters_list.index = clusters_list.Cluster.values

        yearly_profile, years, total_energy = load(clusters_list,
                                                   grid_lifetime,
                                                   input_profile)

        mg = sizing(yearly_profile, clusters_list, geo_df_clustered, wt, years)
        fig_mg=results.graph_mg(mg,geo_df_clustered,clusters_list)
        return fig_mg
    else:
        return fig


@app.callback(Output('output_npc', 'figure'),
              [Input('npc_btn', 'n_clicks')])
def npc_computation(npc_btn):
    global final_npc
    branch = config.iloc[11, 1]
    full_ele = config.iloc[14, 1]
    input_sub = 'imported_subs'
    pop_thresh = float(config.iloc[7, 1])
    coe = float(config.iloc[16, 1])
    p_max_lines =float(config.iloc[28, 1])
    grid_om = float(config.iloc[18, 1])
    grid_ir = float(config.iloc[17, 1])
    grid_lifetime = int(config.iloc[19, 1])
    resolution = float(config.iloc[4, 1])
    line_bc = float(config.iloc[8, 1])

    if npc_btn > 0:
        for file in os.listdir('Output'):
            if file not in ('Datasets','Clusters','Grids','Branches','Microgrids'):
                shutil.rmtree('Output/' + file, ignore_errors=True)
        os.makedirs('Output/NPC')

        geo_df = gpd.read_file(r"Output/Datasets/geo_df_json")
        geo_df_clustered = \
            gpd.read_file(r"Output/Clusters/geo_df_clustered.json")
        clusters_list = pd.read_csv(r"Output/Clusters/clusters_list.csv")
        clusters_list.index = clusters_list.Cluster.values
        substations = pd.read_csv(r'Input/' + input_sub + '.csv')
        geometry = [Point(xy) for xy in
                    zip(substations['X'], substations['Y'])]
        substations = gpd.GeoDataFrame(substations, geometry=geometry,
                                       crs=geo_df.crs)

        mg = pd.read_csv('Output/Microgrids/microgrids.csv')
        mg.index = mg.Cluster.values
        total_energy = pd.read_csv('Output/Microgrids/Grid_energy.csv')
        total_energy.index = total_energy.Cluster.values

        if branch == 'yes':
            grid_resume = pd.read_csv(r'Output/Branches/grid_resume.csv')
            grid_resume.index = grid_resume.Cluster.values

        else:
            grid_resume = pd.read_csv(r'Output/Grids/grid_resume.csv')
            grid_resume.index = grid_resume.Cluster.values
            # all_connections_opt = \
                # gpd.read_file(r'Output/Grids/all_connections_opt.shp')

        grid_resume_opt = \
            optimization.milp_npc(geo_df_clustered, grid_resume,
                                   substations, mg, total_energy, grid_om, coe,
                                   grid_ir, grid_lifetime, branch, line_bc,
                                   resolution,p_max_lines)

        fig_grid = results.graph(geo_df_clustered, clusters_list, branch,
                                 grid_resume_opt, pop_thresh,
                                 full_ele, substations)
        if branch=='yes':
            file='Output/Branches/all_connections_opt'
            if os.path.isfile(file+'.shp'):
                results.line_break(file, fig_grid, 'black')

        else:
            file='Output/Grids/all_connections_opt'
            if os.path.isfile(file+'.shp'):
                results.line_break(file, fig_grid, 'black')
        # else:
        #     file = 'Output/Grids/all_connections_opt'
        #     try:
        #         f = open(file + 'shp')
        #         results.line_break(file, fig_grid, 'black')
        #     except IOError:
        #         print("File not accessible")
        #     finally:
        #         f.close()

        # final_lcoe = lcoe_analysis(clusters_list, total_energy,
        #                            grid_resume_opt, mg, coe, grid_ir, grid_om,
        #                            grid_lifetime)

        return fig_grid
    else:
        return fig


@app.callback([Output('datatable_gis', 'data'),
                Output('output_gis', 'figure')],
              [Input('datatable_gis', "page_current"),
               Input('datatable_gis', "page_size"),
               Input('datatable_gis', "page_count")])
def update_table(page_current, page_size,page_count):
    if os.path.isfile(r'Output/Datasets/geo_df_json'):
        geo_df2 = pd.DataFrame(
            gpd.read_file(r"Output/Datasets/geo_df_json").drop(
                columns='geometry'))
        geo_df=gpd.read_file(r"Output/Datasets/geo_df_json")
        geo_df = geo_df.to_crs(epsg=4326)
        fig2 = go.Figure(go.Scattermapbox(

            name='GeoDataFrame',
            lat=geo_df.geometry.y,
            lon=geo_df.geometry.x,
            mode='markers',
            marker=go.scattermapbox.Marker(
                size=10,
                showscale=True,
                color=geo_df.Population,
                opacity=0.8,
                colorbar=dict(title='People')
            ),
            text=list(
                zip(geo_df.ID, geo_df.Weight, geo_df.Population.round(1))),
            hoverinfo='text',
            below="''"
        ))
        fig2.update_layout(mapbox_style="carto-positron")
        fig2.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        fig2.update_layout(mapbox_zoom=8.5,
                           mapbox_center={"lat": geo_df.geometry.y[
                               (int(geo_df.shape[0] / 2))],
                                          "lon": geo_df.geometry.x[
                                              (int(geo_df.shape[0] / 2))]})
    else:
        geo_df2 = pd.DataFrame()
        fig2 = dash.no_update
    return geo_df2.iloc[
           page_current * page_size:(page_current + 1) * page_size
           ].to_dict('records'), fig2


@app.callback([Output('datatable_grid', 'data'),
               Output('datatable_grid', 'columns')],
              [Input('datatable_grid', "page_current"),
               Input('datatable_grid', "page_size"),
               Input('datatable_grid', 'sort_by'),
               Input('output_grid', "figure")],
              [State('branch', 'value')])
def update_table(page_current, page_size, sort_by, output_grid, branches):
    branch = config.iloc[11, 1]
    geo_df2 = pd.DataFrame()

    if branch == 'no':
        if os.path.isfile(r'Output/Grids/grid_resume.csv'):
            geo_df2 = pd.read_csv(r'Output/Grids/grid_resume.csv')
            geo_df2 = geo_df2.round(2)

            if len(sort_by):
                geo_df2 = geo_df2.sort_values(
                    sort_by[0]['column_id'],
                    ascending=sort_by[0]['direction'] == 'asc',
                    inplace=False)

    if branch == 'yes':
        if os.path.isfile(r'Output/Branches/grid_resume.csv'):
            geo_df2 = pd.read_csv(r'Output/Branches/grid_resume.csv')
            geo_df2 = geo_df2.round(2)

            if len(sort_by):
                geo_df2 = geo_df2.sort_values(
                    sort_by[0]['column_id'],
                    ascending=sort_by[0]['direction'] == 'asc',
                    inplace=False)
    geo_df2 = geo_df2.dropna(axis=1, how='all')
    columns = [{"name": i, "id": i} for i in geo_df2.columns]
    return geo_df2.iloc[
           page_current * page_size:(page_current + 1) * page_size
           ].to_dict('records'), columns


@app.callback(Output('datatable_mg', 'data'),
              [Input('datatable_mg', "page_current"),
               Input('datatable_mg', "page_size"),
               Input('datatable_mg', 'sort_by'),
               Input('output_mg', "figure")])
def update_table(page_current, page_size, sort_by, output_mg):
    if os.path.isfile(r'Output/Microgrids/microgrids.csv'):
        geo_df2 = pd.read_csv(r'Output/Microgrids/microgrids.csv')
        geo_df2 = geo_df2.round(2)

        if len(sort_by):
            geo_df2 = geo_df2.sort_values(
                sort_by[0]['column_id'],
                ascending=sort_by[0]['direction'] == 'asc',
                inplace=False)
    else:
        geo_df2 = pd.DataFrame()
    return geo_df2.iloc[
           page_current * page_size:(page_current + 1) * page_size
           ].to_dict('records')


@app.callback(Output('load_profile_graph', 'figure'),
              [Input('datatable_load_profile', 'data'),
               Input('output_mg', "figure")])
def update_table(datatable_load_profile, output_mg):
    lp = pd.DataFrame(datatable_load_profile)
    graph = go.Figure(data=go.Scatter(x=np.arange(23),
                                      y=lp['Power [p.u.]'].append(
                                          lp['Power (p.u.)']),
                                      mode='lines+markers'))
    graph.update_layout(title='Daily Load Profile',
                        xaxis_title='Hour',
                        yaxis_title='Power [p.u.]')
    return graph



@app.callback([Output('datatable_grid_final', 'data'),
               Output('datatable_grid_final', 'columns')],
              [Input('datatable_grid_final', "page_current"),
               Input('datatable_grid_final', "page_size"),
               Input('datatable_grid_final', 'sort_by'),
               Input('output_npc', "figure")],
              [State('branch', 'value')])
def update_table(page_current, page_size, sort_by, output_grid, branches):
    branch = config.iloc[11, 1]
    geo_df2 = pd.DataFrame()

    if branch == 'no':
        if os.path.isfile(r'Output/Grids/grid_resume_opt.csv'):
            geo_df2 = pd.read_csv(r'Output/Grids/grid_resume_opt.csv')
            geo_df2 = geo_df2.round(2)

            if len(sort_by):
                geo_df2 = geo_df2.sort_values(
                    sort_by[0]['column_id'],
                    ascending=sort_by[0]['direction'] == 'asc',
                    inplace=False)

    if branch == 'yes':
        if os.path.isfile(r'Output/Branches/grid_resume_opt.csv'):
            geo_df2 = pd.read_csv(r'Output/Branches/grid_resume_opt.csv')
            geo_df2 = geo_df2.round(2)

            if len(sort_by):
                geo_df2 = geo_df2.sort_values(
                    sort_by[0]['column_id'],
                    ascending=sort_by[0]['direction'] == 'asc',
                    inplace=False)
    geo_df2 = geo_df2.dropna(axis=1, how='all')
    columns = [{"name": i, "id": i} for i in geo_df2.columns]
    return geo_df2.iloc[
           page_current * page_size:(page_current + 1) * page_size
           ].to_dict('records'), columns


@app.callback(Output('datatable_load_profile', 'data'),
              [Input('upload_loadprofile', 'contents')],
              [State('upload_loadprofile', 'filename'),
               State('upload_loadprofile', 'last_modified')])
def update_output(contents, filename, last_modified):
    if contents is not None:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8'))).round(4)
        upload_profile = pd.DataFrame(columns=['Hour 0-12', 'Power [p.u.]',
                                               'Hour 12-24',
                                               'Power (p.u.)'])
        upload_profile['Hour 0-12'] = pd.Series(np.arange(12)).astype(int)
        upload_profile['Hour 12-24'] = pd.Series(np.arange(12, 24)).astype(
            int)
        upload_profile['Power [p.u.]'] = df.iloc[0:12, 0].values
        upload_profile['Power (p.u.)'] = df.iloc[12:24, 0].values

        return upload_profile.to_dict('records')
    raise PreventUpdate


if __name__ == "__main__":
    app.run_server(debug=False)
