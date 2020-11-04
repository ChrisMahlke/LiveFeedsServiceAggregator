""" Utility methods for working with files and directories """
import json
import os
import pathlib
import stat
import xml.etree.ElementTree as Et
import TimeUtils as TimeUtils


def check_file_exist_by_os_path(path: str = ""):
    """ Check if the path exist """
    # If this file object exist.
    if os.path.exists(path):
        ret = True
    else:
        ret = False
    return ret


def check_file_exist_by_pathlib(path: str = ""):
    """ Check if the file exists """
    # Create path lib object.
    pl = pathlib.Path(path)
    # Check whether the path lib exist or not.
    ret = pl.exists()
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


def open_file(path: str = "") -> dict:
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
    children = element.findall("h2")
    for child in children:
        if child.attrib["attr"] == "status-details":
            return child.text


def dict_to_xml(template=None, input_dict=None, output_file_path=None):
    admin_comments = ""
    sorted_comments = sorted(input_dict["comments"], key=lambda k: k["timestamp"], reverse=True)
    for sorted_comment in sorted_comments:
        comment = sorted_comment["comment"]
        comment_timestamp = TimeUtils.convert_from_utc_to_datetime(sorted_comment["timestamp"]).strftime(
            "%a, %d %b %Y %H:%M:%S")
        admin_comments += f"<li>Posted: {comment_timestamp}<ul><li>{comment}</li></ul></li>"
    input_dict.update({
        "adminComments": admin_comments
    })
    with open(template, "r") as file:
        data = file.read().replace("\n", "")
        output_file_contents = data.format_map(input_dict)

    with open(output_file_path, "w+") as file:
        file.write(output_file_contents)
