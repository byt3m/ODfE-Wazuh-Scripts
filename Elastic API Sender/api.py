import requests, json


class API(object):

    def __init__(self):
        self.validEndpoint = None
        self.endpoints = None
        self.cluster_name = None
        self.cluster_status = None
        self.session = requests.Session()

    def get(self, url):
        req = self.session.get(url)
        return req

    def post(self, url, payload):
        headers = {"Content-type": "application/json; charset=utf-8"}
        req = self.session.post(url, json=payload, headers=headers)
        return req

    def put(self, url, payload):
        headers = {"Content-type": "application/json; charset=utf-8"}
        req = self.session.put(url, json=payload, headers=headers)
        return req

    # Get from the endpoints list a valid endpoint
    def getValidEndpoint(self):
        print("Looking for a valid endpoint from the provided endpoints list")
        for endpoint in self.endpoints:
            result = self.get(endpoint + "_cluster/health")
            if result.status_code == 200:
                self.validEndpoint = endpoint
                print("Valid endpoint found at %s" % self.validEndpoint)
                return True
        print("ERROR: No valid endpoint found!")
        return False

    def checkClusterHealth(self):
        print("Checking cluster status...")
        result = self.get(self.validEndpoint + "_cluster/health")
        if result.status_code == 200:
            content = result.json()
            self.cluster_name = content["cluster_name"]
            self.cluster_status = content["status"]
            if self.cluster_status == "red":
                print("WARNING: Cluster status is red!")
                return False
            elif self.cluster_status == "yellow":
                print("Cluster status is yellow")
                return True
            elif self.cluster_status == "green":
                print("Cluster status is green")
                return True
            else:
                print("Cluster status is unknown, received status: %s" % self.cluster_status)
        else:
            print("Received HTTP status code %s." % result.status_code)
            return False

    def createMonitor(self, payload):
        print("Creating monitor...")
        result = self.post(self.validEndpoint + "_opendistro/_alerting/monitors", payload)
        content = result.json()
        if result.status_code == 201:
            print("Succesfull: monitor ID = %s" % content["_id"])
        else:
            print("ERROR: Received HTTP status code %s:" % result.status_code)
            print("  - Error type: %s" % content["error"]["root_cause"][0]["type"])
            print("  - Error reason: %s" % content["error"]["root_cause"][0]["reason"])

    def putIndexSettings(self, index, payload):
        print("Applying payload on index %s" % index)
        result = self.put(self.validEndpoint + index + "/_settings?pretty", payload)
        content = result.json()
        if result.status_code == 200:
            print("Successfully applied settings, response: %s" % content)
        else:
            print("ERROR: Received HTTP status code %s, error: %s" % (result.status_code, content["error"]))

    def search(self, index, payload):
        print("Searching on index %s with requested payload" % index)
        result = self.post(self.validEndpoint + index + "/_search", payload)
        content = result.json()
        if result.status_code == 200:
            result = result.json()
            print("Search performed successfully, found %s hits" % str(result["hits"]["total"]["value"]))
            return result
        else:
            print("ERROR: Received HTTP status code %s:" % result.status_code)
            print("  - Error type: %s" % content["error"]["root_cause"][0]["type"])
            print("  - Error reason: %s" % content["error"]["root_cause"][0]["reason"])

