This repository contains different services that can be enabled at a CORE node. These services have been tested on [CORE](https://coreemu.github.io/core/) version 9.0.1 and [EMANE](https://coreemu.github.io/core/emane.html) version 1.4.1, using [Python](https://www.python.org/downloads/) version 3.10.6. 
 
---------------

## 1. Traffic\_Service.py
The **Traffic\_Service.py** automates the traffic flow generation at the flow source and destination nodes, collects the per second traffic statistics at both nodes, and moves the file to the user-specified directory on the host machine. To enable this service, right click on a CORE node, select _Config Service_, then select _maXentric_ under _Groups_ section, followed by selecting the desired service. 

This service uses [iperf3](https://github.com/esnet/iperf) network performance measurement tool to generate traffic. Use `sudo apt insteall iperf3` to install iperf3. User can customize the traffic parameters at the source and destination nodes before starting the CORE session by clicking on _Configure_, followed by clicking on _Configuration_ (see Figures 1 and 2 below for reference). Otherwise, these services use the default parameters to set up the traffic flow. To see the list of parameters iperf3 supports, execute `man iperf3` command in the terminal.

| ![FlowSourceSelection.png](Images/Traffic_Service/FlowSourceSelection.png) | 
|:--:| 
| **Figure 1**. Selecting the _FlowSource_ service at a CORE node (see left), and the list of parameters which can be customized for each traffic flow (see right). |

| ![FlowDestinationSelection.png](Images/Traffic_Service/FlowDestinationSelection.png) | 
|:--:| 
| **Figure 2**. Selecting the _FlowDestination_ service at a CORE node (see left), and the list of parameters which can be customized for each traffic flow (see right). |

To setup the background noise, channel conditions and antenna radiation patterns, etc. before starting the flow traffic, select the option _Any node moves_ in the _When to start the service_ field, as shown in Figure 1. It starts the traffic when any node in the CORE session moves, which can be done manually by moving a node in the Canvas or by passing node’s new GPS location as the command line input. Another option is to select _CORE session starts_ (see Figure 2), which starts the traffic when the CORE session starts.

User can also provide the storage directory location, where the log file will be moved after the traffic completes. In the default case, a destination node listens for traffic from all the source nodes (i.e., the nodes that have source service enabled) in the network. The port number a destination node listens on is decided based on the source node’s name. If the source node is _n1_, the port used to receive traffic from node _n1_ will be 5200+1. Note that different destination nodes can receive traffic on the same port, but a node cannot receive traffic from different sources at the same port.

The icon of both source and destination nodes change to notify the user about the start and end of the traffic service (see Figure 3). The default node icons are located in the /home/\<user\>/core/daemon/core/gui/data/icons/ folder. User can add new icons in this directory and use them in the script.

| ![ServiceStart.png](Images/Traffic_Service/ServiceStart.png) ![ServiceComplete.png](Images/Traffic_Service/ServiceComplete.png) | 
|:--:| 
| **Figure 3**. (Left) Node icon _alert.png_ represents the start of traffic service. (Right) Change in the node icon from _alert.png_ to _document-save.gif_ represents that the traffic is complete and the log files have been moved to the user-specified directory. |

To distinguish among different traffic flows, the name of the log file includes the names of the source and destination nodes, the port number used by the destination node to receive traffic, and the date and time of the file creation. For example, the file created by the source and destination nodes are `Client_n1_Server_n2_Port_5201_Time_2023-04-18_18:29:41.json` and `Server_n2_Client_n1_Port_5201_Time_2023-04-18_18:29:41.txt`, respectively. Use [iperf3\_plotter](https://github.com/ekfoury/iperf3_plotter) to plot statistics of the traffic flow; it requires a _.json_ file. The _.txt_ file provides the traffic flow details recorded at the destination node in the human-readable form. Note that the file type can be changed from the python script as per the need.

In case, user accidently stops the CORE session before the traffic completes, the log files are lost because the CORE destroys the node directories and its files. To prevent data loss in such situation, use [Datacollect Hook](https://coreemu.github.io/core/gui.html#session-states), which moves the log files before the node directory is destroyed. Follow these steps to setup Datacollect hook in a CORE session:

1. Before starting the CORE session, click on _Session_ in Canvas, then click _Hooks_.
2. Click _Create_.
3. Select _Datacollect_ as the Hook type from the drop-down menu on the right top corner.
4. You should see a `datacollect_hook.sh` file in left top corner field, and a new hook script in the remaining body (see Figure 4 for reference).
5. Type the following two commands:

```bash
cp /tmp/pycore.1/n*.conf/Server_* <Path to user specified directory on host machine>
cp /tmp/pycore.1/n*.conf/Client_* <Path to user specified directory on host machine>
```

6. Click _Save_ and close the Hooks popup. Do not click _Cancel_ as it would not create the Datacollect hook.
7. Run the Core session.

Since Hooks are global and do not depend on any service, they should be manually created at the start of the session. In the [current version of CORE (i.e., version 9.0.2)](https://github.com/coreemu/core/tree/release-9.0.2), the shutdown commands in [config service](https://coreemu.github.io/core/configservices.html) are not called when the CORE session stops. This is a bug, which has been [reported](https://discord.com/channels/382277735575322625/382277735575322627#:~:text=Thanks%20for%20helping%20point%20this%20out%2C%20this%20issue%20for%20config%20services%20has%20been%20fixed%20on%20the%20develop%20branch%20for%20the%20next%20release) to the developers of CORE.

| ![DatacollectHook.png](Images/Traffic_Service/DatacollectHook.png) | 
|:--:| 
| **Figure 4**. Selecting Datacollect hook in CORE. |


### Before running the service:

Traffic\_Service.py is a custom [config service](https://coreemu.github.io/core/configservices.html). To use it at a node in CORE, add the following entry to the **/etc/core/core.conf** file, and store this python script in the `custom_services` directory.
```bash
custom_config_services_dir = /home/<user>/.coregui/custom_services
```

---------------


## 2. OLSRd_Service
The **OLSRd\_Service.py** enables OLSRd at a node, which is the Linux installation of optimized link state routing (OLSR) protocol and is based on [RFC 3626](https://www.rfc-editor.org/rfc/rfc3626.html). Read more about OLSRd at <https://github.com/OLSR/olsrd> and <https://manpages.ubuntu.com/manpages/trusty/man8/olsrd.8.html>. 

Follow the commands given below to install OLSRd in CORE.
```bash
sudo apt install build-essential 
sudo apt install cmake

#If needed, 
#sudo apt update
#sudo apt upgrade

sudo apt install git
sudo apt install net-tools   
sudo apt install flex flex-doc
sudo apt install bison bison-doc
sudo apt install gpsd
sudo apt install libgps-dev

git clone https://github.com/OLSR/olsrd.git
cd olsrd/
make build_all
sudo make install_all

# Make all script files executable
sudo chmod a+x /core/*.sh; ls -l /core

# If needed
# To uninstall OLSRd: uninstall uninstall_libs
# To clean OLSRd implementation: uberclean clean_libs  
```

Once OLSRd is successfully installed, check the `defaultOlsrd.conf` file. It includes the different input parameters, such as _MainIP_ and _Interface_. Each CORE node must have its own OLSR configuration file, which is automatically created by OLSRd\_Service.py. This python script is based on the custom [Service](https://coreemu.github.io/core/services.html#creating-new-services) template, which is different than [Config Service](https://coreemu.github.io/core/configservices.html).

### Before running the service:

Keep the OLSRd\_Service.py inside `/home/<user>/.coregui/custom_services/` folder and add the following entry in the **/etc/core/core.conf** file. 
```bash
custom_services_dir = /home/<user>/.coregui/custom_services
```

To make OLSR as the default routing protocol, user must remove the other routing protocol (such as OSPF, BGP) already enabled at the CORE node. The steps to select OLSR routing protocol at a node are as follows:

1. Right click on the CORE node and select _Services (Deprecated)_.
2. Click on _maXentric_ under _Groups_, then click _OLSRdService_ under _Services_.
3. As shown in Figure 5, _OLSRdService_ will appear under _Selected_ label. Then press _Save_. 
4. User can check the details of this service by clicking on _Configure_. The first option is _Files_ under which you would see the `myOlsrd.conf` and `myOlsrd.sh` files that will be created upon starting the CORE session. Under the _Startup/Shutdown_ label, you will see two commands. `chmod +x myOlsrd.sh` makes the file executable, and `./myOlsrd.sh` runs the file.
5. To disable other routing protocol at a CORE node, right click and select _Configure Services_. Under the _Selected_ label, you will see all the services selected for this node. Click on the unwanted service, then click _Remove_, followed by _Save_.

| ![OLSRdSelection.png](Images/OLSRd_Service/OLSRdSelection.png) | 
|:--:| 
| **Figure 5**. Selecting OLSRd service at CORE node _n2_. |

To check if a service is running on a node once the CORE session starts, open the terminal at the CORE node and execute command `top`. You should see _myOlsrd_ service (see Figure 6 for reference). To see OLSR protocol in action (i.e., get the 1- and 2-hop neighbor nodes), run command `./myOlsrd.sh`. If you do not see the _myOlsrd_ service running, check if the `myOlsrd.conf` and `myOlsrd.sh` files are in the CORE node’s local directory, and ensure that `myOlsrd.sh` is an executable file (use command `ls -la`  to see files and their permissions). If these files are not in the directory, copy them to the CORE node’s local directory and execute the commands given under the _Startup/Shutdown_ label.

| ![RunningOLSRd.png](Images/OLSRd_Service/RunningOLSRd.png) | 
|:--:| 
| **Figure 6**. A 6-node network topology is shown on the left. OLSRd service is enabled on each node. When the CORE session starts, an executable `myOlsrd.sh` file is created at each node (see top center). The `top` command shows the _Olsrd_ in the bottom center. The routes found at node _n1_ using OLSR are shown on the right. |
