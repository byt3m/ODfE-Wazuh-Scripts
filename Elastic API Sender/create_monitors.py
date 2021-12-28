__version__ = '2021.08.27.01'

import csv
import sys
import os
import traceback
import argparse
from getpass import getpass
from api import *

# Alerts destination ids
notification_destination_id1 = ""
notification_destination_id2 = ""

# Monitors settings
storage_percentage = "80"
storage_critical_percentage = "90"
storage_monitor_time = 30
storage_monitor_time_units = "MINUTES"
ram_percentage = "90"
ram_monitor_time = 10
ram_monitor_units = "MINUTES"
cpu_percentage = "90"
cpu_monitor_time = 10
cpu_monitor_units = "MINUTES"


def main():
    # Get and check arguments
    parser = argparse.ArgumentParser(description="Create RAM, storage and CPU monitors.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-v', '--version', action='version', version=__version__)
    parser.add_argument('-u', '--username', action='store', help='Username to access ElasticSearch API', required=True)
    #parser.add_argument('-p', '--password', action='store', help='Password to access ElasticSearch API', required=True)
    parser.add_argument('-f', '--csv-file', action='store', help='File to save agent hostnames of existing monitors', required=True)
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

    # Check csv hostnames file exists
    if not os.path.exists(args.csv_file) or not os.path.isfile(args.csv_file):
        print("ERROR: File '%s' does not exist!" % args.csv_file)
        sys.exit(1)

    # Read CSV and create monitors
    print("Creating monitors")
    with open(args.csv_file, 'r', encoding="utf-8-sig") as file:
        reader = csv.reader(file)
        for row in reader:
            hostname = row[0].strip()
            # Storage usage monitors
            print("Creating storage usage monitor for hostname %s" % hostname)
            storageMonitorConfig = {
                "type": "monitor",
                "name": "[" + hostname.upper() + "] Storage usage",
                "enabled": True,
                "schedule": {
                    "period": {
                        "interval": storage_monitor_time,
                        "unit": "" + storage_monitor_time_units.upper() + ""
                    }
                },
                "inputs": [
                    {
                        "search": {
                            "indices": [
                                "metricbeat-*"
                            ],
                            "query": {
                                "size": 0,
                                "query": {
                                    "bool": {
                                        "filter": [
                                            {
                                                "range": {
                                                    "@timestamp": {
                                                        "from": "{{period_end}}||-" + str(
                                                            storage_monitor_time) + "m",
                                                        "to": "{{period_end}}",
                                                        "include_lower": True,
                                                        "include_upper": True,
                                                        "format": "epoch_millis",
                                                        "boost": 1.0
                                                    }
                                                }
                                            },
                                            {
                                                "term": {
                                                    "host.name": {
                                                        "value": "" + hostname.lower() + "",
                                                        "boost": 1.0
                                                    }
                                                }
                                            }
                                        ],
                                        "adjust_pure_negative": True,
                                        "boost": 1.0
                                    }
                                },
                                "aggregations": {
                                    "used": {
                                        "max": {
                                            "field": "system.fsstat.total_size.used"
                                        }
                                    },
                                    "free": {
                                        "max": {
                                            "field": "system.fsstat.total_size.free"
                                        }
                                    },
                                    "total": {
                                        "max": {
                                            "field": "system.fsstat.total_size.total"
                                        }
                                    }
                                }
                            }
                        }
                    }
                ],
                "triggers": [
                    {
                        "name": "Storage_" + storage_critical_percentage + "%",
                        "severity": "5",
                        "condition": {
                            "script": {
                                "source": "return ctx.results[0].aggregations.total.value == null || ctx.results[0].aggregations.used.value == null ? false :((ctx.results[0].aggregations.used.value*100)/ctx.results[0].aggregations.total.value) > " + storage_critical_percentage + "",
                                "lang": "painless"
                            }
                        },
                        "actions": [
                            {
                                "name": "EnvioAlertaITS",
                                "destination_id": "" + notification_destination_id1 + "",
                                "message_template": {
                                    "source": """
    Monitor "{{ctx.monitor.name}}" just entered alert status. Please investigate the issue.
        - Trigger: {{ctx.trigger.name}}
        - Severity: {{ctx.trigger.severity}}
        - Period start: {{ctx.periodStart}}
        - Period end: {{ctx.periodEnd}}

    Storage reached the """ + storage_critical_percentage + """% threshold:
        - Total storage (bytes): {{ctx.results.0.aggregations.total.value}}
        - Used storage (bytes): {{ctx.results.0.aggregations.used.value}}
        - Free storage (bytes): {{ctx.results.0.aggregations.free.value}}
                                """,
                                    "lang": "mustache"
                                },
                                "throttle_enabled": False,
                                "subject_template": {
                                    "source": "[ELK Alerts] " + hostname.upper() + " - Almacenamiento superior al " + storage_critical_percentage + "%",
                                    "lang": "mustache"
                                }
                            },
                            {
                                "name": "EnvioAlertaSupportCPD",
                                "destination_id": "" + notification_destination_id2 + "",
                                "message_template": {
                                    "source": """
    Monitor "{{ctx.monitor.name}}" just entered alert status. Please investigate the issue.
        - Trigger: {{ctx.trigger.name}}
        - Severity: {{ctx.trigger.severity}}
        - Period start: {{ctx.periodStart}}
        - Period end: {{ctx.periodEnd}}

    Storage reached the """ + storage_critical_percentage + """% threshold:
        - Total storage (bytes): {{ctx.results.0.aggregations.total.value}}
        - Used storage (bytes): {{ctx.results.0.aggregations.used.value}}
        - Free storage (bytes): {{ctx.results.0.aggregations.free.value}}
                                """,
                                    "lang": "mustache"
                                },
                                "throttle_enabled": False,
                                "subject_template": {
                                    "source": "[ELK Alerts] " + hostname.upper() + " - Almacenamiento superior al " + storage_critical_percentage + "%",
                                    "lang": "mustache"
                                }
                            }
                        ]
                    },
                    {
                        "name": "Storage_" + storage_percentage + "%",
                        "severity": "3",
                        "condition": {
                            "script": {
                                "source": "return ctx.results[0].aggregations.total.value == null || ctx.results[0].aggregations.used.value == null ? false :((ctx.results[0].aggregations.used.value*100)/ctx.results[0].aggregations.total.value) > " + storage_percentage + "",
                                "lang": "painless"
                            }
                        },
                        "actions": [
                            {
                                "name": "EnvioAlertaITS",
                                "destination_id": "" + notification_destination_id1 + "",
                                "message_template": {
                                    "source": """
    Monitor "{{ctx.monitor.name}}" just entered alert status. Please investigate the issue.
        - Trigger: {{ctx.trigger.name}}
        - Severity: {{ctx.trigger.severity}}
        - Period start: {{ctx.periodStart}}
        - Period end: {{ctx.periodEnd}}

    Storage reached the """ + storage_percentage + """% threshold:
        - Total storage (bytes): {{ctx.results.0.aggregations.total.value}}
        - Used storage (bytes): {{ctx.results.0.aggregations.used.value}}
        - Free storage (bytes): {{ctx.results.0.aggregations.free.value}}
                                """,
                                    "lang": "mustache"
                                },
                                "throttle_enabled": False,
                                "subject_template": {
                                    "source": "[ELK Alerts] " + hostname.upper() + " - Almacenamiento superior al " + storage_percentage + "%",
                                    "lang": "mustache"
                                }
                            },
                            {
                                "name": "EnvioAlertaSupportCPD",
                                "destination_id": "" + notification_destination_id2 + "",
                                "message_template": {
                                    "source": """
    Monitor "{{ctx.monitor.name}}" just entered alert status. Please investigate the issue.
        - Trigger: {{ctx.trigger.name}}
        - Severity: {{ctx.trigger.severity}}
        - Period start: {{ctx.periodStart}}
        - Period end: {{ctx.periodEnd}}

    Storage reached the """ + storage_percentage + """% threshold:
        - Total storage (bytes): {{ctx.results.0.aggregations.total.value}}
        - Used storage (bytes): {{ctx.results.0.aggregations.used.value}}
        - Free storage (bytes): {{ctx.results.0.aggregations.free.value}}
                                """,
                                    "lang": "mustache"
                                },
                                "throttle_enabled": False,
                                "subject_template": {
                                    "source": "[ELK Alerts] " + hostname.upper() + " - Almacenamiento superior al " + storage_percentage + "%",
                                    "lang": "mustache"
                                }
                            }
                        ]
                    }
                ]
            }
            api.createMonitor(storageMonitorConfig)
            # RAM usage monitors
            print("Creating RAM usage monitor for hostname %s" % hostname)
            ramMonitorConfig = {
                "type": "monitor",
                "name": "[" + hostname.upper() + "] RAM usage",
                "enabled": True,
                "schedule": {
                    "period": {
                        "interval": ram_monitor_time,
                        "unit": "" + ram_monitor_units.upper() + ""
                    }
                },
                "inputs": [
                    {
                        "search": {
                            "indices": [
                                "metricbeat-*"
                            ],
                            "query": {
                                "size": 0,
                                "query": {
                                    "bool": {
                                        "filter": [
                                            {
                                                "range": {
                                                    "@timestamp": {
                                                        "from": "{{period_end}}||-" + str(ram_monitor_time) + "m",
                                                        "to": "{{period_end}}",
                                                        "include_lower": True,
                                                        "include_upper": True,
                                                        "format": "epoch_millis",
                                                        "boost": 1
                                                    }
                                                }
                                            },
                                            {
                                                "term": {
                                                    "agent.hostname": {
                                                        "value": "" + hostname.upper() + "",
                                                        "boost": 1
                                                    }
                                                }
                                            }
                                        ],
                                        "adjust_pure_negative": True,
                                        "boost": 1
                                    }
                                },
                                "aggregations": {
                                    "when": {
                                        "avg": {
                                            "field": "system.memory.used.pct"
                                        }
                                    }
                                }
                            }
                        }
                    }
                ],
                "triggers": [
                    {
                        "name": "RAM_" + ram_percentage + "%",
                        "severity": "5",
                        "condition": {
                            "script": {
                                "source": "return ctx.results[0].aggregations.when.value == null ? false : ctx.results[0].aggregations.when.value > 0." + ram_percentage + "",
                                "lang": "painless"
                            }
                        },
                        "actions": [
                            {
                                "name": "EnvioAlertaITS",
                                "destination_id": "" + notification_destination_id1 + "",
                                "message_template": {
                                    "source": """
    Monitor "{{ctx.monitor.name}}" just entered alert status. Please investigate the issue.
        - Trigger: {{ctx.trigger.name}}
        - Severity: {{ctx.trigger.severity}}
        - Period start: {{ctx.periodStart}}
        - Period end: {{ctx.periodEnd}}

    RAM reached the """ + ram_percentage + """% threshold:
        - Average RAM percentage: {{ctx.results.0.aggregations.when.value}}
                                    """,
                                    "lang": "mustache"
                                },
                                "throttle_enabled": False,
                                "subject_template": {
                                    "source": "[ELK Alerts] " + hostname.upper() + " - RAM superior al " + ram_percentage + "%",
                                    "lang": "mustache"
                                }
                            },
                            {
                                "name": "EnvioAlertaSupportCPD",
                                "destination_id": "" + notification_destination_id2 + "",
                                "message_template": {
                                    "source": """
    Monitor "{{ctx.monitor.name}}" just entered alert status. Please investigate the issue.
        - Trigger: {{ctx.trigger.name}}
        - Severity: {{ctx.trigger.severity}}
        - Period start: {{ctx.periodStart}}
        - Period end: {{ctx.periodEnd}}

    RAM reached the """ + ram_percentage + """% threshold:
        - Average RAM percentage: {{ctx.results.0.aggregations.when.value}}
                                    """,
                                    "lang": "mustache"
                                },
                                "throttle_enabled": False,
                                "subject_template": {
                                    "source": "[ELK Alerts] " + hostname.upper() + " - RAM superior al " + ram_percentage + "%",
                                    "lang": "mustache"
                                }
                            }
                        ]
                    }
                ]
            }
            api.createMonitor(ramMonitorConfig)
            # CPU usage monitors
            '''print("Creating CPU usage monitor for hostname %s" % hostname)
            cpuMonitorConfig = {
                "type": "monitor",
                "name": "[" + hostname.upper() + "] CPU usage",
                "enabled": True,
                "schedule": {
                    "period": {
                        "interval": cpuMonitorTime,
                        "unit": "" + cpuMonitorUnits.upper() + ""
                    }
                },
                "inputs": [
                    {
                        "search": {
                            "indices": [
                                "metricbeat-*"
                            ],
                            "query": {
                                "size": 0,
                                "query": {
                                    "bool": {
                                        "filter": [
                                            {
                                                "range": {
                                                    "@timestamp": {
                                                        "from": "{{period_end}}||-" + str(cpuMonitorTime) + "m",
                                                        "to": "{{period_end}}",
                                                        "include_lower": True,
                                                        "include_upper": True,
                                                        "format": "epoch_millis",
                                                        "boost": 1
                                                    }
                                                }
                                            },
                                            {
                                                "term": {
                                                    "agent.hostname": {
                                                        "value": "" + hostname.upper() + "",
                                                        "boost": 1
                                                    }
                                                }
                                            }
                                        ],
                                        "adjust_pure_negative": True,
                                        "boost": 1
                                    }
                                },
                                "aggregations": {
                                    "when": {
                                        "avg": {
                                            "field": "system.cpu.total.pct"
                                        }
                                    }
                                }
                            }
                        }
                    }
                ],
                "triggers": [
                    {
                        "name": "CPU_" + cpuPercentage + "%",
                        "severity": "5",
                        "condition": {
                            "script": {
                                "source": "return ctx.results[0].aggregations.when.value == null ? false : ctx.results[0].aggregations.when.value > 0." + cpuPercentage + "",
                                "lang": "painless"
                            }
                        },
                        "actions": [
                            {
                                "name": "EnvioAlertaITS",
                                "destination_id": "" + notificationDestinationID_ITS + "",
                                "message_template": {
                                    "source": """
    Monitor "{{ctx.monitor.name}}" just entered alert status. Please investigate the issue.
        - Trigger: {{ctx.trigger.name}}
        - Severity: {{ctx.trigger.severity}}
        - Period start: {{ctx.periodStart}}
        - Period end: {{ctx.periodEnd}}

    CPU reached the """ + ramPercentage + """% threshold:
        - Average CPU percentage: {{ctx.results.0.aggregations.when.value}}
                                    """,
                                    "lang": "mustache"
                                },
                                "throttle_enabled": False,
                                "subject_template": {
                                    "source": "[ELK Alerts] " + hostname.upper() + " - CPU superior al " + cpuPercentage + "%",
                                    "lang": "mustache"
                                }
                            },
                            {
                                "name": "EnvioAlerta",
                                "destination_id": "" + notificationDestinationID_SUPPORTCPD + "",
                                "message_template": {
                                    "source": """
    Monitor "{{ctx.monitor.name}}" just entered alert status. Please investigate the issue.
        - Trigger: {{ctx.trigger.name}}
        - Severity: {{ctx.trigger.severity}}
        - Period start: {{ctx.periodStart}}
        - Period end: {{ctx.periodEnd}}

    CPU reached the """ + ramPercentage + """% threshold:
        - Average CPU percentage: {{ctx.results.0.aggregations.when.value}}
                                    """,
                                    "lang": "mustache"
                                },
                                "throttle_enabled": False,
                                "subject_template": {
                                    "source": "[ELK Alerts] " + hostname.upper() + " - CPU superior al " + cpuPercentage + "%",
                                    "lang": "mustache"
                                }
                            }
                        ]
                    }
                ]
            }
            api.createMonitor(cpuMonitorConfig)'''


# Call main/start program and catch exceptions
try:
    main()
except SystemExit:
    pass
except:
    print("Exception occurred:")
    print(traceback.format_exc())
    sys.exit(1)
