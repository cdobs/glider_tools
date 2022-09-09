#!/anaconda2/envs/datateam_tools/bin/python
'''
Author: Collin Dobson
Contact: cdobson@whoi.edu
Date: 10/21/2018
Purpose: Queries the NOAA NOMADS server for the data of a specific model run,
    plots it and saves it as a PNG, and creates a GIF of the individual plots.
Python Version: 3.7.x
'''
from functions import *
from configs import *

#############################################################################################
#############################################################################################
# THIS IS THE ONLY SECTION THAT THE USER MUST EDIT TO EXECUTE THIS SCRIPT #                 #
# Input which model you would like to pull data from                                        #
modelName = nww3                                                                            #
#                                                                                           #
# Input which parameter you would like to pull                                              #
parameter = 'htsgwsfc'                                                                      #
#                                                                                           #
# Define the OOI array for which you would like to plot the data                            #
array = 'pioneer'                                                                          #
#                                                                                           #
# Where would you like the files saved?                                                     #
savePath = '/Users/collindobson/Documents/Github/modelAnalysis/output/'                     #
#############################################################################################
#############################################################################################

# Record the current time for script timekeeping purposes.
startTime = datetime.datetime.now()
print(startTime.strftime("%B %d, %Y %H:%M"))

# Determine the current time and which mdoel run we should grab based on that time.
dayOfRun = str(datetime.datetime.today()).split()[0].replace("-","")
modelRun = str(decide_hour(int(str(datetime.datetime.today()).split()[1][0:2])))

# Track down the model definitions based on the user input above and set some plotting parameters
index = modelName['parameters'].index(parameter)
units = modelName['parameterUnits'][index]
nomadsURL = create_url(modelName['shortName'], dayOfRun, modelRun)
plottingBounds = modelName['plottingBounds'][index]
mapCords = mappingBounds[array]

# Create a default title for all created images based on the above definitions
plotTitle = ''+modelName['parameterDescription'][index]+' ['+units+']'
plotSecondaryTitle = 'Model Run: '+dayOfRun+"T"+modelRun+"0000Z"
cBarLabel = 'Wave height (m)'

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
    #if statement for model type
    plot = plot_data(lon, lat, data[x,:,:], dtime[x], plotTitle, array, plottingBounds, mapCords, savePath, cBarLabel)

# Collect and sort the images for the GIF
imageList = alpha_natural_sort(collect_images(savePath))

# Create and save the gif
make_gif(imageList, parameter, savePath)

# FIN
endTime = datetime.datetime.now()
print(endTime.strftime("%B %d, %Y %H:%M"))
#############################################################################################
#############################################################################################

# Plotting significant wave height and wave period
sigWaveHeight = calculate_averages(lat, lon, data, dtime, averageBounds[array]) * 3.28084
wavePeriod = calculate_averages(lat, lon, pull_data(nomadsURL, 'perpwsfc'), dtime, averageBounds[array])
plot_waveht_period_ratio(sigWaveHeight, wavePeriod, array, modelRun, dayOfRun)
