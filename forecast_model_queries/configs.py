# Defining the NOAA Wavewatch 3 model:
nww3 = {
    "name": "NOAA WAVEWATCH III",
    "shortName": "nww3",
    "runTimes": ["00", "06", "12", "18"],
    "parameters": ['dirpwsfc', 'dirswsfc', 'htsgwsfc','perpwsfc', 'perswsfc',
        'ugrdsfc', 'vgrdsfc', 'wdirsfc', 'windsfc', 'wvdirsfc', 'wvpersfc'],
        "parameterDescription": ['primary wave direction', 'secondary wave direction',
        'significant height of combined wind waves and swell', 'primary wave mean period',
        'secondary wave mean period','u-component of wind', 'v-component of wind',
        'wind direction (from which blowing)', 'wind speed', 'direction of wind waves',
        'mean period of wind waves'],
    "parameterUnits": ['deg', 'deg', 'm','s', 's', 'm/s', 'm/s', 'deg', 'm/s', 'deg', 's'],
    "plottingBounds": [[0,0], [0,0], [0,14], [0,10], [0,0], [0,0], [0,0], [0,0], [0,25], [0,0], [0,0]],
}

# Defining the RTOFS global model
rtofsGlobal = {
    "name": "RTOFS Global",
    "shortName": "rtofs",
    "parameters": ['ssh', 'ice_coverage', 'sea_ice_thickness'],
    "parameterDescription": ['sea surface elevation', 'ice coverage', 'sea ice thickness'],
    "parameterUnits": ['m', 'fraction covered', 'm'],
    "plottingBounds": [[-2,2], [0,1], [0,5]]
}

# Defining the Global Forecast System model
gfs = {
    "name": "Global Forecast System",
    "parameters": ['apcpsfc', 'tmpsfc'],
    "parameterDescription": ['surface total precipitation', 'surface temperature'],
    "parameterUnits": ['kg/m^2', 'k'],
    "plottingBounds": [[0, 10], [0, 100]]
}

# Define mapping bounds for the various OOI arrays
mappingBounds = {
    "irminger": [301., 347., 53., 73.],
    "pioneer": [280., 300., 35., 45.],
    "papa": [200., 230., 40., 60.],
    "southern": [0,0,0,0]
}

# Define the bounds for averaging values at each array
averageBounds = {
    "irminger": [318., 322., 58., 60.],
    "pioneer": [289., 291., 39., 41.],
    "papa": [215,217,49,51],
    "southern": [0,0,0,0]
}

# Glider alert email template
glider_message = """\
    Do something about it."""

# Daily report email template
daily_report = {
    "subject": "Daily weather forecast.",
    "body": "Here is the wave condition outlook at each array as predicted by the NOAA Wave Watch 3 model."
}
