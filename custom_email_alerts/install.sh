#!/bin/bash

# Check root permissions
if [[ $(/usr/bin/id -u) -ne 0 ]]; then
    echo "This script requires root privileges"
    exit 1
fi

integrations=/var/ossec/integrations
output=$integrations/custom-cve-email-alerts_output

echo "[-] Moving files to $integrations"
mv *.py $integrations
mv *.json $integrations

echo "[-] Creating output dir: $output"
mkdir $output
chmod 770 $output
chown root:ossec $output

echo "[-] Changing file permissions"
chmod 750 $integrations/utilities.py $integrations/SendEmail.py $integrations/send-custom-cve-email-alerts.py $integrations/send-custom-cve-email-alerts_settings.json $integrations/custom-cve-email-alerts.py
chown root:ossec $integrations/utilities.py $integrations/SendEmail.py $integrations/send-custom-cve-email-alerts.py $integrations/send-custom-cve-email-alerts_settings.json $integrations/custom-cve-email-alerts.py

echo "[-] Renaming integration file"
mv $integrations/custom-cve-email-alerts.py $integrations/custom-cve-email-alerts

echo "[!] Check files are correct!"
ls -la $integrations

echo "[*] Done"