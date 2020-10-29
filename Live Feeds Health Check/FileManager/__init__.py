""" Utility methods for working with files and directories """
import json
import os
import pathlib
import stat
import xml.etree.ElementTree as Et

VERSION = "1.0.0"


def check_file_exist_by_os_path(path: str = ""):
    """ Check if the path exist """
    # If this file object exist.
    if os.path.exists(path):
        ret = True
        print(f"{path} exist.")
        # If this is a file.
        if os.path.isfile(path):
            print(" and it is a file.")
        # This is a directory.    
        else:
            print(" and it is a directory.")
    else:
        ret = False
        print(f"{path} do not exist.")

    return ret


def check_file_exist_by_pathlib(path: str = ""):
    """ """
    # Create path lib object.
    pl = pathlib.Path(path)
    # Check whether the path lib exist or not.
    ret = pl.exists()
    if ret:
        print(f"{path} exist.")
    else:
        print(f"{path} do not exist.")

    if pl.is_file():
        print(f"{path} is a file.")

    if pl.is_dir():
        print(f"{path} is a directory.")
    return ret


def create_new_file(file_path):
    """ Create a new file and write some text in it. """
    file_object = open(file_path, "w")
    print(f"{file_path} has been created.")


def create_new_folder(file_path):
    """ Create a new directory. """
    if not check_file_exist_by_os_path(file_path):
        os.mkdir(file_path)
        print(f"{file_path} has been created.")


def set_file_permission(file_path):
    """ Change the file permission to read and execute only. """
    os.chmod(file_path, stat.S_IEXEC | stat.S_IWRITE)


def save(data=None, path: str = "") -> None:
    if data is None:
        data = {}
    with open(path, "w") as outfile:
        json.dump(data, outfile)


def load_status_config_data(path: str = "") -> dict:
    with open(path) as json_file:
        data = json.load(json_file)
    return data


def get_response_time_data(path: str = "") -> dict:
    with open(path) as json_file:
        data = json.load(json_file)
    return data


def update_response_time_data(path: str = "", input_data=None):
    if input_data is None:
        input_data = {}
    with open(path, "w") as out_file:
        json.dump(input_data, out_file)


def get_status_from_feed(filename):
    """ Retrieve the status of the service """
    xml_doc = Et.parse(filename)
    element = xml_doc.find(".//channel/item/description")
    return element.text
