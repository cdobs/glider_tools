import os
import re
import glob
import configparser
from math import trunc
import xml.dom.minidom

#raw_data_dir = '/Volumes/data/'
raw_data_dir = '/srv/fmc-data/raw/'
ge_template = 'archive.kml'
config_file = 'archive_config.py'

class Archive:
    def __init__(self, glider, dnum, cruise):
        self.glider = glider
        self.dnum = dnum
        self.cruise = cruise
        self.log_path = self.generate_ds_path(raw_data_dir)
        self.ds_logs = self.get_files()
        self.ge_string = ''
        self.ge_strings = []
        # Parse the dockserver logs 
        self.parse_logs()


    def generate_ds_path(self, raw_data_dir):
        """
        Generate the path to dockserver logs for a specific glider deployment 
        """
        ds_log_path = os.path.join(raw_data_dir, self.glider)
        ds_log_path = os.path.join(ds_log_path,'D'+str(self.dnum).zfill(5))
        ds_log_path = os.path.join(ds_log_path, 'logs')
        return ds_log_path 

    def get_files(self):
        """
        Get a sorted list of dockserver log files for a given glider deployment 
        """
        ds_file_list = glob.glob(self.log_path+"/*.log")
        ds_file_list.sort(key=lambda str: re.findall("[0-9]{8}T[0-9]{6}", str))
        return ds_file_list

    def parse_logs(self):
        """
        Parse all dockserver log files for a given glider deployment to extract
        GPS positions and concat them into a string for GE purposes 
        """
        for log in self.ds_logs:
            # Open the dockserver log file to grab the text 
            print(log)
            fh = open(log)
            log_text = fh.read()
            fh.close()

            # Confirm that each log file is for the given glider
            glider_sn = re.findall('Vehicle Name: (......?)', log_text)
            if len(glider_sn) > 0:
                if glider_sn[0][3:] in self.glider:
                    #gps_posits = re.findall('GPS Location:.+? (.+?) m', log_text)
                    gps_posits = re.findall('GPS Location: (.+?) m', log_text)
                    # Exclude invalid positons 
                    gps_posits = [ posit.strip() for posit in gps_posits if "6969" not in posit ]

                    if len(gps_posits) > 0:
                        # Convert lat/lon values to the correct format
                        posit = gps_posits[0]
                        lat = self.convert_lat(posit)
                        lon = self.convert_lon(posit)
                        # Append lat/lon values formatted for GE
                        ge_string = ""+str(lon)+","+str(lat)+",0"
                        self.ge_strings.append(ge_string)
                else:
                    continue
            else:
                continue
        
        # Join all GE formatted lat/lon strings 
        self.ge_string = ",".join(self.ge_strings)

    def convert_lat(self, location):
        """
        Converts a latitude value parsed from a dockserver log file to
        decimal degree format for GE plot
        """
        lat = float(list(filter(lambda x: len(x) > 0, location.split(" ")))[0])
        degrees = trunc(float(lat)/100)
        decimal_minutes = abs(round(lat-degrees*100,3)/60)
        converted_lat = round(abs(degrees)+decimal_minutes,3)

        if lat <0:
            converted_lat = converted_lat * -1

        return(converted_lat)

    def convert_lon(self, location):
        """
        Converts a longitude value parsed from a dockserver log file to
        decimal degree format for GE plot
        """
        lon = float(list(filter(lambda x: len(x) > 0, location.split(" ")))[2])
        degrees = trunc(float(lon)/100)
        decimal_minutes = abs(round(lon-degrees*100,3)/60)
        converted_lon = round(abs(degrees)+decimal_minutes,3)

        if lon <0:
            converted_lon = converted_lon * -1

        return(converted_lon)


def parse_config(config_file):
    """
    Parses the config file containing all glider deployments 
    that are to be included in GE tool archive
    """
    config = configparser.ConfigParser(inline_comment_prefixes=('#',))
    config.optionxform = str  # make keys case sensitive
    config.read(config_file)

    # Create a dictionary to stash all glider deployments 
    config_dict = {}
    for section in config.sections():
        temp_list = []
        for item in config.items(section):
            temp_list.append(item[1])
        config_dict[section] = temp_list
    
    return(config_dict)


class KML: 
    def __init__(self):
        self.kml_pieces = {}
        self.full_kml = ''


        self.base_template = '<?xml version="1.0" ?>'\
        '<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">'\
        '<Document>{}</Document>'\
        '</kml>'

        self.folder_template = '<Folder>'\
        '<name>{}</name>'\
        '{}'\
        '</Folder>'

        self.glider_template = '<Placemark>'\
        '<name>{}</name>'\
        '{}'\
        '<styleUrl>gtrail</styleUrl>'\
        '<LineString>'\
        '<altitudeMode>absolute</altitudeMode>'\
        '<coordinates>{}</coordinates>'\
        '</LineString>'\
        '</Placemark>'

        self.lookat_template = '<LookAt>'\
        '<latitude>{}</latitude>'\
        '<longitude>{}</longitude>'\
        '<range>230000</range>'\
        '<altitude>0</altitude>'\
        '<altitudeMode>absolute</altitudeMode>'\
        '<heading>0</heading>'\
        '<tilt>0</tilt>'\
        '</LookAt>'

    
    def add_glider(self, cruise_name, glider, positions):
        all_posits = positions.split(',')
        if len(all_posits) > 1:
            lookat = all_posits[(len(all_posits)-3):(len(all_posits)-1)]
            lookat_lat = lookat[1]
            lookat_lon = lookat[0]
            lookat_kml = self.lookat_template.format(lookat_lat, lookat_lon)

            temp_lookat = self.lookat_template.format(lookat_lat, lookat_lon)
            temp_glider = self.glider_template.format(glider, temp_lookat, positions)

            if cruise_name in self.kml_pieces:
                self.kml_pieces[cruise_name].append(temp_glider)
            else:
                self.kml_pieces[cruise_name] = []
                self.kml_pieces[cruise_name].append(temp_glider)
    
    def concat_kml(self):
        all_folders = []
        for cruise in self.kml_pieces:
            temp_folder = self.folder_template.format(cruise, ''.join(self.kml_pieces[cruise]))
            all_folders.append(temp_folder)
        self.full_kml = self.base_template.format(''.join(all_folders))


    def pretty_print(self):
        temp = xml.dom.minidom.parseString(self.full_kml)
        new_xml = temp.toprettyxml()
        print(new_xml)
    
    def write_kml(self):
        temp = xml.dom.minidom.parseString(self.full_kml)
        new_xml = temp.toprettyxml()
        with open("Archive.kml", "w") as f:
            f.write(new_xml)


def main():
    # Load in the config file and parse deployments to be archived
    config_dict = parse_config(config_file)

    archive_KML = KML()
    # Iterate through the deployments and build archive KML
    for i in config_dict:
        print(i)
        archives = [Archive(j.split("/")[0], j.split("/")[1][-1], i) for j in config_dict[i]]
        
        for glider_archive in archives:
            #glider_archive.ge_string = '-70.000,49.000,0'
            archive_KML.add_glider(glider_archive.cruise, glider_archive.glider, glider_archive.ge_string)
    archive_KML.concat_kml()
    archive_KML.write_kml()

if __name__ == "__main__":
    main()