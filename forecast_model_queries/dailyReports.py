#!/Users/collindobson/anaconda2/envs/modelAnalysis/bin/python
from functions import *
from configs import *
startTime = datetime.datetime.now()
print(startTime.strftime("%B %d, %Y %H:%M"))

#######
modelName = nww3
parameter = 'windsfc'
parameter2 = 'windsfc'
index = modelName['parameters'].index(parameter)
units = modelName['parameterUnits'][index]
savePath = '/Users/collindobson/Documents/Github/glider_tools/forecast_model_queries/'
arrays = ['irminger', 'pioneer', 'papa']
#######

# Determine the current time and which mdoel run we should grab based on that time.
dayOfRun = str(datetime.datetime.today()).split()[0].replace("-","")
modelRun = str(decide_hour(int(str(datetime.datetime.today()).split()[1][0:2])))
nomadsURL = create_url(modelName['shortName'], dayOfRun, modelRun)

# Pull lat/lon and time data from the model
lat = pull_data(nomadsURL, 'lat')[:]
lon = pull_data(nomadsURL, 'lon')[:]
timestamps = pull_data(nomadsURL, 'time')
dtime = netCDF4.num2date(timestamps[:],timestamps.units)

# Pull the actual wave data from the model
waveHeightData = pull_data(nomadsURL, parameter)
wavePeriodData = pull_data(nomadsURL, parameter2)

for array in arrays:
    # Plotting significant wave height and wave period
    sigWaveHeight = calculate_averages(lat, lon, waveHeightData, dtime, averageBounds[array]) * 3.28084
    wavePeriod = calculate_averages(lat, lon, wavePeriodData, dtime, averageBounds[array])
    plot_waveht_period_ratio(sigWaveHeight, wavePeriod, array, modelRun, dayOfRun)
    plt.savefig(savePath+'/'+array+'waveconditions.png')
    plt.close()

# Iterate through the forecast time bins in each model and plot the data for that bin
for array in arrays:
    plotTitle = modelName['name']+' predicted '+modelName['parameterDescription'][index]
    cBarLabel = ''+modelName['parameterDescription'][index]+' ['+units+']'
    plottingBounds = modelName['plottingBounds'][index]
    mapCords = mappingBounds[array]
    for x in range(1, len(dtime)):
        plot = plot_data(lon, lat, waveHeightData[x,:,:], dtime[x], plotTitle, array, plottingBounds, mapCords, savePath, cBarLabel)
    # Collect and sort the images for the GIF
    imagePath = '/Users/collindobson/Documents/Github/modelAnalysis/output/dailyReports/'+array+'*0.png'
    imageList = alpha_natural_sort(collect_images(imagePath))
    # Create and save the gif
    make_gif(imageList, parameter, savePath, array)

# Gather the attachments and recipients and send the email
attachmentList = collect_images(savePath+'*waveconditions.png')
attachmentList = np.append(attachmentList, collect_images(savePath+'*.gif'))
recipients = ['collindobson@yahoo.com', 'cdobson@whoi.edu']
send_email("daily_report", attachmentList, recipients)
