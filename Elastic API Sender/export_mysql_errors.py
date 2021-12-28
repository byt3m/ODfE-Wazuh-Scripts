__version__ = '2021.10.05'

import csv
import sys
import traceback
import argparse
from datetime import date
from datetime import timedelta
from datetime import datetime
from getpass import getpass
from api import *

csvHeader = ["Timestamp","Hostname","Log level","Message"]
today = date.today()
dateTo = "now"
dateFrom = (today - timedelta(days = 2)).strftime("%Y-%m-%d") + "T22:00:00.000Z"
searchRequest = {"size":10000,"sort":[{"@timestamp":{"order":"desc","unmapped_type":"boolean"}}],"aggs":{"2":{"date_histogram":{"field":"@timestamp","fixed_interval":"30m","time_zone":"Europe/Madrid","min_doc_count":1}}},"query":{"bool":{"must":[],"filter":[{"bool":{"should":[{"query_string":{"fields":["agent.hostname"],"query":"SRVPN\\-LBBDD\\-*"}}],"minimum_should_match":1}},{"match_phrase":{"event.module":"mysql"}},{"match_phrase":{"event.dataset":"mysql.error"}},{"range":{"@timestamp":{"gte":dateFrom,"lte":dateTo}}}],"should":[],"must_not":[]}}}

def convertElasticTimestamp(timestamp):
    result = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
    result = result + timedelta(hours=2)
    return result.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

def main():
    # Get and check arguments
    parser = argparse.ArgumentParser(description="Export a search to csv.",formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-v', '--version', action='version', version=__version__)
    parser.add_argument('-u', '--username', action='store', help='Username to access ElasticSearch API', required=True)
    #parser.add_argument('-p', '--password', action='store', help='Password to access ElasticSearch API', required=True)
    parser.add_argument('-o', '--csv-file', action='store', help='Path to the CSV file to save results', required=True)
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

    # Perform search
    result = api.search("filebeat-*", searchRequest)

    # Save results to CSV
    print("Exporting results to csv file %s" % args.csv_file)
    hits = result["hits"]["hits"]
    hitsData = {"hits": []}

    for hit in hits:
        hitsData["hits"].append({
            "Timestamp": convertElasticTimestamp(hit["_source"]["@timestamp"]),
            "Hostname": hit["_source"]["agent"]["hostname"],
            "Log level": hit["_source"]["log"]["level"],
            "Message": hit["_source"]["message"]
        })

    dataFile = open(args.csv_file, "w", newline='')
    csvWriter = csv.DictWriter(dataFile, delimiter=";", fieldnames=csvHeader)
    csvWriter.writeheader()
    csvWriter.writerows(hitsData["hits"])
    dataFile.close()


# Call main/start program and catch exceptions
try:
    main()
except SystemExit:
    pass
except:
    print("Exception occurred:")
    print(traceback.format_exc())
    sys.exit(1)

