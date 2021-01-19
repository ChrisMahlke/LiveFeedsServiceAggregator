""" Utility methods for working with files and directories """
import html
import json
import os
import pathlib
import stat
import xml.etree.ElementTree as Et
import TimeUtils as TimeUtils


def check_file_exist_by_os_path(path: str = ""):
    """
    Check if the path exist

    :param path:
    :return:
    """
    # If this file object exist.
    if os.path.exists(path):
        ret = True
    else:
        ret = False
    return ret


def check_file_exist_by_pathlib(path: str = ""):
    """
    Check if the file exists

    :param path: Path to file
    :return: Boolean indicating if the file exist
    """
    # Create path lib object.
    pl = pathlib.Path(path)
    # Check whether the path lib exist or not.
    ret = pl.exists()
    return ret


def create_new_file(file_path):
    """
    Create a new file and write some text in it.

    :param file_path:
    :return:
    """
    file_object = open(file_path, "w")
    print(f"{file_path} has been created.")


def create_new_folder(file_path):
    """
    Create a new directory.
    :param file_path:
    :return:
    """
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
    """
    Open the file and return the data
    :param path: Path to the file
    :return: Return the content of the file
    """
    with open(path) as json_file:
        data = json.load(json_file)
    return data


def get_response_time_data(path: str = "") -> dict:
    """
    :param path:
    :return:
    """
    with open(path) as json_file:
        data = json.load(json_file)
    return data


def update_response_time_data(path: str = "", input_data=None):
    """
    :param path:
    :param input_data:
    :return:
    """
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


def dict_to_xml(template=None, rss_item_template=None, input_dict=None, output_file_path=None):
    """
    Hydrate an input XML template with an input dictionary and save to disk
    :param template: An XML template
    :param rss_item_template: The XML template for a single item node
    :param input_dict: Input dictionary of data
    :param output_file_path: Output file path
    :return: None
    """
    # The RSS comments header (this is set in the config ini file)
    admin_comments_header = "<h4>" + input_dict["rss_comments_header"] + "</h4>"
    # store the admin comments
    admin_comments = ""
    # comments section
    comments_section = ""
    # sort the comments in reverse order by time
    sorted_comments = sorted(input_dict["comments"], key=lambda k: k["timestamp"], reverse=True)
    # If there are comments, build the section that will be included in the rss output
    if len(sorted_comments) > 0:
        for sorted_comment in sorted_comments:
            comment = sorted_comment["comment"]
            comment_timestamp = TimeUtils.convert_from_utc_to_datetime(sorted_comment["timestamp"]).strftime(
                "%a, %d %b %Y %H:%M:%S")
            admin_comments += "<li>" + f"Posted: {comment_timestamp} | <b>{comment}</b>" + "</li>"
        comments_section = admin_comments_header + admin_comments

    # Hydrate the data model to include the comments
    input_dict.update({
        "adminComments": html.escape(comments_section)
    })

    # TODO
    # [*]   Create item.xml template
    # [*]   Remove item node from rss template
    # [*]   Add placeholder in rss template for items to be added
    #
    # [ ]   Two config parameters
    #       [ ] 1) date range
    #       [ ] 2) ceiling
    #
    # If ...

    # Open the RSS item template.
    # Create the item nodes that will ultimately hydrate the main rss template
    with open(rss_item_template, "r") as file:
        data = file.read().replace("\n", "")
        item_template = data.format_map(input_dict)

    # Update the dictionary
    # rss_items is the placeholder in the main rss_template file
    input_dict.update({
        "rss_items": item_template
    })

    # Open the RSS main template
    with open(template, "r") as file:
        data = file.read().replace("\n", "")
        output_file_contents = data.format_map(input_dict)

    # Over-write to an existing or new file
    with open(output_file_path, "w+") as file:
        file.write(output_file_contents)

