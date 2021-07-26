import requests
import pandas as pd
import json

##
# PV
##

'''lat = -16.5941
long = 36.5955
project_life = 25'''


def import_pv_data(lat, lon, tilt_angle):

    token = '556d9ea27f35f2e26ac9ce1552a3f702e35a8596  '
    api_base = 'https://www.renewables.ninja/api/'

    s = requests.session()
    # Send token header with each request
    s.headers = {'Authorization': 'Token ' + token}

    url = api_base + 'data/pv'

    args = {
        'lat': lat,
        'lon': lon,
        'date_from': '2019-01-01',
        'date_to': '2019-12-31',
        'dataset': 'merra2',
        'local_time': True,
        'capacity': 1.0,
        'system_loss': 0,
        'tracking': 0,
        'tilt': tilt_angle,
        'azim': 180,
        'format': 'json',
    }

    r = s.get(url, params=args)
    parsed_response = json.loads(r.text)

    data = pd.read_json(json.dumps(parsed_response['data']),
                        orient='index')
    pv_prod = data
    print("Solar Data imported")

    return pv_prod


def import_wind_data(lat, lon, wt):

    token = 'c511d32b578b4ec19c3d43c1a3fffb4cad5dc4d2'
    api_base = 'https://www.renewables.ninja/api/'

    s = requests.session()
    # Send token header with each request
    s.headers = {'Authorization': 'Token ' + token}
    url = api_base + 'data/wind'
    args = {
        'lat': lat,
        'lon': lon,
        'date_from': '2019-01-01',
        'date_to': '2019-12-31',
        'capacity': 1.0,
        'height': 50,
        'turbine': str(wt),
        'format': 'json',
    }

    # Parse JSON to get a pandas.DataFrame
    r = s.get(url, params=args)
    parsed_response = json.loads(r.text)

    data = pd.read_json(json.dumps(parsed_response['data']),
                        orient='index')
    wt_prod = data
    print("Wind Data imported")

    return wt_prod
