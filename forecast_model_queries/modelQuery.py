#!/anaconda2/envs/datateam_tools/bin/python
'''
Author: Collin Dobson
Contact: cdobson@whoi.edu
Date: 10/21/2018
Purpose: Queries the NOAA NOMADS server for the data of a specific model run,
    plots it and saves it as a PNG, and creates a GIF of the individual plots.
Python Version: 2.7x

This code is OBE and needs to be updated to conform to NOMAS API.


Needed to install basemap:
brew install geos
export GEOS_DIR="/usr/local"
python -m pip install basemap


'''
import os
import re
import netCDF4
import imageio
import datetime
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
'''
Function definitions below. Normally these would be defined in a separate module
    and imported above, but they were pulled into this file to show full demostration
    of how this project works.
'''


'''
alpha_natural_sort is a simple algorithm that performs a natural alphabetic sort
    on a given list. Useful for log files that append the datestamp to the name.
    Adapted from a stackoverflow post.

Post-Conditions: A naturally sorted list is returned.
'''
def alpha_natural_sort(l):
    converted = lambda text: int(text) if text.isdigit() else text.lower()
    aKey = lambda key: [ converted(c) for c in re.split('([0-9]+)', key) ]
    return sorted(l, key = aKey)


'''
pull_data queries the NOAA Nomads server for the given model and date.

Pre-conditions: nomadsURL is a formatted query URL that is formatted to match
    a specific model run on a specific day and hour. The desired parameter to pull
    from the server must be provided in the specific language described in the
    model dictionary below.

Post-Conditions: The data from the requested model is returned in NETCDF format.
'''
def pull_data(nomadsURL, parameter):
    file = netCDF4.Dataset(nomadsURL)
    data = file.variables[parameter]
    return data
    file.close()


'''
plot_data plots the data for a given model run using basemap.

Pre-conditions: x,y are lons and lats, timeStamp is in datetime format,
    color scale bounds are provided via plottingBounds and desired map coordinates
    via mapCords.

Post-Conditions: The data is plotted and stored as a .PNG file.
'''
def plot_data(x, y, variable, timestamp, plotTitle, array, plottingBounds, mapCords, savePath):
    # Create a basemap projection with specified coordinates
    plt.figure()
    m=Basemap(projection='merc', \
    llcrnrlon=mapCords[0],urcrnrlon=mapCords[1], \
    llcrnrlat=mapCords[2],urcrnrlat=mapCords[3], \
    resolution='h')

    # Place the lat and lon on a grid and create a colormesh
    x, y = m(*np.meshgrid(lon,lat))
    m.pcolormesh(x,y,variable,shading='flat',cmap=plt.cm.jet, \
        vmin=plottingBounds[0], vmax=plottingBounds[1])

    m.colorbar(location='right')

    # Draw coastlines and grid lines
    m.drawcoastlines()
    m.fillcontinents()
    m.drawmapboundary()
    m.drawparallels(np.arange(-90.,120.,2.5),labels=[1,0,0,0])
    m.drawmeridians(np.arange(-180.,180.,5),labels=[0,0,0,1])

    # Create a plot title and filename using the timestamp
    timeForTitle = timestamp.strftime("%B %d, %Y %H:%M")
    timeForFN = timestamp.strftime("%Y%m%d%H%M")
    plt.title(plotTitle+':'+timeForTitle+'UTC', fontsize=8)

    # Save the figure and clear out the buffer for the next ieration
    plt.savefig(savePath+'/'+array+'seaheight'+timeForFN+'.png')
    plt.cla()
    plt.clf()


'''
collect_images gathers a list of the filenames for the images that will be included
    in a gif.

Pre-conditions: imageDir is the directory of where the images are stored. An
    exception will be raised if there are other files im this directory that do
    not match the intended format.

Post-Conditions: a list of the full path and filenames will be returned
'''
def collect_images(imageDir):
    images = []
    for filename in os.listdir(imageDir):
        images.append(imageDir+filename)
    return images


'''
make_gif combines the PNGs in the provided image list into a gif

Pre-conditions: imageList is a list of the absolute path of the images to be placed
    in a GIF. gifPath is where you want the GIF saved.

Post-Conditions: a GIF will be saved to the hardcoded directory
'''
def make_gif(imageList, parameter, gifPath):
    images = []
    for filename in imageList:
        images.append(imageio.imread(filename))
    imageio.mimsave(gifPath+parameter+'.gif', \
        images, duration = 1)


'''
decide_hour is a simple algorithm to decide which model run is the latest based on
    the current time so we know which one to look for.

Pre-conditions: hour is the current hour in UTC

Post-Conditions: the hour of the model run we should grab is returned.
'''
def decide_hour(hour):
    if hour >= 0 and hour < 6:
        useHour = '00'
    elif hour >= 6 and hour < 12:
        useHour = '06'
    elif hour >= 12 and hour < 18:
        useHour = '12'
    elif hour >= 18 and hour < 24:
        useHour = '18'
    return useHour


'''
convert_dtime64 converts datetime64 timestamp(s) to regular datetime

Pre-conditions: timestamp is a datetime64 timestamp

Post-Conditions: the timestamps are returned in datetime format
'''
def convert_dtime64(timestamps):
    newTimes = np.array([])
    for t in range(0, len(timestamps)):
        t64 = timestamps[t]
        ts = (t64 - np.datetime64('1970-01-01T00:00:00Z')) / np.timedelta64(1, 's')
        newTimes = np.append(newTimes, datetime.datetime.utcfromtimestamp(ts))
    return(newTimes)



# Record the current time for script timekeeping purposes.
startTime = datetime.datetime.now()
print(startTime.strftime("%B %d, %Y %H:%M"))

# Determine the current time and which mdoel run we should grab based on that time.
dayOfRun = str(datetime.datetime.today()).split()[0].replace("-","")
modelRun = str(decide_hour(int(str(datetime.datetime.today()).split()[1][0:2])))

# Defining the NOAA Wavewatch 3 model:
nww3 = {
    "name": "NOAA WAVEWATCH III",
    "runTimes": ['00', '06', '12', '18'],
    "nomadsURL": 'https://nomads.ncep.noaa.gov:9090/dods/wave/nww3/nww3'+ \
        dayOfRun+'/nww3'+dayOfRun+'_'+modelRun+'z',

    "parameters": ['dirpwsfc', 'dirswsfc', 'htsgwsfc','perpwsfc', 'perswsfc', \
    'ugrdsfc', 'vgrdsfc', 'wdirsfc', 'windsfc', 'wvdirsfc', 'wvpersfc'],

    "parameterDescription": ['primary wave direction', 'secondary wave direction', \
        'significant height of combined wind waves and swell', 'primary wave mean period', \
        'secondary wave mean period','u-component of wind', 'v-component of wind', \
        'wind direction (from which blowing)', 'wind speed', 'direction of wind waves',
        'mean period of wind waves'],

    "parameterUnits": ['deg', 'deg', 'm','s', 's', 'm/s', 'm/s', 'deg', 'm/s', 'deg', 's'],

    "plottingBounds": [[0,0], [0,0], [0,14], [0,10], [0,0], [0,0], [0,0], [0,0], [0,0], [0,0], [0,0]]
}

# Defining the RTOFS global model
rtofsGlobal = {
    "name": "RTOFS Global",
    "nomadsURL": 'https://nomads.ncep.noaa.gov:9090/dods/rtofs/rtofs_global'+dayOfRun+'/rtofs_glo_2ds_forecast_3hrly_diag',

    "parameters": ['ssh', 'ice_coverage', 'sea_ice_thickness'],

    "parameterDescription": ['sea surface elevation', 'ice coverage', 'sea ice thickness'],

    "parameterUnits": ['m', 'fraction covered', 'm'],

    "plottingBounds": [[-2,2], [0,1], [0,5]]
}

# Defining the Global Forecast System model
gfs = {
    "name": "Global Forecast System",
    "nomadsURL": 'https://nomads.ncep.noaa.gov:9090/dods/gfs_0p25/gfs'+dayOfRun+'/gfs_0p25_00z',
    "parameters": ['apcpsfc', 'tmpsfc'],
    "parameterDescription": ['surface total precipitation', 'surface temperature'],
    "parameterUnits": ['kg/m^2', 'k'],
    "plottingBounds": [[0, 10], [0, 100]]
}

# Define mapping bounds for the various OOI arrays
mappingBounds = {
    "irminger": [301., 347., 53., 73.],
    "pioneer": [280., 300., 35., 45.],
    "papa": [0,0,0,0],
    "southern": [0,0,0,0]
}

######################################################################################################################
######################################################################################################################
# THIS IS THE ONLY SECTION THAT THE USER MUST EDIT TO EXECUTE THIS SCRIPT #                                         #
# Input which model you would like to pull data from                                                                #
modelName = nww3                                                                                                    #
#                                                                                                                   #
# Input which parameter you would like to pull                                                                      #
parameter = 'htsgwsfc'                                                                                              #
#                                                                                                                   #
# Define the OOI array for which you would like to plot the data                                                    #
array = 'irminger'                                                                                                  #
#                                                                                                                   #
# Where would you like the files saved?                                                                             #
savePath = '/Users/cdobson/Documents/Github/glider_tools/forecast_mode_queries/output/'+array+'/'                   #
#####################################################################################################################
#####################################################################################################################


# Track down the model definitions based on the user input above and set some plotting parameters
index = modelName['parameters'].index(parameter)
units = modelName['parameterUnits'][index]
nomadsURL = modelName['nomadsURL']
plottingBounds = modelName['plottingBounds'][index]
mapCords = mappingBounds[array]

# Create a default title for all created images based on the above definitions
plotTitle = ''+modelName['parameterDescription'][index]+' ['+units+']'

#############################################################################################
# Pull the location and time data from the model
lat = pull_data(nomadsURL, 'lat')[:]
lon = pull_data(nomadsURL, 'lon')[:]
timestamps = pull_data(nomadsURL, 'time')
dtime = netCDF4.num2date(timestamps[:],timestamps.units)

# Pull the actual data from the model
data = pull_data(nomadsURL, parameter)

# Iterate through the forecast time bins in each model and plot the data for that bin
for x in range(1, len(dtime)):
    plot = plot_data(lon, lat, data[x,:,:], dtime[x], plotTitle, array, plottingBounds, mapCords, savePath)

# Collect and sort the images for the GIF
imageList = alpha_natural_sort(collect_images(savePath))

# Create and save the gif
make_gif(imageList, parameter, savePath)

# FIN
endTime = datetime.datetime.now()
print(endTime.strftime("%B %d, %Y %H:%M"))
#############################################################################################
#############################################################################################
