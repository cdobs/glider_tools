import os
import re
import glob
import configparser
import xml.dom.minidom

raw_data_dir = '/Volumes/data/'
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
            glider_sn = re.findall('Vehicle Name: (......?)', log_text)[0][3:]
            if glider_sn in self.glider:
                gps_posits = re.findall('GPS Location:.+? (.+?) m', log_text)
                # Exclude invalid positons 
                for posit in gps_posits:
                    if "696969" in posit:
                        gps_posits.remove(posit)

                if len(gps_posits) > 0:
                    # Convert lat/lon values to the correct format
                    posit = gps_posits[0]
                    lat = self.convert_lat(posit)
                    lon = self.convert_lon(posit)
                    # Append lat/lon values formatted for GE
                    ge_string = "-"+str(lon)+","+str(lat)+",0"
                    self.ge_strings.append(ge_string)
                else:
                    continue
        
        # Join all GE formatted lat/lon strings 
        self.ge_string = ",".join(self.ge_strings)

    def convert_lat(self, location):
        """
        Converts a latitude value parsed from a dockserver log file to
        decimal degree format for GE plot
        """
        lat = location.split(" ")[0]
        converted_lat = round((float(lat[0:2]) + float(lat[2:])/60), 4)
        return(converted_lat)

    def convert_lon(self, location):
        """
        Converts a longitude value parsed from a dockserver log file to
        decimal degree format for GE plot
        """
        lon = location.split(" ")[2]
        converted_lon = round((float(lon[1:3]) + float(lon[3:])/60), 4)
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
        self.kml_base = '<?xml version="1.0" ?><kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2"><Document>INSERT_HERE</Document></kml>'
        self.kml_string = self.kml_base
    
    def add_glider(self, cruise_name, glider, positions):
        if cruise_name in self.kml_string:
            index_start = self.kml_string.find(cruise_name)+len(cruise_name)+len("</name>")
            index_end = self.kml_string.find(cruise_name)+len(cruise_name)+len("</name>")
            new_kml_string = self.kml_string[:index_start]+'<Placemark><name>'+glider+'</name><styleUrl>gtrail</styleUrl><LineString><altitudeMode>absolute</altitudeMode><coordinates>'+positions+'</coordinates></LineString></Placemark>'+self.kml_string[index_end:]
            self.kml_string = new_kml_string
        else:
            if "INSERT_HERE" in self.kml_string:
                index_start = self.kml_string.find("INSERT_HERE")
                index_end = index_start+11
            else:
                index_start = self.kml_string.rfind("</Folder>")+9
                index_end = self.kml_string.rfind("</Folder>")+9

            new_kml_string = self.kml_string[:index_start]+'<Folder><name>'+cruise_name+'</name><Placemark><name>'+glider+'</name><styleUrl>gtrail</styleUrl><LineString><altitudeMode>absolute</altitudeMode><coordinates>'+positions+'</coordinates></LineString></Placemark></Folder>'+self.kml_string[index_end:]
            self.kml_string = new_kml_string

    def pretty_print(self):
        temp = xml.dom.minidom.parseString(self.kml_string)
        new_xml = temp.toprettyxml()
        print(new_xml)
    
    def write_kml(self):
        temp = xml.dom.minidom.parseString(self.kml_string)
        new_xml = temp.toprettyxml()
        with open("Archive.kml", "w") as f:
            f.write(new_xml)


def main():
    # Load in the config file and parse deployments to be archived
    config_dict = parse_config(config_file)

    archive_KML = KML()
    # Iterate through the deployments and build archive KML
    for i in config_dict:
        archives = [Archive(j.split("/")[0], j.split("/")[1][-1], i) for j in config_dict[i]]
        for glider_archive in archives:
            #glider_archive.ge_string = '-70.000,49.000,0'
            archive_KML.add_glider(glider_archive.cruise, glider_archive.glider, glider_archive.ge_string)
    archive_KML.write_kml()



