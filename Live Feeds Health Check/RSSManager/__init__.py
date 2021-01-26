""" Utility methods for working with RSS """
import html
import os
import FileManager as FileManager
import TimeUtils as TimeUtils
from datetime import datetime, timedelta


class RSS:
    """

    """

    def __init__(self, rss_template, item_template):
        """

        :param rss_template:
        :param item_template:
        """
        self.rss_template = os.path.realpath(rss_template)
        self.item_template = os.path.realpath(item_template)

    def build_item_nodes(self, input_data=None, events_file=None):
        """

        :param input_data:
        :param events_file:
        :return:
        """
        # JSON from events file
        status_history_json = FileManager.open_file(path=events_file)
        # history element
        history = status_history_json["history"]
        # comments
        comments = ""
        #
        items = []
        # build RSS file
        for event in history:
            # store the admin comments
            admin_comments = ""
            # comments section
            comments_section = ""
            # sort the comments in the comments section in reverse order by time
            sorted_comments = sorted(event["comments"], key=lambda k: k["timestamp"], reverse=True)
            # If there are comments, build the section that will be included in the rss output
            if len(sorted_comments) > 0:
                for sorted_comment in sorted_comments:
                    comment = sorted_comment["comment"]
                    comment_timestamp = TimeUtils.convert_from_utc_to_datetime(
                        sorted_comment["timestamp"]).strftime("%a, %d %b %Y %H:%M:%S")
                    admin_comments += "<li>" + f"Posted: {comment_timestamp} | <b>{comment}</b>" + "</li>"
                comments_section = "<h4>" + input_data["rss_comments_header"] + "</h4>" + admin_comments
            comments = comments + comments_section

            # Hydrate the data model to include the comments
            input_data.update({
                "adminComments": html.escape(comments_section),
                "timestamp": event["timestamp"],
                "lastBuildTime": event["lastBuildTime"],
                "lastRunTimestamp": event["lastRunTimestamp"],
                "lastUpdateTime": event["lastUpdateTime"],
                "status": event["status"]
            })

            # Open the RSS item template.
            # Create the item nodes that will ultimately hydrate the main rss template
            with open(self.item_template, "r") as file:
                data = file.read().replace("\n", "")
                items.append(data.format_map(input_data))
        return "".join(items)

    def update_rss_contents(self, input_data=None, rss_file=None):
        """

        :param input_data:
        :param rss_file:
        :return:
        """
        # Open the RSS main template
        with open(self.rss_template, "r") as file:
            data = file.read().replace("\n", "")
            output_file_contents = data.format_map(input_data)

        # Over-write to an existing or new file
        with open(rss_file, "w+") as file:
            file.write(output_file_contents)
