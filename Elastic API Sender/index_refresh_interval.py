__version__ = '2021.08.27.01'

import sys
import traceback
import argparse
from api import *
from getpass import getpass
from datetime import date


def main():
    # Get and check arguments
    parser = argparse.ArgumentParser(description="Apply refresh_interval setting to today's beats indexes.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-v', '--version', action='version', version=__version__)
    parser.add_argument('-u', '--username', action='store', help='Username to access ElasticSearch API', required=True)
    parser.add_argument('-p', '--password', action='store', help='Password to access ElasticSearch API', required=True)
    parser.add_argument('-b', '--beats-version', action='store', help='Version of the beats agents', required=True)
    args = parser.parse_args()

    # Initialize API class object
    api = API()

    # Elasticsearch endpoint URL
    api.endpoints = [""]

    # Session settings
    api.session.verify = ""  # CA certificate for the TLS communication
    userpassword = getpass(prompt=("User '" + args.username + "' password: "))
    api.session.auth = (args.username, userpassword)

    # "Init" methods
    if not api.getValidEndpoint() or not api.checkClusterHealth():
        sys.exit(1)

    # Indexes names
    today = date.today()
    filebeatIndex = "filebeat-" + args.beats_version + "-" + today.strftime("%Y.%m.%d")
    metricbeatIndex = "metricbeat-" + args.beats_version + "-" + today.strftime("%Y.%m.%d")
    heartbeatIndex = "heartbeat-" + args.beats_version + "-" + today.strftime("%Y.%m.%d")
    wazuhmonitoringIndex = "wazuh-monitoring-" + today.strftime("%Y.%m.%d")
    wazuhalertsIndex = "wazuh-alerts-4.x-" + today.strftime("%Y.%m.%d")

    # Config to apply to beats index
    config = {
        "index":
            {
                "refresh_interval": "60s"
            }
    }

    # Apply config
    api.putIndexSettings(filebeatIndex, config)
    api.putIndexSettings(metricbeatIndex, config)
    api.putIndexSettings(heartbeatIndex, config)
    api.putIndexSettings(wazuhmonitoringIndex, config)
    api.putIndexSettings(wazuhalertsIndex, config)


# Call main/start program and catch exceptions
try:
    main()
except SystemExit:
    pass
except:
    print("Exception occurred:")
    print(traceback.format_exc())
    sys.exit(1)
