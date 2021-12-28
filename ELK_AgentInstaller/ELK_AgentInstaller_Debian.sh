#!/bin/bash

export PATH=$PATH:/usr/local/sbin:/usr/sbin:/sbin

# Check root permissions
if [[ $(/usr/bin/id -u) -ne 0 ]]; then
    echo "This script requires root privileges"
    exit 1
fi

function helptext()
{
  echo "This script will install the supported elasticsearch and wazuh agents."
}

function usage()
{
  echo "Usage: ./ELK_AgentInstaller_Debian.sh -a <agentname> -m \"<beat_list_modules>\""
  echo "  -a: The available agents are: filebeat, metricbeat and wazuh."
  echo "  -m: The modules option is only used for beat agents and it must be a list inside double quotes separated spaces."
  echo "      The available modulesare:"
  echo "          - Metricbeat: system, apache, mysql, elasticsearch and kibana."
  echo "          - Filebeat: system, apache, mysql, elasticsearch and kibana."
}

function check_args()
{
  # Check beat option
  if ! [[ "$AGENT" =~ ^(metricbeat|filebeat|wazuh)$ ]]; #regular expression with agent possible options
    then echo "Error in agent option. Agent selected: $AGENT";
    usage
    exit 1
  fi

  # Check modules option
  if [[ "$AGENT" =~ ^(metricbeat|filebeat)$ ]]; then
    if ! [[ -z "$MODULES" ]]; then #check modules is not empty
      readarray -d ' ' -t modulesArray <<<"$MODULES" #split the modules string based on the delimiter: space
      for (( n=0; n < ${#modulesArray[*]}; n++ ))
      do
        if ! [[ "${modulesArray[n]}" =~ ^(system|apache|mysql|elasticsearch|kibana)[[:space:]]?$ ]]; #regular expression with modules possible options
          then echo "Error in module option: ${modulesArray[n]}";
          usage
          exit 1
        fi
      done
    else
      echo "Error in modules option.";
      usage
      exit 1
    fi
  fi
}


function checkHostReachable()
{
	if ping -c 1 $1 &> /dev/null
	then
	  return 0
	else
	  return 1
	fi
}


function installWazuh()
{
	wazuhServerDNS=
	wazuhAgentGroup=Linux
	wazuhAgentVersion=4.2.4
	wazuhAgentInstallerURL=https://packages.wazuh.com/4.x/apt/pool/main/w/wazuh-agent/wazuh-agent_$wazuhAgentVersion-1_amd64.deb
	wazuhServiceName=wazuh-agent
	wazuhConfigDir=/var/ossec/etc/
	wazuhConfigFile=/var/ossec/etc/ossec.conf
	wazuhAgentGroup=Linux

	echo "[+] Installing Wazuh"
	
	# Check $wazuhServerDNS is reachable
	if checkHostReachable $wazuhServerDNS
	then
	  echo "  [*] Wazuh server $wazuhServerDNS is reachable"
	else
	  echo "  [X] ERROR: wazuh server $wazuhServerDNS is NOT reachable"
	  exit 1
	fi
	
	# Download package
	echo "  [-] Downloading package from $wazuhAgentInstallerURL"
	curl $wazuhAgentInstallerURL -so /tmp/wazuh-agent.deb
	
	# Ask for the agent register password
	echo "  [-] Enter the wazuh agent register password:"
	read -s wazuhRegistrationPassword
	
	# Install .deb package
	echo "  [-] Installing package"
	dpkg -i /tmp/wazuh-agent.deb
	
	# Register agent
	echo "  [-] Registering agent"
	/var/ossec/bin/agent-auth -m $wazuhServerDNS -P $wazuhRegistrationPassword -G $wazuhAgentGroup
	
	# Enable $wazuhServiceName service
	echo "  [-] Enabling $wazuhServiceName service"
	systemctl daemon-reload
	systemctl enable $wazuhServiceName
	
	# Replace MANAGER_IP in ossec.conf
	echo "  [-] Replacing wazuh MANAGER_IP with $wazuhServerDNS"
	sed -i "s/MANAGER_IP/$wazuhServerDNS/" $wazuhConfigFile
	
	# Apply custom configs
	echo "  [-] Copying custom configuration files"
	cp ./configuration_files/wazuh_agent/* $wazuhConfigDir
	
	# Start service
	echo "  [-] Starting wazuh service"
	systemctl start wazuh-agent
	
	# Check wazuh service state
	if [[ $(systemctl status wazuh-agent | grep "active (running)") ]]; then
		echo "  [*] Service started correctly."
	else
		echo "  [X] ERROR: service did not start correctly, please troubleshoot the daemon with 'journalctl -u wazuh-agent' and log file '/var/ossec/logs/ossec.log'"
	fi
}

function installBeat()
{
	elasticsearchHosts='[""]'
	hostname=$(cat /etc/hostname)
	ca="\/etc\/certs\/CA.crt"
	cert="\/etc\/certs\/$hostname.crt"
	key="\/etc\/certs\/$hostname.key"
	beatsVersion=7.12.1
	beatsConfigDir=/etc/$AGENT/
	beatsInstallerURL=https://artifacts.elastic.co/downloads/beats/$AGENT/$AGENT-oss-$beatsVersion-amd64.deb
	beatsCertDir=/etc/certs/
	
	
	echo "[+] Installing $AGENT"
	echo "  [-] Downloading installer from $beatsInstallerURL"
	curl $beatsInstallerURL -so /tmp/$AGENT.deb
	echo "  [-] Installing package"
	dpkg -i /tmp/$AGENT.deb
	echo "  [-] Copying certificates"
	mkdir $beatsCertDir
	cp ./certificates/* $beatsCertDir
	echo "  [-] Applying configuration"
	sed "s/XXCOMPUTERNAMEXX/$hostname/" ./configuration_files/$AGENT/$AGENT.yml > /tmp/1.yml
	sed "s/XXELKHOSTSXX/$elasticsearchHosts/" /tmp/1.yml > /tmp/2.yml
	sed "s/XXCACERTIFICATEXX/$ca/" /tmp/2.yml > /tmp/1.yml
	sed "s/XXAGENTCERTIFICATEXX/$cert/" /tmp/1.yml > /tmp/2.yml
	sed "s/XXAGENTKEYXX/$key/" /tmp/2.yml > /tmp/1.yml
	echo "  [-] Copying configuration files"
	cp /tmp/1.yml $beatsConfigDir$AGENT.yml
	if [ "${AGENT}" = "metricbeat" ]
	then
	  yes | cp -ri configuration_files/metricbeat/modules.d/* /etc/metricbeat/modules.d/
	  yes | cp -ri configuration_files/metricbeat/module/mysql/performance/* /usr/share/metricbeat/module/mysql/performance/
	  mv /etc/metricbeat/modules.d/system.yml.debian /etc/metricbeat/modules.d/system.yml.disabled
	fi
	echo "  [-] Setting up $AGENT"
	if [ "${AGENT}" = "filebeat" ]
	then  # Install Wazuh agent
	  /bin/$AGENT setup --index-management --pipelines
	else # Install beat agent
	  /bin/$AGENT setup --index-management
	fi
	echo "  [-] Enabling modules '${MODULES}'"
	/bin/$AGENT modules enable ${MODULES}
	echo "  [-] Enabling $AGENT service"
	systemctl daemon-reload
	systemctl enable $AGENT
	systemctl start $AGENT
	echo "  [!] Please perform additional steps:"
	echo "         1. Check the service is running 'systemctl status $AGENT'"
	echo "         2. Troubleshoot any error with 'journalctl -u $AGENT'"
}

# Read arguments
while getopts "a:m: h" flag
do
  case "${flag}" in
    a) AGENT=${OPTARG};;
    m) MODULES=${OPTARG};;
    h) helptext
       usage
       exit 0;; #exit gracefully
    *) helptext
       usage
       exit 1;; #exit abnormally
  esac
done

# Check arguments
check_args

if [ "${AGENT}" = "wazuh" ]
then  # Install Wazuh agent
  installWazuh
else # Install beat agent
  installBeat
fi

echo "[*] Done"
exit 0