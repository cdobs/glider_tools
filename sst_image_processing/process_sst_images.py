#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author Collin Dobson
@brief Scrapes SST images from Rutgers University and overlays OOI CGSN
    glider positions on them.
"""
import config
from deployed_gliders import deployed_gliders

import os
import re
import glob
import datetime
import requests
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Configuration
# Type of SST images to process (Options are composite or hourly)
sst_image_type = 'hourly'
# number of days to process
num_days = 1
images_per_day = 3

# Get remote directory
current_year = datetime.datetime.now().year
remote_url = f"https://marine.rutgers.edu/cool/regions/capehat/sst/noaa/{current_year}/img/"

def get_glider_names(deployed_gliders):
    """
    Gets glider name and other metadata for deployed gliders

    :param url: deployed glider configurations
    :return: glider_names, ref_designators, and glider_deployments

    """
    glider_names = []
    glider_deployments = []
    ref_designators = []

    for ref_des, deployments in deployed_gliders['Pioneer MAB'].items():
        for deployment_id, deployment_data in deployments.items():
            glider_names.append(deployment_data['glider_name'])
            glider_deployments.append(deployment_id)
            ref_designators.append(deployment_data['ref_des'])

    return(glider_names, ref_designators, glider_deployments)

def validate_url(url):
    """
    Validates a url

    :param url: The url to be validated
    :return: bool dependent on whether the url could be validated
    """
    parsed = urlparse(url)

    return bool(parsed.netloc) and bool(parsed.scheme)

def get_images(url, ext='.jpg'):
    """
    Scrapes a webpage/server index to get a list of images hosted there

    :param url: The url of the page to be scraped
    :param ext: The extension of images to scrape
    :return: a list of urls to images that were scraped
    """
    content = requests.get(url).text
    soup = BeautifulSoup(content, 'html.parser')
    image_urls = [url + '/' + node.get('href') for node in soup.find_all('a') if node.get('href').endswith(ext)]

    return image_urls

def cull_images(images, num_days):
    """
    Culls a list of images down based on date, determined by the
     number of days specified as a parameter

    :param images: A list of images to be culled
    :param num_days: The number of days of images to include in the culled list
    :return: a list of images that were culled
    """
    culled_images = []
    for i in range(0, num_days):
        today = datetime.date.today() - datetime.timedelta(days = i)
        year = str(today.year)[2:4]
        month = str(today.month).zfill(2)
        day = str(today.day).zfill(2)
        image_date_string = year+month+day
        temp_images = [x for x in images if image_date_string in x]
        culled_images = culled_images + temp_images

    return(culled_images)

def download_images(remote_url, images, local_url, sst_image_type):
    """
    Downloads a list of images from a remote url to a local destination

    :param remote_url: Remote url to download images from
    :param images: The list of images to be downloaded
    :param local_url: The local destination for the images to be downloaded
    :return: nothing
    """
    if len(images) != 0:
        for i, image in enumerate(images):
            if sst_image_type == 'composite':
                image_name = image.split("/")[-1]
                image_url = remote_url+image_name
                img_regx = re.compile(r'n')
                print(img_regx)
            elif sst_image_type == 'hourly':
                image_name = image.split("/")[-1]
                image_url = remote_url+image_name
                img_regx = re.compile(r'n00.jpg')

            if img_regx.search(image_name):
                print(f"Downloading image {image}")
                r = requests.get(image_url).content
                with open(f"{local_url}/{image_name}", "wb+") as f:
                    f.write(r)


def parse_image_name(image_name):
    """
    Parses an image name to extract the date components

    :param image_name: image name to be parsed
    :return: a list of the image name components
    """
    image_components = image_name.split(".")[0].split("/")[-1]
    image_year = image_components[0:2]
    image_month = image_components[2:4]
    image_day = image_components[4:6]

    image_name_components = [image_year, image_month, image_day]
    return(image_name_components)

def get_sst_image_config(sst_image_type):
    """
    Returns image cropping corners and lat/lon bounds based on SST image type.

    :param sst_image_type: (str): Either 'composite' or 'hourly'.
    :return: dict: Dictionary containing pixel corners and lat/lon bounds.
    """
    if sst_image_type == 'composite':
        return {
            'TOP_LEFT': (46, 38),
            'TOP_RIGHT': (755, 38),
            'BOTTOM_LEFT': (46, 770),
            'BOTTOM_RIGHT': (755, 770),
            'max_lat': 46,
            'min_lat': 35,
            'max_lon': 77,
            'min_lon': 63,
        }
    elif sst_image_type == 'hourly':
        return {
            'TOP_LEFT': (175, 150),
            'TOP_RIGHT': (2225, 150),
            'BOTTOM_LEFT': (175, 1725),
            'BOTTOM_RIGHT': (2225, 1725),
            'max_lat': 37,
            'min_lat': 33,
            'max_lon': 79.25,
            'min_lon': 73,
        }
    else:
        raise ValueError(f"Unknown SST image type: {sst_image_type}")

def convert_x(left_max_pixel, max_lon_deg, x_pixel_factor, x):
    """
    Converts a longitude value to an x pixel location

    :param left_max_pixel: x pixel cordinate of x,y pair that represents
        the top left of the grid
    :param max_lon_deg: maximum longitude degree displayed on pixel map
    :param x_pixel_factor: number of pixels per each lon degree on the map
    :param x: the longitude value to be converted to a pixel value
    :return: a pixel value for the x value in an x,y pair
    """
    pixel_x = left_max_pixel - ((max_lon_deg+x)*x_pixel_factor*-1)
    return(pixel_x)

def convert_y(top_max_pixel, max_lat_deg, y_pixel_factor, y):
    """
    Converts a latitude value to a y pixel location

    :param top_max_pixel: y pixel cordinate of x,y pair that represents
        the top left of the grid
    :param max_lat_deg: maximum latitude degree displayed on pixel map
    :param y_pixel_factor: number of pixels per each lat degree on the map
    :param x: the latitude value to be converted to a pixel value
    :return: a pixel value for the y value in an x,y pair
    """
    pixel_y = top_max_pixel + ((max_lat_deg-y)*y_pixel_factor)
    return(pixel_y)


def parse_log(log_file):
    """
    Parses a glider dockserver log to extract a GPS position

    :param log_file: glider to pull the dockserver logs for
    :param local_dir: local directory to store the DS logs
    :return: the gps fix (string)
    """
    with open(log_file, 'r') as fh:
        content = fh.read()
    gps_fix = re.findall(r'GPS Location:.+? (.+?) m', content)[-1]
    return gps_fix

def get_posit(glider, ref_des, deployment, logs_dir, posit_date="most_recent"):
    """
    Aggregates all log files or a specified glider and uses the parse_log
     function to extract a GPS position for a specified date.

    :param glider: glider to get a GPS position for
    :param local_dir: local directory where the DS logs are stored
    :param posit_date: date for which to extract a gps position
    :return: the gps fix (string)
    """
    log_files = [os.path.basename(x) for x in glob.glob(logs_dir+"/"+ref_des+'/'+deployment+'/logs/*.log')]
    log_files.sort(key=lambda log: re.findall(r"[0-9]{8}T[0-9]{6}", log))

    if posit_date == "most_recent":
        most_recent_log = log_files[-1]
        #gps_fix = parse_log(local_dir+"/ds_logs/"+glider+"/"+most_recent_log)
        gps_fix = parse_log(logs_dir+"/"+ref_des+"/"+deployment+"/logs/"+most_recent_log)
    else:
        culled_logs = [log for log in log_files if posit_date in log]
        most_recent_log = culled_logs[0]
        gps_fix = parse_log(logs_dir+"/"+ref_des+"/"+deployment+"/logs/"+most_recent_log)

        # Skip a bad position and find the next good one
        i = 0
        while "696969" in gps_fix and i != len(culled_logs):
            print(gps_fix)
            most_recent_log = culled_logs[i]
            gps_fix = parse_log(local_dir+"/ds_logs/"+glider+"/"+most_recent_log)
            i += 1

    return(gps_fix)

def main(argv=None):
    """
    -Validates the URL where the SST images are located and
     downloads those images to a local directory
    -Rsyncs the glider's dockserver log files to a local directory
      so that the GPS positions can be parsed
    -Constructs the geographic grid to be overlaid on the SST images
    -Aggregates the SST images to be processed from a local directory
    -Processes each SST image by calculating the geographic grid, converts
     and plots each glider's GPS position on the SST image

    :return: none
    """

    # gliders to process
    gliders, ref_designators, deployments = get_glider_names(deployed_gliders)

    # Clean previously processed images out of the local directory
    local_files = glob.glob(config.LOCAL_DIR+'images/*.*')
    for file in local_files:
        os.remove(file)

    # Validate the remote URL and download the images
    validate_url(remote_url)
    images = get_images(remote_url, 'jpg')
    images = cull_images(images, num_days)
    download_images(remote_url, images, config.IMAGE_DIR, sst_image_type)

    # calculate map coordinates and scale
    sst_image_config = get_sst_image_config('hourly')
    map_width = sst_image_config['TOP_RIGHT'][0] - sst_image_config['TOP_LEFT'][0]
    map_height = sst_image_config['BOTTOM_LEFT'][1]-sst_image_config['TOP_LEFT'][1]

    pixels_per_lon_degrees = map_width / (sst_image_config['max_lon'] - sst_image_config['min_lon'])
    pixels_per_lat_degrees = map_height / (sst_image_config['max_lat'] - sst_image_config['min_lat'])

    # Get the most recent 3 images to process
    num_images = num_days * images_per_day
    local_images = sorted(glob.glob(config.IMAGE_DIR + "/*.jpg"))[-num_images:]

    # process the images
    for img in local_images:
        print(f"Processing image {img} for gliders {', '.join(gliders)}")
        # get the date for each image
        image_date = parse_image_name(img)
        image_date_string = image_date[0]+image_date[1]+image_date[2]

        # read in the image data in Python figure
        fig = plt.figure()
        data = mpimg.imread(img)
        plt.imshow(data)

        # Skip over the images that are not on the correct grid
        if data.shape[0] < 800:
            continue

        # Get each glider position for this image and plot it
        for i, glider in enumerate(gliders):
            deployment = deployments[i]
            ref_des = ref_designators[i]
            try:
                glider_posit = get_posit(glider, ref_des, deployment, config.LOGS_DIR, posit_date=image_date_string)
            except:
                print("Glider " + glider + " does not have a position on " + image_date_string)
                continue

            posit_y = glider_posit.split(" -")[0]
            posit_x = glider_posit.split(" -")[1]
            y_decimal = int(posit_y[0:2])+float(posit_y[2:8])/60
            x_decimal = (int(posit_x[0:2])+float(posit_x[2:8])/60)*-1

            # convert lat/lon to pixel locations
            py = convert_y(sst_image_config['TOP_LEFT'][1], sst_image_config['max_lat'], pixels_per_lat_degrees, y_decimal)
            px = convert_x(sst_image_config['TOP_LEFT'][0], sst_image_config['max_lon'], pixels_per_lon_degrees, x_decimal)

            # Plot the positions
            plt.plot(px, py, marker='x', color="black")
            plt.annotate(glider,  xy=(px, py), fontsize=2.5)

        # Save the figure
        plt.axis('off')

        for i, glider in enumerate(gliders):
            sst_img_dir = os.path.join(config.SAVE_DIR, ref_designators[i], deployments[i], "sst")
            science_dir = os.path.join(config.SAVE_DIR, ref_designators[i], deployments[i], "science")
            image_name = f"{ref_designators[i]}-{deployments[i]}_{sst_name}"
            plt.savefig(os.path.join(sst_img_dir, f"{image_name}.png"), bbox_inches='tight')
            plt.savefig(os.path.join(sst_img_dir, f"{image_name}_Large.png"), dpi=300, bbox_inches='tight')

            if is_last:
                image_name = f"{ref_designators[i]}-{deployments[i]}-SST"
                plt.savefig(os.path.join(science_dir, f"{image_name}.png"), bbox_inches='tight')
                plt.savefig(os.path.join(science_dir, f"{image_name}_Large.png"), dpi=300, bbox_inches='tight')

        plt.close()

    for i, glider in enumerate(gliders):
        science_dir = os.path.join(config.SAVE_DIR, ref_designators[i], deployments[i], "science")
        sst_img_dir = os.path.join(config.SAVE_DIR, ref_designators[i], deployments[i], "sst")
        gif_output_path = os.path.join(science_dir, 'sst_animation.gif')
        create_gif_from_images(sst_img_dir, gif_output_path, duration=300)



if __name__ == '__main__':
    main()
