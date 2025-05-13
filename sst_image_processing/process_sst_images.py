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
from datetime import datetime, timedelta
import requests
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import imageio

# Configuration
# Type of SST images to process (Options are composite or hourly)
sst_image_type = 'hourly'
# number of days to process
num_days = 1

# Get remote directory
current_year = datetime.now().year
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

def cull_images(images, num_hours=24):
    """
    Culls a list of images down to the most recent `num_hours` images.

    :param images: A list of image filenames or URLs
    :param num_hours: The number of recent images to keep (default: 24)
    :return: A list of the most recent `num_hours` images
    """
    # Sort images by the datetime encoded in their filename
    def extract_timestamp(img):
        match = re.search(r'(\d{6})\.(\d{1,3})\.(\d{4})', img)
        if match:
            date_part, hourish, minsec = match.groups()
            try:
                hour = hourish.zfill(2)[:2]
                minute = minsec[:2]
                second = minsec[2:].zfill(2)
                timestamp_str = f"{date_part}{hour}{minute}{second}"
                return datetime.strptime(timestamp_str, "%y%m%d%H%M%S")
            except:
                return datetime.min
        return datetime.min

    images_sorted = sorted(images, key=extract_timestamp)
    return images_sorted[-num_hours:]

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
    image_filename = os.path.basename(urlparse(image_name).path)
    image_filename_components = image_filename.split(".")
    image_year = image_filename_components[0][0:2]
    image_month = image_filename_components[0][2:4]
    image_day = image_filename_components[0][4:6]

    image_hour = image_filename_components[2][0:2]

    image_name_components = [image_year, image_month, image_day, image_hour]

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
    Aggregates all log files for a specified glider and uses the parse_log
    function to extract a GPS position for a specified date.

    :param glider: glider to get a GPS position for
    :param ref_des: reference designator (e.g., CP05MOAS-GL564)
    :param deployment: deployment name (e.g., D00001)
    :param logs_dir: local directory where the logs are stored
    :param posit_date: date for which to extract a GPS position, in format '250513T12' (YYMMDDTHH)
    :return: the gps fix (string)
    """
    log_path = os.path.join(logs_dir, ref_des, deployment, 'logs', '*.log')
    log_files = [os.path.basename(x) for x in glob.glob(log_path)]

    # Extract timestamps from log filenames
    log_timestamps = []
    for log in log_files:
        match = re.search(r"(\d{8}T\d{6})", log)
        if match:
            ts_str = match.group(1)
            ts_dt = datetime.strptime(ts_str, "%Y%m%dT%H%M%S")
            log_timestamps.append((log, ts_dt))

    if not log_timestamps:
        raise ValueError("No valid log timestamps found in filenames.")

    if posit_date == "most_recent":
        # Sort by datetime and get the most recent
        most_recent_log = max(log_timestamps, key=lambda x: x[1])[0]
        gps_fix = parse_log(os.path.join(logs_dir, ref_des, deployment, 'logs', most_recent_log))
    else:
        # Convert posit_date (e.g., '250513T12') into datetime object
        try:
            posit_dt = datetime.strptime(posit_date, "%y%m%dT%H")
        except ValueError:
            raise ValueError(f"Invalid posit_date format: {posit_date}. Expected format: 'YYMMDDTHH'")

        # Find the log file with the timestamp closest to posit_date
        closest_log = min(log_timestamps, key=lambda x: abs(x[1] - posit_dt))[0]
        gps_fix = parse_log(os.path.join(logs_dir, ref_des, deployment, 'logs', closest_log))

        # Skip a bad position and find the next good one
        i = 0
        sorted_by_proximity = sorted(log_timestamps, key=lambda x: abs(x[1] - posit_dt))
        while "696969" in gps_fix and i < len(sorted_by_proximity):
            log_candidate = sorted_by_proximity[i][0]
            gps_fix = parse_log(os.path.join(logs_dir, ref_des, deployment, 'logs', log_candidate))
            i += 1

    return gps_fix


def create_gif_from_images(image_dir, gif_path, duration=0.5):
    """
    Creates a GIF from all SST images in the directory using imageio.

    :param image_dir: Path to directory containing SST images.
    :param gif_path: Full output path for the gif.
    :param duration: Duration (in seconds) each frame is shown in the GIF.
    """
    image_files = sorted(
        [os.path.join(image_dir, f) for f in os.listdir(image_dir) if f.lower().endswith('.png') and "_Large" in f],
        key=os.path.getmtime
    )

    if not image_files:
        print("No images found to create a GIF.")
        return

    images = [imageio.imread(f) for f in image_files]
    imageio.mimsave(gif_path, images, duration=duration)
    print(f"GIF created at: {gif_path}")

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

    # Clean previously processed images out of glider directories
    for i, glider in enumerate(gliders):
        glider_dir = os.path.join(config.SAVE_DIR, ref_designators[i], deployments[i], "sst")
        glider_files = glob.glob(glider_dir+'/*')
        for file in glider_files:
            os.remove(file)

    # Clean previously processed images out of the local directory
    local_files = glob.glob(config.LOCAL_DIR+'images/*.*')
    for file in local_files:
        os.remove(file)

    # Validate the remote URL and download the images
    if validate_url(remote_url):
        images = get_images(remote_url, 'jpg')
        images = cull_images(images, num_hours=24)
        download_images(remote_url, images, config.IMAGE_DIR, sst_image_type)

    # calculate map coordinates and scale
    sst_image_config = get_sst_image_config('hourly')
    map_width = sst_image_config['TOP_RIGHT'][0] - sst_image_config['TOP_LEFT'][0]
    map_height = sst_image_config['BOTTOM_LEFT'][1]-sst_image_config['TOP_LEFT'][1]

    pixels_per_lon_degrees = map_width / (sst_image_config['max_lon'] - sst_image_config['min_lon'])
    pixels_per_lat_degrees = map_height / (sst_image_config['max_lat'] - sst_image_config['min_lat'])

    # Get the most recent 3 images to process
    num_images = num_days * 24
    local_images = sorted(glob.glob(config.IMAGE_DIR + "/*.jpg"))[-num_images:]

    # process the images
    for img in local_images:
        is_last = img == local_images[-1]
        print(f"Processing image {img} for gliders {', '.join(gliders)}")
        # get the date for each image
        image_date = parse_image_name(img)
        image_hour = image_date[3]
        image_date_string = image_date[0]+image_date[1]+image_date[2]+"T"+image_hour

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

        sst_name = os.path.splitext(os.path.basename(urlparse(img).path))[0]
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
