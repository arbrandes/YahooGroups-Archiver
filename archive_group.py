'''
Yahoo-Groups-Archiver Copyright 2015, 2017, 2018 Andrew Ferguson and others

YahooGroups-Archiver, a simple python script that allows for all
messages in a public Yahoo Group to be archived.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import json  # required for reading various JSON attributes from the content
import requests  # required for fetching the raw messages
import os  # required for checking if a file exists locally
import time  # required to log the date and time of run
import sys  # required to cancel script if blocked by Yahoo
import shutil  # required for deletung an old folder
import glob  # required to find the most recent message downloaded


cookie_T = ""
cookie_Y = ""


def archive_group(groupName, mode="update"):
    log("\nArchiving group '" + groupName + "', mode: " + mode + " , on " + time.strftime("%c"), groupName)
    startTime = time.time()
    msgsArchived = 0
    if mode == "retry":
        # don't archive any messages we already have
        # but try to archive ones that we don't, and may have
        # already attempted to archive
        min = 1
    elif mode == "update":
        # start archiving at the last+1 message message we archived
        mostRecent = 1
        if os.path.exists(groupName):
            oldDir = os.getcwd()
            os.chdir(groupName)
            # Match *.json and *.fail
            for file in glob.glob("*.[jf][sa][oi][nl]"):
                if int(file[0:-5]) > mostRecent:
                    mostRecent = int(file[0:-5])
            os.chdir(oldDir)

        min = mostRecent
    elif mode == "restart":
        # delete all previous archival attempts and archive everything again
        if os.path.exists(groupName):
            shutil.rmtree(groupName)
        min = 1

    else:
        print("You have specified an invalid mode (" + mode + ").")
        print("Valid modes are:\nupdate - add any new messages to the archive\nretry - attempt to get all messages that are not in the archive\nrestart - delete archive and start from scratch")
        sys.exit(1)

    if not os.path.exists(groupName):
        os.makedirs(groupName)
    max = group_messages_max(groupName)
    consecutive_fail_count = 0
    for x in range(min, max+1):
        basename = groupName + '/' + str(x)
        filename = basename + ".json"
        if not os.path.isfile(filename):
            print("Archiving message " + str(x) + " of " + str(max))
            status_code = archive_message(groupName, x)
            if status_code == 200:
                consecutive_fail_count = 0
                msgsArchived = msgsArchived + 1
            else:
                print("Cannot get message " + str(x) + " due to HTTP status code " + str(status_code))
                consecutive_fail_count = consecutive_fail_count + 1
                if (consecutive_fail_count >= 10):
                    print("Exiting due to too many consecutive failures.")
                    sys.exit(1)
                time.sleep(1)
        elif mode == "retry":
            # Reset fail count when retrying
            consecutive_fail_count = 0

    log("Archive finished, archived " + str(msgsArchived) + ", time taken is " + str(time.time() - startTime) + " seconds", groupName)


def group_messages_max(groupName):
    s = requests.Session()
    resp = s.get('https://groups.yahoo.com/api/v1/groups/' + groupName + '/messages?count=1&sortOrder=desc&direction=-1', cookies={'T': cookie_T, 'Y': cookie_Y})
    try:
        pageHTML = resp.text
        pageJson = json.loads(pageHTML)
    except ValueError:
        if "Stay signed in" in pageHTML and "Trouble signing in" in pageHTML:
            # the user needs to be signed in to Yahoo
            print("Error. The group you are trying to archive is a private group. To archive a private group using this tool, login to a Yahoo account that has access to the private groups, then extract the data from the cookies Y and T from the domain yahoo.com . Paste this data into the appropriate variables (cookie_Y and cookie_T) at the top of this script, and run the script again.")
            sys.exit()
    return pageJson["ygData"]["totalRecords"]


def archive_message(groupName, msgNumber):
    url = 'https://groups.yahoo.com/api/v1/groups/' + groupName + '/messages/' + str(msgNumber) + '/raw'
    cookies = {'T': cookie_T, 'Y': cookie_Y}
    s = requests.Session()
    try:
        resp = s.get(url, cookies=cookies, timeout=30)
    except Exception as e:
        return 500
    basename = groupName + "/" + str(msgNumber)
    if resp.status_code == 200:
        msgJson = resp.text
        filename = basename + ".json"
        with open(filename, "wb") as f:
            f.write(msgJson.encode('utf-8'))
    else:
        filename = basename + ".fail"
        open(filename, "wa").close()

    return resp.status_code


def log(msg, groupName):
    print(msg)
    if writeLogFile:
        logF = open(groupName + ".txt", "a")
        logF.write("\n" + msg)
        logF.close()


if __name__ == "__main__":
    global writeLogFile
    writeLogFile = True
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if "nologs" in sys.argv:
        print("Logging mode OFF")
        writeLogFile = False
        sys.argv.remove("nologs")
    if len(sys.argv) > 2:
        archive_group(sys.argv[1], sys.argv[2])
    else:
        archive_group(sys.argv[1])
