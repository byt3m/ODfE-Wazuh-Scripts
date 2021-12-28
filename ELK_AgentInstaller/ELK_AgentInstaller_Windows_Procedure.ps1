param(
    [Parameter(mandatory=$true)] [string] $agent
)

# Check admin rights
If (!(([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] “Administrator”)))
{
    Write-Warning “Administrator privileges are required to run this script.”
    Exit
}

# GLOBALS
$elasticsearchHosts = '[""]'
$beatsVersion = "7.12.1"
$beatsInstallerURL = "https://artifacts.elastic.co/downloads/beats/$agent/$agent-oss-$beatsVersion-windows-x86_64.zip"
$wazuhVersion = "4.2.5"
$wazuhAgentInstallerURL = "https://packages.wazuh.com/4.x/windows/wazuh-agent-$wazuhVersion-1.msi"
$wazuhServerDNS = ""
$wazuhServiceName = "WazuhSvc"
$wazuhAgentGroup = "Windows"

# Paths
$certificatesDirBeatConfig = "C:\\Certs"
$certificatesInstallDir = "C:\Certs"
$configDir = Join-Path $PSScriptRoot "configuration_files"
$caCertificate = Join-Path $PSScriptRoot "certificates\CA.crt"
$agentCertificate = Join-Path $PSScriptRoot ("certificates\" + $env:COMPUTERNAME + ".crt")
$agentKey = Join-Path $PSScriptRoot ("certificates\" + $env:COMPUTERNAME + ".key")

# Functions
function ReadInput
{
    Param ( [string] $msg, [switch] $secure, [switch]$yesno ) 

    while ( $true )
    {
        if ($secure)
        {
            $input = Read-Host $msg -AsSecureString
        }
        else
        {
            $input = Read-Host $msg
        }

        if ( $input )
        {
            if ($yesno)
            {
                if ($input -eq "N" -or $input -eq "Y")
                {
                    break
                }
                else
                {
                    Write-Warning "Write 'N' for No or 'Y' for Yes"
                }
            }
            else
            {
                break
            }
        }
    }

    return $input
}

function SecureStringtoString
{
    Param ( [securestring] $pwd ) 

    return [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($pwd))
}

# Agent installation
try
{
    # Handle agent param received
    if ($agent -eq "filebeat")
    {
        $installer = Join-Path $env:TEMP "$agent-oss-$beatsVersion-windows-x86_64.zip"
        $installerURL = $beatsInstallerURL
        $agentExeName = "$agent.exe"
        $agentExeCmd = "setup --index-management --pipelines"
        $modulesDirName = "modules.d"
    }
    elseif ($agent -eq "metricbeat")
    {
        $installer = Join-Path $env:TEMP "$agent-oss-$beatsVersion-windows-x86_64.zip"
        $installerURL = $beatsInstallerURL
        $agentExeName = "$agent.exe"
        $agentExeCmd = "setup --index-management"
        $modulesDirName = "modules.d"
    }
    elseif ($agent -eq "wazuh")
    {
        $installer = Join-Path $env:TEMP "$agent-agent-$wazuhVersion-1.msi"
        $installerURL = $wazuhAgentInstallerURL
        $installerCmd = "/q WAZUH_MANAGER=$wazuhServerDNS WAZUH_REGISTRATION_SERVER=$wazuhServerDNS WAZUH_AGENT_GROUP=$wazuhAgentGroup"
        $agentExeName = "agent-auth.exe"
        $agentExeCmd = "-m $wazuhServerDNS -P `"XXPASSXX`""
    }
    else
    {
        Write-Host "[X] Agent $agent not recognized!" -ForegroundColor Red
        Exit
    }

    # Check if agent is already installed
    if ((Get-ChildItem -Path $env:ProgramFiles -Recurse -Filter $agentExeName -File -ErrorAction Ignore) -or `
         (Get-ChildItem -Path ${env:ProgramFiles(x86)} -Recurse -Filter $agentExeName -File -ErrorAction Ignore))
    {
        Write-Host "  [X] $agent is already installed!" -ForegroundColor Red
        Exit
    }

    # Download the installer    
    if (Test-Path $installer)
    {
        Write-Host "[-] Installer found at `"$installer`", skipping download..." -ForegroundColor Cyan
    }
    else
    {
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12;
        Write-Host "[-] Downloading $agent installer from `"$installerURL`"" -ForegroundColor Cyan
        $wc = New-Object net.webclient
        $wc.Downloadfile($installerURL, $installer)
        #Invoke-WebRequest -Uri $installerURL -OutFile $installer
    }    

    # Perform installation
    Write-Host "[+] Installing $agent" -ForegroundColor Cyan

    if ($agent -eq "wazuh")
    {
        # Install wazuh agent
        Write-Host "  [-] Installing $agent agent" -ForegroundColor Cyan
        & $installer ($installerCmd -split " ")
        while (!(Get-Service -Name $wazuhServiceName -ErrorAction Ignore)){ }

        # Register agent
        Write-Host "  [-] Registering agent" -ForegroundColor Cyan
        $agentExePath = Join-Path ${env:ProgramFiles(x86)} "ossec-agent\$agentExeName"
        & $agentExePath (($agentExeCmd -split " ") -replace "XXPASSXX",(SecureStringtoString (ReadInput -msg "      Write the agent register password" -secure)))

        # Apply custom configuration
        Write-Host "  [-] Copying custom configuration" -ForegroundColor Cyan
        $wazuhInstallDir = Join-Path ${env:ProgramFiles(x86)} "ossec-agent"
        $wazuhConfigDir = Join-Path $configDir "wazuh_agent"
        Get-ChildItem -Path $wazuhConfigDir -File | ForEach-Object { Copy-Item -Path $_.FullName -Destination $wazuhInstallDir -Force }
                
        # Restart service
        Write-Host "  [-] Starting service" -ForegroundColor Cyan
        Restart-Service -Name $wazuhServiceName
    }
    else
    {
        # Check certs exist
        if (!(Test-Path $caCertificate) -or !(Test-Path $agentCertificate) -or !(Test-Path $agentKey))
        {
            Write-Host "[X] Certificate files not found!" -ForegroundColor Red
            Exit
        }

        # Extract installer to %TEMP%
        Write-Host "  [-] Extracting installer" -ForegroundColor Cyan
        $installerTempDir = Join-Path $env:TEMP "$agent-$beatsVersion-windows-x86_64"
        Remove-Item -Path $installerTempDir -Recurse -Force -ErrorAction Ignore
        Expand-Archive -Path $installer -DestinationPath $env:TEMP

        # Copy config files to %TEMP%
        $tempBeatsConfigDir = Join-Path $env:TEMP ($agent + "_config_files")
        New-Item -Path $tempBeatsConfigDir -ItemType Directory -Force | Out-Null
        Copy-Item -Path (Join-Path $configDir ($agent + "\*")) -Destination $tempBeatsConfigDir -Recurse -Force        
        if ($agent -eq "metricbeat")
        {
            $systemModule = Join-Path $tempBeatsConfigDir ("modules.d\system.yml.windows")
            Rename-Item -Path $systemModule -NewName "system.yml"
        }

        # Copy and delete the config files to the agent installer temp dir
        Copy-Item -Path (Join-Path $tempBeatsConfigDir "*") -Destination $installerTempDir -Recurse -Force
        Remove-Item -Path $tempBeatsConfigDir -Recurse -Force

        # Modify config files
        Write-Host "  [-] Modifying config files" -ForegroundColor Cyan
        $configFile = Join-Path $installerTempDir "$agent.yml"
        $configFileContent = Get-Content -Path $configFile
        $configFileContent = $configFileContent -replace "XXCOMPUTERNAMEXX",($env:COMPUTERNAME).ToLower()
        $configFileContent = $configFileContent -replace "XXCACERTIFICATEXX", ($certificatesDirBeatConfig + "\\" + [System.IO.Path]::GetFileName($caCertificate))
        $configFileContent = $configFileContent -replace "XXAGENTCERTIFICATEXX",($certificatesDirBeatConfig + "\\" + [System.IO.Path]::GetFileName($agentCertificate))
        $configFileContent = $configFileContent -replace "XXAGENTKEYXX",($certificatesDirBeatConfig + "\\" + [System.IO.Path]::GetFileName($agentKey))
        $configFileContent = $configFileContent -replace "XXELKHOSTSXX",$elasticsearchHosts
        $configFileContent > $configFile

        # Move agent to programfiles
        Write-Host "  [-] Moving $agent files to"`"$env:ProgramFiles`" -ForegroundColor Cyan
        Move-Item -Path $installerTempDir -Destination $env:ProgramFiles -Force
        Rename-Item (Join-Path $env:ProgramFiles "$agent-$beatsVersion-windows-x86_64") "$agent" -Force

        # Copy certs
        Write-Host "  [-] Moving certificates to `"$certificatesInstallDir`"" -ForegroundColor Cyan
        if (!(Test-Path -Path $certificatesInstallDir)){ New-Item -Path $certificatesInstallDir -ItemType Directory | Out-Null }
        Copy-Item -Path $caCertificate -Destination $certificatesInstallDir -Force
        Copy-Item -Path $agentCertificate -Destination $certificatesInstallDir -Force
        Copy-Item -Path $agentKey -Destination $certificatesInstallDir -Force

        # Install agent
        Write-Host "  [-] Installing $agent" -ForegroundColor Cyan
        $agentProgFiles = Join-Path $env:ProgramFiles "$agent"
        Set-Location $agentProgFiles
        $installScript = Join-Path $agentProgFiles "install-service-$agent.ps1"
        & "$installScript"

        # Setup agent
        Write-Host "  [-] Setting up $agent" -ForegroundColor Cyan
        $agentExePath = Join-Path $agentProgFiles $agentExeName
        & "$agentExePath" ($agentExeCmd -split " ")
        Start-Service $agent

        # Ask for modules to be enabled
        Write-Host "  [i] Write the modules to be enabled separated by spaces (for example: iis mysql)." -ForegroundColor Yellow
        Write-Host "  [i] You can find a list of modules at the angent's offical documentation." -ForegroundColor Yellow
        $modules = ReadInput -msg "      Choose the modules to be installed"
        & "$agentExePath" ("modules enable $modules" -split " ")

        Set-Location $PSScriptRoot
    }

     Write-Host "  [*] $agent installation finished" -ForegroundColor Green
}
Catch
{
    Write-Host "[X] Installation failed!`n" -ForegroundColor Red
    Write-Error $Error[0]
    Exit
}

Write-Host "[*] Done!" -ForegroundColor Green