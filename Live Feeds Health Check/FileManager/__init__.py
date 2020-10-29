""" Utility methods for working with files and directories """

VERSION = "1.0.0"

import configparser
import os, stat
import pathlib
import json
import xml.etree.ElementTree as et

def checkFileExistByOSPath(path: str = ""):
    """ Check if the path exist """
    ret = False
    # If this file object exist.
    if(os.path.exists(path)):
        ret = True
        print(f"{path} exist.")
        # If this is a file.
        if(os.path.isfile(path)):
            print(" and it is a file.")
        # This is a directory.    
        else:
            print(" and it is a directory.")
    else:
        ret = False
        print(f"{path} do not exist.")
        
    return ret

def checkFileExistByPathlib(path: str = ""):
    """ """
    ret = True
    # Create path lib object.
    pl = pathlib.Path(path)
    # Check whether the path lib exist or not.
    ret = pl.exists()
    if(ret):
        print(f"{path} exist.")
    else:
        print(f"{path} do not exist.")
    
    if(pl.is_file()):
        print(f"{path} is a file.")
       
    if(pl.is_dir()):
        print(f"{path} is a directory.")

    return ret

def createNewFile(file_path):
    """ Create a new file and write some text in it. """
    file_object = open(file_path, "w")
    print(f"{file_path} has been created.")
    
def createNewFolder(file_path):
    """ Create a new directory. """
    if(not checkFileExistByOSPath(file_path)):
        os.mkdir(file_path)
        print(f"{file_path} has been created.")

def setFilePermission(file_path):
    """ Change the file permission to read and execute only. """
    os.chmod(file_path, stat.S_IEXEC | stat.S_IWRITE) 

def save(data: dict = {}, path: str = "") -> None:
    with open(path, "w") as outfile:
        json.dump(data, outfile)

def loadStatusConfigData(path: str = "") -> dict:
    with open(path) as json_file:
        data = json.load(json_file)
    return data

def getResponseTimeData(path: str = "") -> dict:
    with open(path) as json_file:
        data = json.load(json_file)
    return data

def updateResponseTimeData(path: str = "", inputData: dict = {}) -> dict:
    with open(path, "w") as out_file:
        json.dump(inputData, out_file)

def getStatusFromFeed(filename):
    """ Retrieve the status of the service """
    xmldoc = et.parse(filename)
    element = xmldoc.find(".//channel/item/description")
    return element.text