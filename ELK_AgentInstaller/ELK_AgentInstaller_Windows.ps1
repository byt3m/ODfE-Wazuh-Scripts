param(
    [Parameter(mandatory=$false)] [switch] $filebeat,
    [Parameter(mandatory=$false)] [switch] $metricbeat,
    [Parameter(mandatory=$false)] [switch] $wazuh
)

Clear-Host

# Procedure script path
$procedureScript = Join-Path $PSScriptRoot "ELK_AgentInstaller_Windows_Procedure.ps1"

# Check admin rights
If (!(([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] “Administrator”)))
{
    Write-Warning “Administrator privileges are required to run this script.”
    Exit
}

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


# Check if procedure script exists
if (!(Test-Path -Path $procedureScript))
{
    Write-Host "[X] Procedure script `"$procedureScript`" not found!" -ForegroundColor Red
    Exit
}

Write-Host "
___________.____     ____  __.
\_   _____/|    |   |    |/ _|
 |    __)_ |    |   |      <  
 |        \|    |___|    |  \ 
/_______  /|_______ \____|__ \
        \/         \/       \/                  
" -ForegroundColor Magenta

# Advertisement
Write-Host "WARNING! This script does not automatize every aspect of beats installation!" -ForegroundColor Yellow
Write-Host "Remember to do the necessary configurations depending on your system. For example:" -ForegroundColor Yellow
Write-Host "`t- If you are installing the `"mysql`" metricbeat module, you must configure a MySQL account so the agent can gather the required metrics." -ForegroundColor Yellow
Write-Host "`t- Check that services like IIS, apache, mysql... are using the default paths for storing their logs, otherwise you have to configure them manually." -ForegroundColor Yellow
Write-Host "`t- For questions on how to do the manual tasks, refer to the original documentation of an agent." -ForegroundColor Yellow
Write-Host "`t- etc.`n" -ForegroundColor Yellow

if ((ReadInput -msg "Do you want to continue? (Y/N)" -yesno) -eq "n")
{
    Exit
}

$noparam = $true

if ($filebeat) # -filebeat
{
    $noparam = $false
    & $procedureScript "filebeat"
}

if ($metricbeat) # -metricbeat
{
    $noparam = $false
    & $procedureScript "metricbeat"
}

if ($wazuh) # -wazuh
{
    $noparam = $false
    & $procedureScript "wazuh"
}

if ($noparam)
{
    Write-Host "`n"
    Write-Warning "Usage: .\ELK_AgentInstaller_Windows.ps1 <agent>"
    Write-Host "Agents available:`n  -filebeat: install filebeat agent.`n  -metricbeat: install metricbeat agent.`n  -wazuh: install wazuh agent." -ForegroundColor Yellow
    Exit
}