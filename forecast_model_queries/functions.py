from functions import *
from configs import *
from mpl_toolkits.basemap import Basemap
import numpy as np
import matplotlib.pyplot as plt
import netCDF4
import os, glob
import re
import imageio
import datetime
import xarray as xr
import email, smtplib, ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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
create_url

Pre-conditions:

Post-Conditions:
'''
def create_url(model, dayOfRun, modelRun):
    baseUrl = "https://nomads.ncep.noaa.gov:9090/dods/"
    if (model == "nww3"):
        url = baseUrl+"wave/nww3/nww3"+dayOfRun+"/nww3"+dayOfRun+"_"+modelRun+"z"
    elif (model == "rtofs"):
        url = baseUrl+"rtofs/rtofs_global"+dayOfRun+"/rtofs_glo_2ds_forecast_3hrly_diag"
    return url


'''
plot_data plots the data for a given model run using basemap.

Pre-conditions: x,y are lons and lats, timeStamp is in datetime format,
    color scale bounds are provided via plottingBounds and desired map coordinates
    via mapCords.

Post-Conditions: The data is plotted and stored as a .PNG file.
'''
def plot_data(lon, lat, variable, timestamp, plotTitle, array, plottingBounds, mapCords, savePath, cBarLabel):
    # Create a basemap projection with specified coordinates
    plt.figure()
    m=Basemap(projection='merc', \
    llcrnrlon=mapCords[0],urcrnrlon=mapCords[1], \
    llcrnrlat=mapCords[2],urcrnrlat=mapCords[3], \
    resolution='l')

    # Place the lat and lon on a grid and create a colormesh
    x, y = m(*np.meshgrid(lon,lat))
    m.pcolormesh(x,y,variable,shading='flat',cmap=plt.cm.jet, \
        vmin=plottingBounds[0], vmax=plottingBounds[1])

    m.colorbar(location='right', label=cBarLabel)

    # Draw coastlines and grid lines
    m.drawcoastlines()
    m.fillcontinents()
    m.drawmapboundary()
    m.drawparallels(np.arange(-90.,120.,2.5),labels=[1,0,0,0])
    m.drawmeridians(np.arange(-180.,180.,5),labels=[0,0,0,1])

    # Create a plot title and filename using the timestamp
    timeForTitle = timestamp.strftime("%B %d, %Y %H:%M")
    timeForFN = timestamp.strftime("%Y%m%d%H%M")
    plt.title(plotTitle+'\n'+timeForTitle+'UTC', fontsize=8)

    # Save the figure and clear out the buffer for the next ieration
    plt.savefig(savePath+'/'+array+'seaheight'+timeForFN+'.png')
    plt.cla()
    plt.close()



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
    for filename in glob.glob(imageDir):
        images.append(filename)
    return images


'''
make_gif combines the PNGs in the provided image list into a gif

Pre-conditions: imageList is a list of the absolute path of the images to be placed
    in a GIF. gifPath is where you want the GIF saved.

Post-Conditions: a GIF will be saved to the hardcoded directory
'''
def make_gif(imageList, parameter, gifPath, array):
    images = []
    for filename in imageList:
        images.append(imageio.imread(filename))
        imageio.mimsave(gifPath+array+parameter+'.gif', images, duration = 1)


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


'''
calculate_averages averages the predicted values of a forecast values across a pre-determined grid
    for multiple model runs

Pre-conditions: bounds are lat/lon minimums and maximums to average across

Post-Conditions: the averages are returned in an array with one number per model run
'''
def calculate_averages(lat, lon, variable, dtime, bounds):
    # Restrict the lat and lon bounds to include only the area we want to average values for
    lats = np.argwhere((lat > bounds[2]) & (lat < bounds[3])).flatten()
    lons = np.argwhere((lon > bounds[0]) & (lon < bounds[1])).flatten()

    # Create arrays to house time and average results
    time = np.array([])
    avgVariable = np.array([])

    # Iterate through each timed model run
    for x in range(0, len(dtime)):
        # Create a temporary array to store the parameter values for each model run
        tempValues = np.array([])
        # Unmask the data array of parameter values
        data = variable[x,:,:].filled()
        # Grab the parameter values for each model run and XY pair, find the mean then store it
        for i in range(0, len(lats)):
            for j in range(0, len(lons)):
                tempValues = np.append(tempValues, data[lats[i]][lons[j]])
        avgVariable = np.append(avgVariable, tempValues.mean())
        time = np.append(time, dtime[x])
    return(avgVariable)


'''
plot_waveht_period_ratio is a specialized plotting function to create wave height and wave period plots

Pre-conditions: none

Post-Conditions: none
'''
def plot_waveht_period_ratio(sigWaveHeight, wavePeriod, array, modelRun, dayOfRun):
    horiz_line_data = np.array([2 for i in range(len(sigWaveHeight)*3)])
    sigWaveHeightToPeriod = sigWaveHeight / wavePeriod
    xaxisValues = [x*3 for x in range(0, 61)]

    plt.plot(horiz_line_data,'r--')
    plt.plot(xaxisValues, sigWaveHeight, label='Significant Wave Height (ft)')
    plt.plot(xaxisValues, wavePeriod, label='Wave Period (s)')
    plt.plot(xaxisValues, sigWaveHeightToPeriod, label='Wave Height:Period ft/s')

    plt.title(array.capitalize()+" Predicted Wave Conditions     \n Model run: "+dayOfRun+"T"+modelRun+"0000Z")
    plt.xlabel("Time (hours)")
    plt.xlim([0, 180])
    plt.ylabel("Wave Height (ft) and Period(s)")
    plt.xticks([0, 24, 48, 72, 96, 120, 144, 168])
    plt.legend()


'''
send_email creates a local email server to send emails with attachments

Pre-conditions: attachmentList can be one or multiple files, receipients can be one or multiple

Post-Conditions: none
'''
def send_email(type, attachmentList, recipients):
    if type == "glider":
        message = glider_message
    elif type == "daily_report":
        message = daily_report
    elif type == "icing":
        message = icing

    # Email server settings
    port = 465
    smtp_server = "smtp.gmail.com"
    sender_email = "ooicgsnalerts@gmail.com"
    subject = message['subject']
    body = message['body']

    # Construct the email use MIME protocol
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message["CC"] = ", ".join(recipients)

    # Attach the body to the email
    message.attach(MIMEText(body, "plain"))

    # Open your attachment in binary mode
    for filename in attachmentList:
        with open(filename, "rb") as attachment:
            # Add file as application/octet-stream
            # Email client can usually download this automatically as attachment
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())

        # Encode file in ASCII characters to send by email
        encoders.encode_base64(part)

        # Add header as key/value pair to attachment part
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {filename}",
        )
        message.attach(part)

    # Add the attachment and text to the email
    text = message.as_string()

    # Send the email using the SMTP server
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        server.login(sender_email, "cgsnooiuser")
        server.sendmail(sender_email, receiver_email, text)
