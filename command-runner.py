import commands
import argparse
import os
from getpass import getpass
from netmiko import SSHDetect, ConnectHandler, NetMikoAuthenticationException, NetMikoTimeoutException


print("Cisco Command Runner Starting....")

parser = argparse.ArgumentParser(description='Collect required information for a basic Command Runner')
parser.add_argument('-o',dest='onscreen',action='store_true',help="Display output on screen")
parser.add_argument('--outputname',dest='outputname',help="Optional output filename prefix")
parser.add_argument("filename",nargs=1,help="filename of file which contains device list")

args=parser.parse_args()
onscreen = args.onscreen
outputname=args.outputname
if outputname==None:
    outputname="session-log"

filename = args.filename

print (f"Filename to run commands on: {filename[0]}")
print (f"Output prefix for files: {outputname}")

# Open up the input filename
try:
    file_object = open(filename[0],"r")
except IOError as e:
    print("Error: "+str(e))
    exit(-1)

device_list=[]
for line in file_object:
    cleaned = line.replace("\n", "")
    # Remove the newline character, and split the file into the fields
    device = cleaned.split()
    if len(device) < 3:
        print(f"WARNING: Ignoring Line '{cleaned}', Doesn't contain required fields.")
    else:
        item={
            "ipaddress":device[0],
            "username":device[1],
            "password":device[2]
        }
        device_list.append(item)



# Iterate through the devices that were passed and attempt to gather information.
for device in device_list:


    remote_device = {'device_type': 'autodetect',
                    'host': device["ipaddress"],
                    'username': device["username"],
                    'password': device["password"]}

    print ("------------------------------------------------------------")
    print ("Performing a health check on "+remote_device['host']+" using username: "+remote_device['username'])

    # Try to detect the type of device
    try:

        guesser = SSHDetect(**remote_device,timeout=10)
    except (NetMikoAuthenticationException, NetMikoTimeoutException) as e:
        print("Error connecting to device: "+str(e))
        continue

    best_match = guesser.autodetect()

    print("This device is detected to be model type: " + best_match)

    if best_match not in ['cisco_ios', 'cisco_nxos', 'cisco_xr']:
        print("ERROR: " + best_match + " is not currently supported in this revision")
        continue
    else:

        remote_device['device_type'] = best_match

        ssh_connection = ConnectHandler(**remote_device)

        ssh_connection.open_session_log("session-log-"+device["ipaddress"]+".log", mode=u'write')

        # enter enable mode
        ssh_connection.enable()

        # prepend the command prompt to the result (used to identify the local host)
        result = ssh_connection.find_prompt() + "\n"
        print ("Device name is: "+result)

        # execute the show cdp neighbor detail command
        # we increase the delay_factor for this command, because it take some time if many devices are seen by CDP

        if best_match == 'cisco_ios':
            cmds = commands.commands_ios
        elif best_match == 'cisco_nxos':
            cmds = commands.commands_nxos
        elif best_match == 'cisco_xr':
            cmds = commands.commands_iosxr


    for command in cmds:
        print("Executing: '" + command + "' on " + remote_device['host'])

        result = ssh_connection.send_command(command)

        if onscreen:
            print(result)

        # close SSH connection
    ssh_connection.close_session_log()
    ssh_connection.disconnect()

