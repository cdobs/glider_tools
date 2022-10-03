from cgitb import text
import os
import re
import sys
import glob
import argparse
import requests
import datetime
import numpy as np
from bs4 import *
import pandas as pd
from matplotlib import pyplot as plt
from urllib.parse import urljoin, urlparse
from datetime import timezone
import math
import geopy.distance

def validate_url(url):
    """
    Validates a url

    :param url: The url to be validated
    :return: bool dependent on whether the url could be validated
    """
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)

def get_file_urls(url, ext='.ma'):
    """
    Scrapes a web page to return a list of files hosted

    :param url: The url of the page to be scraped
    :param ext: The extension of files to scrape
    :return file_urls: a list of urls to the scraped images
    """
    content = requests.get(url).text
    soup = BeautifulSoup(content, 'html.parser')
    file_urls = [url + node.get('href') for node in soup.find_all('a') if node.get('href').endswith(ext)]

    return file_urls

def download_file(remote_url, file_url, local_dir, file_regx=""):
    """
    Downloads a file from a remote url to a local destination

    :param remote_url: Remote url to download files from
    :param file_url: The url of the file to be downloaded
    :param local_dir: Local destination to download file
    :optional param file_regx: Optional parameter to download a file
        only if specified string is contained within the name
    :return: nothing
    """
    if len(file_url) != 0:
        if file_regx in file_url:
            r = requests.get(file_url).content
            file_name = file_url.split("/")[-1]
            with open(f"{local_dir}/{file_name}", "wb+") as f:
                f.write(r)

def parse_file(file, string_to_match):
    """
    Parses a glider MA file or dockserver log file to return the value of
        a particular argument or sensor

    :param file: file to be parsed
    :param string: the string to search for in the file
    :return match_list: a list of matches (if any) for the string in the file
    """

    # Open the file and search for the regex
    fh = open(file).read()

    if string_to_match == "GPS Location:":
        try:
            match_list = re.findall('GPS Location:(.+?)\n', fh)
            gps_split = re.split(" +", match_list[-1])
            lat = gps_split[1].strip(" ")
            lon = gps_split[3].strip(" ")
            age = gps_split[6].strip(" ")
        except:
            lat = "No match."
            lon = "No match."
            age = "No match."
        return lat, lon, age

    else:
        match_string = re.compile(string_to_match+'(.+?)\n')
        match_list = re.findall(match_string, fh)

    file_type = file.split(".")[-1].lower()
    # If the provided file is an MA file then parse it
    if file_type == 'ma':
        try:
            match_text = match_list[0].split(")")[1]
            value_index = len(match_text) - len(match_text.lstrip())
            match_return = match_text.split(" ")[value_index]
        except:
            # Handles cases where regex was not matched in the MA file
            match_return = "No match."

    # If the provided file is a DS log file then parse it
    elif file_type == 'log':
        try:
            match_text = match_list[0].split("=")[1].split(" ")
            match_return = match_text[0]
        except:
            # Handles cases where regex was not matched in the DS log file
            match_return = "No match."
    else:
        match_return = "No match."

    if file_type == "log" and "horz" in string_to_match:
        try:
            match_return = match_list[0].split()[1]
        except:
            match_return = "No match."

    return(match_return)

def parse_date_from_file_name(file):
    """
    Parses an archived glider ma filename to extract the date it was archived or
    a dockserver log file to extract the date it was created

    :param file: filename to be parsed
    :return fname_as_datetime: a datetime object with the date and time that
        were extracted from the filename
    """

    # Determine if this is an MA file or a dockserver log file based on the extension
    file_name = file.split("/")[-1]
    file_type = file_name.split(".")[-1].lower()

    if file_type == "log":
        file_name = file_name.split("_")[-1]

    # Parse the MA file or DS logfile name to extract the date and time components
    year = int(file_name[0:4])
    month = int(file_name[4:6])
    day = int(file_name[6:8])
    hour = int(file_name[9:11])
    minute = int(file_name[11:13])
    second = int(file_name[13:15])

    # Return the datetime object
    fname_as_datetime = datetime.datetime(year, month, day, hour, minute, second)
    return(fname_as_datetime)


def parse_times_from_ds(ds_log_file):
    """
    Parses a

    :param ds_log_file: log file to be parsed
    :return match_list: a list of matches (if any) for the string in the file
    """

    # Open the file and search for the regex
    fh = open(ds_log_file).read()
    string_to_match = "Curr Time:"
    match_string = re.compile(string_to_match+'(.+?)\n')
    match_list = re.findall(match_string, fh)

    return(match_list)

def natural_sort(l):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ]
    return sorted(l, key = alphanum_key)

def calculate_time_delta_ds_logs(ds_log_1, ds_log_2):
    # Open the file and search for the regex
    fh = open(ds_log_1).read()
    ds_log_1_match_string = re.compile('Curr Time: (.+?)\n')
    ds_log_1_match_list = re.findall(ds_log_1_match_string, fh)

    # If the DS log contains no timestamp paragraph, parse it from file name
    if not ds_log_1_match_list:
        ds_log_1_datetime = parse_date_from_file_name(ds_log_1)
    else:
        earliest_time = ds_log_1_match_list[0]
        latest_time = ds_log_1_match_list[-1]

        if ds_log_1 == ds_log_2:
            latest_time = earliest_time

        split_time = latest_time.split(" ")
        split_time = [i for i in split_time if i]
        year = int(split_time[4])
        month = split_time[1]
        day = int(split_time[2])
        hour = int(split_time[3].split(":")[0])
        minute = int(split_time[3].split(":")[1])
        second = int(split_time[3].split(":")[2])

        month_object = datetime.datetime.strptime(month, "%b")
        month_object = datetime.datetime.strptime(month, "%b")
        month_number = month_object.month
        ds_log_1_datetime = datetime.datetime(year, month_number, day, hour, minute, second)

    # Open the file and search for the regex
    fh = open(ds_log_2).read()
    ds_log_2_match_string = re.compile('Curr Time: (.+?)\n')
    ds_log_2_match_list = re.findall(ds_log_1_match_string, fh)

    # If the DS log contains no timestamp paragraph, parse it from file name
    if not ds_log_2_match_list:
        ds_log_2_datetime = parse_date_from_file_name(ds_log_2)
    else:
        earliest_time = ds_log_2_match_list[0]
        latest_time = ds_log_2_match_list[-1]

        split_time = latest_time.split(" ")
        split_time = [i for i in split_time if i]
        year = int(split_time[4])
        month = split_time[1]
        day = int(split_time[2])
        hour = int(split_time[3].split(":")[0])
        minute = int(split_time[3].split(":")[1])
        second = int(split_time[3].split(":")[2])

        month_object = datetime.datetime.strptime(month, "%b")
        month_number = month_object.month
        ds_log_2_datetime = datetime.datetime(year, month_number, day, hour, minute, second)

    ds_log_delta = abs(ds_log_2_datetime - ds_log_1_datetime)

    return(ds_log_delta)

def calculate_distance_from_waypoint(gps_lat, gps_lon, wpt_lat, wpt_lon):
    gps_cords = (gps_lat, gps_lon)
    wpt_cords = (wpt_lat, wpt_lon)

    distance = geopy.distance.geodesic(gps_cords, wpt_cords).m

    return distance


def parse_gps_lat(gps_lat):
    if "69696969" in str(gps_lat):
        decimal_gps_lat = "No Fix."
    else:
        decimal_gps_lat = round(float(gps_lat[0:2])+float(gps_lat[2:])/60,3)
    return(decimal_gps_lat)

def parse_gps_lon(gps_lon):
    decimal_gps_lon = round(float(gps_lon[1:3])+float(gps_lon[3:])/60,3)
    return(decimal_gps_lon)

def parse_wpt_lat(wpt_lat):
    decimal_wpt_lat = round(float(wpt_lat[0:2])+float(wpt_lat[2:4])/60, 3)
    return(decimal_wpt_lat)

def parse_wpt_lon(wpt_lon):
    decimal_wpt_lon = round(float(wpt_lon[1:3])+float(wpt_lon[3:5])/60, 3)
    return(decimal_wpt_lon)


def calculate_fz(wpt_lat, wpt_lon):
    SE_bound = (39.833,70.375)
    NE_bound = (40.083,70.375)
    NW_bound = (40.083,71.167)
    SW_bound = (39.833,71.167)

    SE_NE_line = np.full(10, np.nan)
    SE_NE_line[0] = SE_bound[0]
    SE_NE_line[-1] = NE_bound[0]

    SE_NE_Y = pd.Series(SE_NE_line).interpolate()

    if math.isclose(wpt_lat, SE_bound[0],  abs_tol = .05) & math.isclose(wpt_lon, SE_bound[1],  abs_tol = .05):
        bound = "SE"
    elif math.isclose(wpt_lat, NE_bound[0],  abs_tol = .05) & math.isclose(wpt_lon, NE_bound[1],  abs_tol = .05):
        bound = "NE"
    elif math.isclose(wpt_lat, NW_bound[0],  abs_tol = .05) & math.isclose(wpt_lon, NW_bound[1],  abs_tol = .05):
        bound = "NW"
    elif math.isclose(wpt_lat, SW_bound[0],  abs_tol = .05) & math.isclose(wpt_lon, SW_bound[1],  abs_tol = .05):
        bound = "SW"
    else:
        bound = "n/a"

    for lat in SE_NE_Y[len(SE_NE_Y/2):-1]:
        if math.isclose(lat, wpt_lat, abs_tol = .05) & math.isclose(wpt_lon, 70.375):
            bound = "NE"
    return(bound)


def count_transects(save_dir, glider, deployment, line, wpt1, wpt2):
    line_csv = save_dir+"/output/"+line+"_Gliders/"+"CP05MOAS-GL"+glider+"_D"+str(deployment).zfill(5)+"_ds_logfile_extractions.csv"
    line_df = pd.read_csv(line_csv)
    line_df = line_df.sort_values("Datetime")

    wpt_1_string = wpt1
    wpt_2_string = wpt2

    transect_counter = 0
    used_indices = []
    at_end = 0
    transect_start_dates = []
    transect_end_dates = []
    transect_numbers = []
    return_list = []
    transect_deltas = []

    for index, row in line_df.iterrows():
        if line_df['Science_on'][index] != 0:
            if row[wpt_1_string] == 1:
                #print(index)
                if index in used_indices:
                    a = 1
                else:
                    transect_start_index = index
                    temp_index = index

                    while temp_index < len(line_df) and line_df[wpt_1_string][temp_index] != 0:
                        temp_index += 1
                    # When it is no longer at the waypoint
                    leaves_wpt_index = temp_index
                    transect_index = temp_index

                    # When it gets to the NE wpt
                    while transect_index < len(line_df) and line_df[wpt_2_string][transect_index] != 1:
                        transect_index += 1

                    transect_end_index = transect_index
                    if transect_index == len(line_df):
                        at_end = 1
                    else:
                        transect_counter += 1
                        transect_start_date = line_df['Datetime'][transect_start_index]
                        transect_end_date = line_df['Datetime'][transect_end_index]
                        transect_delta_time = (transect_end_date - transect_start_date)/60/60/24

                        transect_numbers.append(transect_counter)
                        transect_start_dates.append(transect_start_date)
                        transect_end_dates.append(transect_end_date)
                        transect_deltas.append(transect_delta_time)

                    used_range = list(range(transect_start_index, transect_end_index))
                    for number in used_range:
                        used_indices.append(number)


    return_list.append(transect_numbers)
    return_list.append(transect_start_dates)
    return_list.append(transect_end_dates)
    return_list.append(transect_deltas)

    return(return_list)

def main(argv=None):
    """
    -Does this

    :return: none
    """

    if argv is None:
        argv = sys.argv[1:]

    # initialize argument parser
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description = "")

    # assign input arguments.
    parser.add_argument("-g", "--glider", dest="glider_name", type=str,
                        required=True, help="Glider name, i.e., GA05MOAS-GL364")
    parser.add_argument("-d", "--deployment", dest="deployment_number", type=int,
                        required=True, help="Glider deployment, i.e., 2")
    parser.add_argument("-s", "--save", dest="save_dir", type=str,
                        required=True, help="Directory to save files")
    parser.add_argument("-t", "--file_type", dest="file_type", type=str,
                        required=True, choices=['ma', 'ds', 'sbd', 'meta'],
                        help="File type to process. Options are ma (ma files), \
                        ds (dockserver logs), or sbd (short binary data)")

    # parse the input arguments and create a parser object
    args = parser.parse_args(argv)
    file_type = args.file_type
    save_dir = args.save_dir
    glider_name = args.glider_name
    deployment_number = args.deployment_number

    # Set the base URL for the OOI Raw Data Repo
    rdr_base_url = "https://rawdata.oceanobservatories.org/files/"

    # Set up local input and output directories
    input_dir = save_dir+"/input/"+glider_name+"/D"+str(deployment_number).zfill(5)
    output_dir = save_dir+"/output/"+glider_name+"/D"+str(deployment_number).zfill(5)

    # Process either the MA files or dockserver log files for a given glider/deployment
    # MA file processing below
    if file_type.lower() == "ma":
        # Make sure the local sub-directories exist and create them if not
        local_dir = save_dir+"/input/"+glider_name+"/D"+str(deployment_number).zfill(5)+"/mafiles"
        if not (os.path.isdir(local_dir)):
            print("Directory "+local_dir+" does not exist. Making it now.")
            os.makedirs(local_dir)

        # Generate and validate the OOI Raw Data Repo URL for the MA file directory
        ma_directory = glider_name+"/D"+str(deployment_number).zfill(5)+"/archive/"
        full_url = urljoin(rdr_base_url, ma_directory)

        # Get a listing of MA files that already exist locally
        local_existing_files = glob.glob(local_dir+"/*.ma")

        # If the URL is valid, download the MA files in the directory to a local machine
        if (validate_url(full_url)):
            file_urls = get_file_urls(full_url)
            for url in file_urls:
                if url.split("/")[-1] not in '\t'.join(local_existing_files):
                    download_file(full_url, url, local_dir, "yo")

            # Parse the files
            local_files = glob.glob(local_dir+"/*.ma")

            # Extract the date from the filename for each MA file
            file_dates = []
            file_names = []
            for file in local_files:
                temp_fname_date = parse_date_from_file_name(file)
                file_dates.append(temp_fname_date.replace(tzinfo=timezone.utc).timestamp())
                file_names.append(file.split("/")[-1])

            # Create a dataframe to store information from the MA files
            df = pd.DataFrame({'File_Name': file_names, 'Datetime': file_dates})

            # Determine which values should be extracted from each ma file
            ma_values_to_extract = ["b_arg: d_target_depth", "b_arg: d_target_altitude",
                "b_arg: d_use_bpump", "b_arg: d_bpump_value", "b_arg: d_speed_min",
                "b_arg: d_use_pitch", "b_arg: d_pitch_value",
                "b_arg: c_target_depth", "b_arg: c_target_altitude", "b_arg: c_use_bpump",
                "b_arg: c_bpump_value", "b_arg: c_speed_min", "b_arg: c_use_pitch",
                "b_arg: c_pitch_value"]

            # Iterate through each MA file to extract the values and store them
            for value in ma_values_to_extract:
                extracted_values = []
                for file in local_files:
                    parsed_output = parse_file(file, value)
                    extracted_values.append(parsed_output)
                # Add the extracted values to the existing dataframe
                df[value] = extracted_values

            # Sort the dataframe by date and save it
            df = df.sort_values('Datetime')
            csv_name = save_dir+"/output/"+glider_name+"/D"+str(deployment_number).zfill(5)+"/"+glider_name+"_D"+str(deployment_number).zfill(5)+"_ma_file_extractions.csv"
            df.to_csv(csv_name, index=False)

        # Dockserver log file processing below
    elif file_type.lower() == "ds":
        # Make sure the local sub-directories exist and create them if not
        input_dir = input_dir+"/dockserver_logs"
        if not (os.path.isdir(input_dir)):
            print("Directory "+input_dir+" does not exist. Making it now.")
            os.makedirs(input_dir)

        if not (os.path.isdir(output_dir)):
            print("Directory "+output_dir+" does not exist. Making it now.")
            os.makedirs(output_dir)

        # Generate and validate the OOI Raw Data Repo URL for the DS file directory
        ds_directory = glider_name+"/D"+str(deployment_number).zfill(5)+"/logs/"
        full_url = urljoin(rdr_base_url, ds_directory)

        # Get a listing of MA files that already exist locally
        local_existing_files = glob.glob(input_dir+"/*.log")

        # If the URL is valid, download the DS files in the directory to a local machine
        if (validate_url(full_url)):
            file_urls = get_file_urls(full_url, '.log')
            for url in file_urls:
                if url.split("/")[-1] not in '\t'.join(local_existing_files):
                    download_file(full_url, url, input_dir, glider_name[11:])

            # Get the glider deployment info and line
            deploy_csv = save_dir + "input/"+glider_name+"/"+glider_name+"_Deploy.csv"
            deploy_info = pd.read_csv(deploy_csv)
            this_deployment = deploy_info.loc[(deploy_info["deploymentNumber"] == deployment_number)]

            deploy_csv_start_date = max(this_deployment['startDateTime'])
            deploy_start_datetime = datetime.datetime.strptime(deploy_csv_start_date, "%Y-%m-%dT%H:%M:%S")
            deploy_start_datetime = deploy_start_datetime.replace(tzinfo=timezone.utc).timestamp()

            deploy_csv_end_date = max(this_deployment['stopDateTime'])

            if pd.isnull(deploy_csv_end_date):
                deploy_end_datetime = datetime.datetime.now().timestamp()
            else:
                deploy_end_datetime = datetime.datetime.strptime(deploy_csv_end_date, "%Y-%m-%dT%H:%M:%S")
                deploy_end_datetime = deploy_end_datetime.replace(tzinfo=timezone.utc).timestamp()

            line = this_deployment["notes"].mode()[0].split(",")[0]

            # Parse the files
            local_files = glob.glob(input_dir+"/*.log")

            # Extract the date from the filename for each DS log file
            file_dates = []
            file_names = []
            for file in local_files:
                temp_fname_date = parse_date_from_file_name(file)
                file_dates.append(temp_fname_date.replace(tzinfo=timezone.utc).timestamp())
                file_names.append(file.split("/")[-1])

            # Create a dataframe to store information from the DS log files
            df = pd.DataFrame({'File_Name': file_names, 'Datetime': file_dates})
            df['Glider'] = glider_name[-3:]
            df['Deployment'] = deployment_number

            # Determine which values should be extracted from each DS log file
            ds_values_to_extract = ["c_wpt_lat", "c_wpt_lon",
            "GPS Location:", "m_tot_horz_dist"]

           # ds_values_to_extract = ["c_wpt_lat"]

            # Iterate through each DS log file to extract the values and store them
            for value in ds_values_to_extract:
                extracted_values = []
                if value == "GPS Location:":
                    lat_values = []
                    lon_values = []
                    age_values = []
                    for file in local_files:
                        parsed_output = parse_file(file, value)
                        if parsed_output[0] == "No match.":
                            lat_values.append(-1)
                        if parsed_output[1] == "No match.":
                            lon_values.append(-1)
                        if parsed_output[2] == "No match.":
                            age_values.append(-1)
                        elif "696969" in parsed_output[0]:
                            lat_values.append(-1)
                            lon_values.append(-1)
                            age_values.append(-1)
                        else:
                            #lat_values.append(parsed_output[0])
                            #print(parsed_output[0])
                            lat_values.append(parsed_output[0])
                            lon_values.append(parsed_output[1])
                            age_values.append(parsed_output[2])


                    df['GPS_Lat'] = lat_values
                    df['GPS_Lon'] = lon_values
                    df['GPS_Age'] = age_values

                    # add in the line
                    df['Line'] = line
                elif value == "c_wpt_lat":
                    wpt_lat_values = []
                    for file in local_files:
                        parsed_output = parse_file(file, value)
                        if parsed_output == "No match.":
                            wpt_lat_values.append(-1)
                        elif parsed_output == "0":
                            wpt_lat_values.append(-1)
                        else:
                            wpt_lat_values.append(parsed_output)
                    df['WPT_Lat'] = wpt_lat_values
                elif value == "c_wpt_lon":
                    wpt_lon_values = []
                    for file in local_files:
                        parsed_output = parse_file(file, value)
                        if parsed_output == "No match.":
                            wpt_lon_values.append(-1)
                        elif parsed_output == "0":
                            wpt_lon_values.append(-1)
                        else:
                            wpt_lon_values.append(parsed_output)
                    df['WPT_Lon'] = wpt_lon_values
                else:
                    for file in local_files:
                        parsed_output = parse_file(file, value)
                        extracted_values.append(parsed_output)
                    # Add the extracted values to the existing dataframe
                    df[value] = extracted_values
                    # add in the line
                    df['Line'] = line

            # Calculate distance to waypoint
            df = df.sort_values('Datetime')
            df = df.reset_index()

            bounds = []
            distances = []

            if "FZ" in line:
                FZ_box = np.array([[39.833, 70.375], # SE corner
                    [40.083, 70.375], # NE corner
                    [40.083, 71.167], # NW corner
                    [39.833, 71.167]]) # SW corner
                distances_to_SE = []
                distances_to_NE = []
                distances_to_NW = []
                distances_to_SW = []
                SE_flags = []
                NE_flags = []
                NW_flags = []
                SW_flags = []

            if "EB" in line:
                EB_line = np.array([[39.833, 70.000], # SE corner
                                    [39.967,70.000], # mid-E
                                    [40.400, 70.000], # far-N wpt
                                    [40.083, 70.190], # W corner on shelf
                                    [39.967, 70.190], # mid-W
                                    [39.833, 70.190] # SW corner
                                    ])
                distances_to_SE = []
                distances_to_mid_E = []
                distances_to_N = []
                distances_to_W = []
                distances_to_mid_W = []
                distances_to_SW = []
                SE_flags = []
                mid_E_flags = []
                N_flags = []
                W_flags = []
                mid_W_flags = []
                SW_flags = []


            if "SS-1" in line:
                SS1_line = np.array([[39.333, 70.000], # SE wpt
                                    [39.833, 70.000], # NE wpt
                                    [39.333, 70.583],  # S-mid wpt
                                    [39.833, 71.167], # NW wpt
                                    [39.333, 71.167], # SW wpt
                                    [39.833, 70.583] # N-mid wpt
                                    ])
                distances_to_SE = []
                distances_to_NE = []
                distances_to_S_mid = []
                distances_to_NW = []
                distances_to_SW = []
                distances_to_N_mid = []
                SE_flags = []
                NE_flags = []
                S_mid_flags = []
                NW_flags = []
                SW_flags = []
                N_mid_flags = []



            if "SS-2" in line:
                SS2_line = np.array([[39.333, 70.292], # SE point
                                    [39.583, 70.000], # mid-E wpt
                                    [39.833, 70.292], # NE wpt
                                    [39.333, 70.875], # SW wpt
                                    [39.583, 71.167], # mid-W wpt
                                    [39.833, 70.875], # NW wpt
                                    ])
                distances_to_SE = []
                distances_to_mid_E = []
                distances_to_NE = []
                distances_to_SW = []
                distances_to_mid_W = []
                distances_to_NW = []
                SE_flags = []
                mid_E_flags = []
                NE_flags = []
                SW_flags = []
                mid_W_flags = []
                NW_flags = []


            decimal_gps_lats = []
            decimal_gps_lons = []
            decimal_wpt_lats = []
            decimal_wpt_lons = []

            for index, row in df.iterrows():
                gps_lat = row['GPS_Lat']
                gps_lon = row['GPS_Lon']
                wpt_lat = row['WPT_Lat']
                wpt_lon = row['WPT_Lon']

                #
                if wpt_lat == -1:
                    decimal_wpt_lat = -1
                    distance = "n/a"
                else:
                    decimal_wpt_lat = parse_wpt_lat(wpt_lat)
                decimal_wpt_lats.append(decimal_wpt_lat)


                #
                if wpt_lon == -1:
                    decimal_wpt_lon = -1
                    distance = "n/a"
                else:
                    decimal_wpt_lon = parse_wpt_lon(wpt_lon)
                decimal_wpt_lons.append(decimal_wpt_lon)

                #
                if gps_lat == -1:
                    decimal_gps_lat = -1
                else:
                    decimal_gps_lat = parse_gps_lat(gps_lat)
                decimal_gps_lats.append(decimal_gps_lat)

                #
                if gps_lon == -1:
                    decimal_gps_lon = -1
                else:
                    decimal_gps_lon = parse_gps_lon(gps_lon)
                decimal_gps_lons.append(decimal_gps_lon)


                if decimal_gps_lat == -1 or decimal_gps_lon == -1 or decimal_wpt_lat == -1 or decimal_wpt_lon == -1:
                    distance = -1
                else:
                    distance = calculate_distance_from_waypoint(decimal_gps_lat, decimal_gps_lon, decimal_wpt_lat, decimal_wpt_lon)


                #bound = calculate_fz(decimal_wpt_lat, decimal_wpt_lon)
                #bounds.append(bound)
                distances.append(distance)

                #
                if "FZ" in line:
                    distance_to_SE = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, FZ_box[0][0], FZ_box[0][1])
                    distance_to_NE = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, FZ_box[1][0], FZ_box[1][1])
                    distance_to_NW = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, FZ_box[2][0], FZ_box[2][1])
                    distance_to_SW = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, FZ_box[3][0], FZ_box[3][1])

                    distance_threshold = 10000
                    SE_flag = 0
                    NE_flag = 0
                    NW_flag = 0
                    SW_flag = 0

                    if distance_to_SE < distance_threshold:
                        SE_flag = 1
                    if distance_to_NE < distance_threshold:
                        NE_flag = 1
                    if distance_to_NW < distance_threshold:
                        NW_flag = 1
                    if distance_to_SW < distance_threshold:
                        SW_flag = 1

                    distances_to_SE.append(distance_to_SE)
                    distances_to_NE.append(distance_to_NE)
                    distances_to_NW.append(distance_to_NW)
                    distances_to_SW.append(distance_to_SW)

                    SE_flags.append(SE_flag)
                    NE_flags.append(NE_flag)
                    NW_flags.append(NW_flag)
                    SW_flags.append(SW_flag)

                if "EB" in line:
                    distance_to_SE = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, EB_line[0][0], EB_line[0][1])
                    distance_to_mid_E = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, EB_line[1][0], EB_line[1][1])
                    distance_to_N = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, EB_line[2][0], EB_line[2][1])
                    distance_to_W = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, EB_line[3][0], EB_line[3][1])
                    distance_to_mid_W = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, EB_line[4][0], EB_line[4][1])
                    distance_to_SW = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, EB_line[5][0], EB_line[5][1])

                    distance_threshold = 10000
                    SE_flag = 0
                    mid_E_flag = 0
                    N_flag = 0
                    mid_W_flag = 0
                    W_flag = 0
                    SW_flag = 0

                    if distance_to_SE < distance_threshold:
                        SE_flag = 1
                    if distance_to_mid_E < distance_threshold:
                        mid_E_flag = 1
                    if distance_to_N < distance_threshold:
                        N_flag = 1
                    if distance_to_W < distance_threshold:
                        W_flag = 1
                    if distance_to_mid_W < distance_threshold:
                        mid_W_flag = 1
                    if distance_to_SW < distance_threshold:
                        SW_flag = 1

                    distances_to_SE.append(distance_to_SE)
                    distances_to_mid_E.append(distance_to_mid_E)
                    distances_to_N.append(distance_to_N)
                    distances_to_W.append(distance_to_W)
                    distances_to_mid_W.append(distance_to_mid_W)
                    distances_to_SW.append(distance_to_SW)

                    SE_flags.append(SE_flag)
                    mid_E_flags.append(mid_E_flag)
                    N_flags.append(N_flag)
                    W_flags.append(W_flag)
                    mid_W_flags.append(mid_W_flag)
                    SW_flags.append(SW_flag)

                if "SS-1" in line:
                    distance_to_SE = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, SS1_line[0][0], SS1_line[0][1])
                    distance_to_NE = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, SS1_line[1][0], SS1_line[1][1])
                    distance_to_S_mid = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, SS1_line[2][0], SS1_line[2][1])
                    distance_to_NW = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, SS1_line[3][0], SS1_line[3][1])
                    distance_to_SW = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, SS1_line[4][0], SS1_line[4][1])
                    distance_to_N_mid = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, SS1_line[5][0], SS1_line[5][1])

                    distance_threshold = 10000
                    SE_flag = 0
                    NE_flag = 0
                    S_mid_flag = 0
                    NW_flag = 0
                    SW_flag = 0
                    N_mid_flag = 0

                    if distance_to_SE < distance_threshold:
                        SE_flag = 1
                    if distance_to_NE < distance_threshold:
                        NE_flag = 1
                    if distance_to_S_mid < distance_threshold:
                        S_mid_flag = 1
                    if distance_to_NW < distance_threshold:
                        NW_flag = 1
                    if distance_to_SW < distance_threshold:
                        SW_flag = 1
                    if distance_to_N_mid < distance_threshold:
                        N_mid_flag = 1

                    distances_to_SE.append(distance_to_SE)
                    distances_to_NE.append(distance_to_NE)
                    distances_to_S_mid.append(distance_to_S_mid)
                    distances_to_NW.append(distance_to_NW)
                    distances_to_SW.append(distance_to_SW)
                    distances_to_N_mid.append(distance_to_N_mid)

                    SE_flags.append(SE_flag)
                    NE_flags.append(NE_flag)
                    S_mid_flags.append(S_mid_flag)
                    NW_flags.append(NW_flag)
                    SW_flags.append(SW_flag)
                    N_mid_flags.append(N_mid_flag)

                if "SS-2" in line:
                    distance_to_SE = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, SS2_line[0][0], SS2_line[0][1])
                    distance_to_mid_E = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, SS2_line[1][0], SS2_line[1][1])
                    distance_to_NE = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, SS2_line[2][0], SS2_line[2][1])
                    distance_to_SW = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, SS2_line[3][0], SS2_line[3][1])
                    distance_to_mid_W = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, SS2_line[4][0], SS2_line[4][1])
                    distance_to_NW = calculate_distance_from_waypoint(decimal_gps_lat,
                        decimal_gps_lon, SS2_line[5][0], SS2_line[5][1])

                    distance_threshold = 10000
                    SE_flag = 0
                    mid_E_flag = 0
                    NE_flag = 0
                    SW_flag = 0
                    mid_W_flag = 0
                    NW_flag = 0

                    if distance_to_SE < distance_threshold:
                        SE_flag = 1
                    if distance_to_mid_E < distance_threshold:
                        mid_E_flag = 1
                    if distance_to_NE < distance_threshold:
                        NE_flag = 1
                    if distance_to_SW < distance_threshold:
                        SW_flag = 1
                    if distance_to_mid_W < distance_threshold:
                        mid_W_flag = 1
                    if distance_to_NW < distance_threshold:
                        NW_flag = 1

                    distances_to_SE.append(distance_to_SE)
                    distances_to_mid_E.append(distance_to_mid_E)
                    distances_to_NE.append(distance_to_NE)
                    distances_to_SW.append(distance_to_SW)
                    distances_to_mid_W.append(distance_to_mid_W)
                    distances_to_NW.append(distance_to_NW)

                    SE_flags.append(SE_flag)
                    mid_E_flags.append(mid_E_flag)
                    NE_flags.append(NE_flag)
                    SW_flags.append(SW_flag)
                    mid_W_flags.append(mid_W_flag)
                    NW_flags.append(NW_flag)

                #if row['m_gps_heading'] == "No match.":
                #    heading_deg = "No match."
                #else:
                #    heading_deg = float(row['m_gps_heading'])*(180/math.pi)
                #headings.append(heading_deg)

            #
            #df['Track_Portion'] = bounds
            df['Distance_to_waypoint'] = distances
            #df.drop('Heading(deg)', axis=1, inplace=True)
            df['GPS_Lat(DD)'] = decimal_gps_lats
            df['GPS_Lon(DD)'] = decimal_gps_lons
            df['WPT_Lat(DD)'] = decimal_wpt_lats
            df['WPT_Lon(DD)'] = decimal_wpt_lons

            if "FZ" in line:
                df['Distance_to_SE_WPT'] = distances_to_SE
                df['Distance_to_NE_WPT'] = distances_to_NE
                df['Distance_to_NW_WPT'] = distances_to_NW
                df['Distance_to_SW_WPT'] = distances_to_SW
                df['AT_SE_WPT'] = SE_flags
                df['AT_NE_WPT'] = NE_flags
                df['AT_NW_WPT'] = NW_flags
                df['AT_SW_WPT'] = SW_flags

            if "EB" in line:
                df['Distance_to_SE_WPT'] = distances_to_SE
                df['Distance_to_mid_E_WPT'] = distances_to_mid_E
                df['Distance_to_N_WPT'] = distances_to_N
                df['Distance_to_W_WPT'] = distances_to_W
                df['Distance_to_mid_W_WPT'] = distances_to_mid_W
                df['Distance_to_SW_WPT'] = distances_to_SW
                df['AT_SE_WPT'] = SE_flags
                df['AT_MID_E_WPT'] = mid_E_flags
                df['AT_N_WPT'] = N_flags
                df['AT_W_WPT'] = W_flags
                df['AT_MID_W_WPT'] = mid_W_flags
                df['AT_SW_WPT'] = SW_flags

            if "SS-1" in line:
                df['Distance_to_SE_WPT'] = distances_to_SE
                df['Distance_to_NE_WPT'] = distances_to_NE
                df['Distance_to_mid_S_WPT'] = distances_to_S_mid
                df['Distance_to_NW_WPT'] = distances_to_NW
                df['Distance_to_SW_WPT'] = distances_to_SW
                df['Distance_to_mid_N_WPT'] = distances_to_N_mid

                df['AT_SE_WPT'] = SE_flags
                df['AT_NE_WPT'] = NE_flags
                df['AT_MID_N_WPT'] = N_mid_flags
                df['AT_NW_WPT'] = NW_flags
                df['AT_SW_WPT'] = SW_flags
                df['AT_MID_S_WPT'] = N_mid_flags

            if "SS-2" in line:
                df['Distance_to_SE_WPT'] = distances_to_SE
                df['Distance_to_mid_E_WPT'] = distances_to_mid_E
                df['Distance_to_NE_WPT'] = distances_to_NE
                df['Distance_to_SW_WPT'] = distances_to_SW
                df['Distance_to_mid_W_WPT'] = distances_to_mid_W
                df['Distance_to_NW_WPT'] = distances_to_NW

                df['AT_SE_WPT'] = SE_flags
                df['AT_MID_E_WPT'] = mid_E_flags
                df['AT_NE_WPT'] = NE_flags
                df['AT_SW_WPT'] = SW_flags
                df['AT_MID_W_WPT'] = mid_W_flags
                df['AT_NW_WPT'] = NW_flags


            # Clean up the dataframe for out of place files
            drop_files = []
            glider = glider_name[-3:]
            for index, row in df.iterrows():
                drop_file = 0
                file = row['File_Name']
                if glider not in file:
                    drop_file = 1
                else:
                    drop_file = 0

                file_date = float(row['Datetime'])
                if file_date < deploy_start_datetime or file_date > deploy_end_datetime:
                    drop_file = 1
                    #print("Dropping: "+ file)

                drop_files.append(drop_file)

            df["Drop_me"] = drop_files
            df = df[df["Drop_me"] < 1]
            df.drop('Drop_me', axis=1, inplace=True)
            df.drop('index', axis=1, inplace=True)
            df.drop('WPT_Lat', axis=1, inplace=True)
            df.drop('WPT_Lon', axis=1, inplace=True)
            df.drop('GPS_Lat', axis=1, inplace=True)
            df.drop('GPS_Lon', axis=1, inplace=True)
            df_cols = df.columns.tolist()
            cols = ['Glider', 'Deployment', 'File_Name', 'Datetime', 'Line', 'GPS_Lat(DD)', 'GPS_Lon(DD)', 'WPT_Lat(DD)', 'WPT_Lon(DD)', 'm_tot_horz_dist', 'Distance_to_waypoint'] + df_cols[11:]
            df = df[cols]

            # Last science stuff
            last_science_df = pd.read_csv("/Users/cdobson/Documents/Datateam/biofouling_project/input/last_science_dates.csv")
            first_slice = last_science_df[last_science_df['Glider']==int(glider)]
            second_slice = first_slice[first_slice['Deployment']==int(deployment_number)]
            science_off = second_slice['ScienceOffDatetime'].values[0]
            print("Science off: "+str(science_off))

            science_on_flags = []
            for index, row in df.iterrows():
                science_on_flag = 0
                if row['Datetime'] < science_off:
                    #print("yes")
                    science_on_flag= 1
                else:
                    science_on_flag = 0
                science_on_flags.append(science_on_flag)

            df["Science_on"] = science_on_flags

            # Sort the dataframe by date and save it
            df = df.sort_values('Datetime')
            csv_name = output_dir+"/"+glider_name+"_D"+str(deployment_number).zfill(5)+"_ds_logfile_extractions.csv"
            df.to_csv(csv_name, index=False)


            # Save the csv a second time
            if "FZ" in line:
                csv_save = save_dir+"output/FZ_Gliders/"+glider_name+"_D"+str(deployment_number).zfill(5)+"_ds_logfile_extractions.csv"
            elif "SS-1" in line:
                csv_save = save_dir+"output/SS-1_Gliders/"+glider_name+"_D"+str(deployment_number).zfill(5)+"_ds_logfile_extractions.csv"
            elif "SS-2" in line:
                csv_save = save_dir+"output/SS-2_Gliders/"+glider_name+"_D"+str(deployment_number).zfill(5)+"_ds_logfile_extractions.csv"
            elif "EB" in line:
                csv_save = save_dir+"output/EB_Gliders/"+glider_name+"_D"+str(deployment_number).zfill(5)+"_ds_logfile_extractions.csv"
            else:
                csv_save = save_dir+"output/No-Line_Gliders/"+glider_name+"_D"+str(deployment_number).zfill(5)+"_ds_logfile_extractions.csv"

            df.to_csv(csv_save, index=False)

    elif file_type.lower() == "meta":
        all_gliders = []
        all_deployments = []
        all_lines = []
        all_transect_numbers = []
        all_start_dates = []
        all_end_dates = []
        all_deltas = []
        all_paths = []

        lines = ["EB", "FZ", "SS-1", "SS-2"]
        for line in lines:
            base_dir = save_dir+"output/"+line+"_Gliders"
            os.chdir(base_dir)
            all_filenames = [i for i in glob.glob('*.{}'.format("csv"))]
            all_filenames.sort()

            for file in all_filenames:
                if "Combined" not in file:
                    file_split = file.split("_")
                    glider = file_split[0][-3:]
                    deployment = file_split[1].strip("D").lstrip("0")
                    if line == "EB":
                        wpt_pairs = [
                                      ['AT_SW_WPT', 'AT_SE_WPT'],
                                      ['AT_SE_WPT', 'AT_MID_E_WPT'],
                                      ['AT_MID_E_WPT', 'AT_N_WPT'],
                                      ['AT_N_WPT', 'AT_W_WPT'],
                                      ['AT_W_WPT', 'AT_MID_W_WPT'],
                                      ['AT_MID_W_WPT', 'AT_SW_WPT'],
                                      ['AT_SE_WPT', 'AT_SE_WPT']
                                    ]
                        for wpt_pair in wpt_pairs:
                            transect_info = count_transects(save_dir, glider, deployment, "EB", wpt_pair[0], wpt_pair[1])

                            transects = transect_info[0]
                            start_dates = transect_info[1]
                            end_dates = transect_info[2]
                            deltas = transect_info[3]

                            i = 0
                            for transect in transects:
                                all_gliders.append(glider)
                                all_deployments.append(deployment)
                                all_lines.append(line)
                                all_transect_numbers.append(transects[i])
                                all_start_dates.append(start_dates[i])
                                all_end_dates.append(end_dates[i])
                                all_deltas.append(deltas[i])
                                all_paths.append(wpt_pair[0]+":"+wpt_pair[1])
                                i+=1

                    elif line == "FZ":
                        wpt_pairs = [
                                      ['AT_SW_WPT', 'AT_SE_WPT'],
                                      ['AT_SE_WPT', 'AT_NE_WPT'],
                                      ['AT_NE_WPT', 'AT_NW_WPT'],
                                      ['AT_NW_WPT', 'AT_SW_WPT'],
                                      ['AT_SE_WPT', 'AT_SE_WPT']
                                    ]
                        for wpt_pair in wpt_pairs:
                            transect_info = count_transects(save_dir, glider, deployment, "FZ", wpt_pair[0], wpt_pair[1])

                            transects = transect_info[0]
                            start_dates = transect_info[1]
                            end_dates = transect_info[2]
                            deltas = transect_info[3]

                            i = 0
                            for transect in transects:
                                all_gliders.append(glider)
                                all_deployments.append(deployment)
                                all_lines.append(line)
                                all_transect_numbers.append(transects[i])
                                all_start_dates.append(start_dates[i])
                                all_end_dates.append(end_dates[i])
                                all_deltas.append(deltas[i])
                                all_paths.append(wpt_pair[0]+":"+wpt_pair[1])
                                i+=1

                    elif line == "SS-1":
                        wpt_pairs = [
                                    ['AT_SE_WPT', 'AT_NE_WPT'],
                                    ['AT_NE_WPT','AT_MID_S_WPT'],
                                    ['AT_MID_S_WPT','AT_NW_WPT'],
                                    ['AT_NW_WPT','AT_SW_WPT'],
                                    ['AT_SW_WPT','AT_MID_N_WPT'],
                                    ['AT_MID_N_WPT', 'AT_SE_WPT'],
                                    ['AT_SE_WPT', 'AT_SE_WPT']
                                    ]

                        for wpt_pair in wpt_pairs:
                            transect_info = count_transects(save_dir, glider, deployment, "SS-1", wpt_pair[0], wpt_pair[1])
                            transects = transect_info[0]
                            start_dates = transect_info[1]
                            end_dates = transect_info[2]
                            deltas = transect_info[3]

                            i = 0
                            for transect in transects:
                                all_gliders.append(glider)
                                all_deployments.append(deployment)
                                all_lines.append(line)
                                all_transect_numbers.append(transects[i])
                                all_start_dates.append(start_dates[i])
                                all_end_dates.append(end_dates[i])
                                all_deltas.append(deltas[i])
                                all_paths.append(wpt_pair[0]+":"+wpt_pair[1])
                                i+=1

                    elif line == "SS-2":
                        wpt_pairs = [
                                    ['AT_SE_WPT','AT_MID_E_WPT'],
                                    ['AT_MID_E_WPT', 'AT_NE_WPT'],
                                    ['AT_NE_WPT','AT_SW_WPT'],
                                    ['AT_SW_WPT', 'AT_MID_W_WPT'],
                                    ['AT_MID_W_WPT', 'AT_NW_WPT'],
                                    ['AT_NW_WPT','AT_SE_WPT'],
                                    ['AT_SE_WPT','AT_SE_WPT']
                                    ]

                        for wpt_pair in wpt_pairs:
                            transect_info = count_transects(save_dir, glider, deployment, "SS-2", wpt_pair[0], wpt_pair[1])
                            transects = transect_info[0]
                            start_dates = transect_info[1]
                            end_dates = transect_info[2]
                            deltas = transect_info[3]

                            i = 0
                            for transect in transects:
                                all_gliders.append(glider)
                                all_deployments.append(deployment)
                                all_lines.append(line)
                                all_transect_numbers.append(transects[i])
                                all_start_dates.append(start_dates[i])
                                all_end_dates.append(end_dates[i])
                                all_deltas.append(deltas[i])
                                all_paths.append(wpt_pair[0]+":"+wpt_pair[1])
                                i+=1


            df = pd.DataFrame({'Glider': all_gliders, 'Deployment': all_deployments,
                                'Line': all_lines, 'Transect': all_transect_numbers,
                                'Transect_Start': all_start_dates, 'Transect_End': all_end_dates, 'Transect_Total_Time': all_deltas,
                                'Path': all_paths
            })

            csv_name = save_dir+"output/All_CGSN_Transects.csv"
            df.to_csv(csv_name, index=False, encoding='utf-8-sig')



    elif file_type.lower() == "sbd":
        local_dir = save_dir+"/input/"+glider_name+"/D"+str(deployment_number).zfill(5)+"/sbd"
        local_existing_files = glob.glob(local_dir+"/*sbd.asc")

        sbd_directory = glider_name+"/D"+str(deployment_number).zfill(5)+"/merged-from-glider/"
        full_url = urljoin(rdr_base_url, sbd_directory)

        # Get a listing of sbd files that already exist locally
        local_existing_files = glob.glob(local_dir+"/*sbd.asc")

        # If the URL is valid, download the DS files in the directory to a local machine
        if (validate_url(full_url)):
            file_urls = get_file_urls(full_url, 'sbd.asc')
            for url in file_urls:
                if url.split("/")[-1] not in '\t'.join(local_existing_files):
                    download_file(full_url, url, local_dir, glider_name[11:])

        # Assign the deployment start and end dates
        deployment_start = datetime.datetime(2020, 8, 15, 14, 37, 0)
        deployment_end =  datetime.datetime(2021, 8, 11, 15, 32, 0)

        # Get a list of all sbd files
        local_files = glob.glob(local_dir+"/*.asc")
        local_files = natural_sort(local_files)

        # Set all time counters to 0
        time_spent_in_drift = 0
        time_spent_in_mission = 0
        time_spent_on_surface_in_mission = 0
        total_time_on_surface = 0

        #
        time_on_surface_values = []
        dates = []
        epoch_dates = []
        file_names = []
        # Iterate through and process each sbd file
        for sbd in local_files:
            if sbd.split("/")[-1] == "ga_538_2016_182_0_45_sbd.asc":
                continue
            if sbd.split("/")[-1] == "ga_538_2016_182_0_47_sbd.asc":
                continue
            if sbd.split("/")[-1] == "ga_538_2016_182_0_46_sbd.asc":
                continue
            # Read in the header file of the sbd file
            sbd_contents = open(sbd).read().split("\n")[0:17]
            # Find index with mission name and glider names to extract info
            for i, s in enumerate(sbd_contents):
                if "mission_name" in s:
                    mission_name_index = i
                if "segment_filename" in s:
                    glider_name_index = i
            mission_name = sbd_contents[mission_name_index].split(":")[-1]
            file_glider_name = sbd_contents[glider_name_index].split(":")[-1][4:7]

            # Read each sbd file into a demporary dataframe
            temp_df = pd.read_csv(sbd, delimiter=r"\s+", error_bad_lines=False, skiprows=14)
            temp_df = temp_df.iloc[2:, :]

            # Find the min and max timestamps in each file and calculate the delta
            time_min = float(temp_df['m_present_time'].min())
            time_max = float(temp_df['m_present_time'].max())
            time_delta = time_max - time_min
            if (time_delta > 1000000):
                print(sbd.split("/")[-1])
                print(time_delta)

            # Calculate the delta from deployment start to mission start
            time_max_datetime = datetime.datetime.utcfromtimestamp(time_max)
            time_min_datetime = datetime.datetime.utcfromtimestamp(time_min)
            deployment_delta = (time_max_datetime - deployment_start).total_seconds()
            #print(sbd.split("/")[-1])
            #print(deployment_delta)
            #print(deployment_delta)

            # Skip over log files created before the official deployment start
            if deployment_delta < 0:
                continue

            # Skip over log files that are not for this glider
            if file_glider_name not in glider_name:
                continue

            # Isolate the sdriftxx.mi missions and add their time
            if "drift" in mission_name.lower():
                time_spent_in_drift += time_delta
            else:
                # Identify the max depth for each non-drift mission
                depths = temp_df['m_depth']
                depths = [float(x) for x in depths]
                depths = [x for x in depths if np.isnan(x) == False]
                max_depth = max(depths)

                # Isolate missions where the glider left the surface
                if max_depth > 1:
                    time_spent_in_mission = time_spent_in_mission + time_delta
                else:
                    # If the glider did not leave the surface for the mission, add
                    # the delta to the surface time
                    time_spent_on_surface_in_mission += time_delta

            # Calculate cumulative time on surface thus far
            total_time_on_surface = (deployment_delta - time_spent_in_mission)
            #print(total_time_on_surface)

            time_on_surface_values.append(total_time_on_surface/86400)

            dates.append(time_max_datetime)
            epoch_dates.append(time_max_datetime.replace(tzinfo=timezone.utc).timestamp())

            file_names.append(sbd)

        # Add the deployment end date
        dates.append(deployment_end)
        epoch_dates.append(deployment_end.replace(tzinfo=timezone.utc).timestamp())
        file_names.append(sbd)

        # Calculate the time on surface between deployment end and last sbd
        end_deployment_gap = deployment_end - time_max_datetime
        end_deployment_value = end_deployment_gap.days
        time_on_surface_values.append(end_deployment_value)

        plt.title("GA05MOAS-GL364 D00002 Time Spent on Surface")
        plt.plot(dates, time_on_surface_values)
        save_dir = save_dir+"/output/"+glider_name+"/D"+str(deployment_number).zfill(5)+"/"
        plt.xticks(rotation = -45)
        plt.ylabel("Time spent on surface (days)")
        plt.tight_layout()
        plt.savefig(save_dir+"test.png")


        # Create a dataframe to store information from the sbd files
        df = pd.DataFrame({'Date': dates, 'Datetime': epoch_dates, 'Days on surface': time_on_surface_values})
        df = df.sort_values('Datetime')
        df.to_csv(save_dir+glider_name+"_D"+str(deployment_number).zfill(5)+"_time_on_surface.csv", index=False)

    else:
        print("Invalid file type specified. File type needs to be ma or ds.")


if __name__ == '__main__':
    main()
