This repository contains different services that can be enabled at a CORE node. These services have been tested on CORE version 9.0.1 and EMANE version 1.4.1, using python version 3.10.6. 

1. The **Traffic\_Service.py** automates the traffic flow generation at the flow source and destination nodes, collects the per second traffic statistics at both nodes, and moves the file to the user-specified directory on the host machine. To enable this service, right click on a CORE node, select ‘Config Service’, then select maXentric under ‘Groups’ section, followed by selecting the desired service. 

This service uses iperf3 network performance measurement tool to generate traffic. Use **sudo apt insteall iperf3** to install iperf3 or follow this link <https://github.com/esnet/iperf> for installation details. User can customize the traffic parameters at the source and destination nodes before starting the CORE session by clicking on 'Configure', followed by clicking on 'Configuration' (see Figures 1 and 2 below for reference). Otherwise, these services use the default parameters to set up the traffic flow. To see the list of parameters iperf3 supports, execute **man iperf3** command in the terminal.

![](Aspose.Words.42dac42c-ff96-4ab6-9a84-e21f8560cfbf.001.png)

Figure 1. Selecting the FlowSource service at a CORE node (see left), and the list of parameters which can be customized for each traffic flow (see right). 

![](Aspose.Words.42dac42c-ff96-4ab6-9a84-e21f8560cfbf.002.png)

Figure 2. Selecting the FlowDestination service at a CORE node (see left), and the list of parameters which can be customized for each traffic flow (see right).

To setup the background noise, channel conditions and antenna radiation patterns, etc. before starting the flow traffic, select the option ‘Any node moves’ in the ‘When to start the service’ field, as shown in Figure 1. It starts the traffic when any node in the CORE session moves, which can be done manually by moving a node in the Canvas or by passing node’s new GPS location as the command line input. Another option is to select ‘CORE session starts’ (see Figure 2), which starts the traffic when the CORE session starts.

User can also provide the storage directory location, where the log file will be moved after the traffic completes. In the default case, a destination node listens for traffic from all the source nodes (i.e., the nodes that have source service enabled) in the network. The port number a destination node listens on is decided based on the source node’s name. If the source node is ‘n1’, the port used to receive traffic from node n1 will be 5200+1. Note that different destination nodes can receive traffic on the same port, but a node cannot receive traffic from different sources at the same port.

The icon of both source and destination nodes change to notify the user about the start and end of the traffic service (see Fig. 3). The default node icons are located in the ~/core/daemon/core/gui/data/icons/ folder. User can add new icons in this directory and use them in the script.

![](Aspose.Words.42dac42c-ff96-4ab6-9a84-e21f8560cfbf.003.png)  ![](Aspose.Words.42dac42c-ff96-4ab6-9a84-e21f8560cfbf.004.png) 
Figure 3. (Left) Change in the node icon to ‘alert.png’ represents the start of traffic service. (Right) Change in the node icon from ‘alert.png’ to ‘document-save.gif’ represents that the traffic is complete and the log files have been moved to the user-specified directory.

To distinguish among different traffic flows, the name of the log file includes the names of the source and destination nodes, the port number used by the destination node to receive traffic, and the date and time of the file creation. For example, the file created by the source and destination nodes are ‘Client\_n1\_Server\_n2\_Port\_5201\_Time\_2023-04-18\_18:29:41.json’ and ‘Server\_n2\_Client\_n1\_Port\_5201\_Time\_2023-04-18\_18:29:41.txt’, respectively. To plot statistics, use iperf3\_plotter (<https://github.com/ekfoury/iperf3_plotter>), which requires a ‘.json’ file. The ‘.txt’ file provides the traffic flow details recorded at the destination node, in the human-readable form. Note that the file type can be changed from the python script as per the need.

In case, user accidently stops the CORE session before the traffic completes, the log files are lost because the CORE destroys the node directories and its files. To prevent data loss in such situation, use Datacollect Hook (see Session States in <https://coreemu.github.io/core/gui.html> for details), which moves the log files before the node directory is destroyed. Follow these steps to setup Datacollect hook in a CORE session:

1. Before starting the CORE session, click on ‘Session’ in Canvas, then click ‘Hooks’.
1. Click ‘Create’.
1. Select ‘Datacollect’ as the Hook type from the drop-down menu on the right top corner.
1. You should see a ‘datacollect\_hook.sh’ file in left top corner field, and a new hook script in the remaining body (see Figure 4 for reference).
1. Type the following two commands:

**cp /tmp/pycore.1/n\*.conf/Server\_\* <Path to user specified directory on host machine>**

**cp /tmp/pycore.1/n\*.conf/Client\_\* <Path to user specified directory on host machine>**

1. Click ‘Save’ and close the Hooks popup. Do not click ‘Cancel’ as it would not create the Datacollect hook.
1. Run the Core session.

Since Hooks are global and do not depend on any service, they should be manually created at the start of the session. In the current version of CORE (i.e., version 9.0.2), the shutdown commands in ‘config service’ are not called when the CORE session stops. This is a bug, which has been reported to the developers of CORE.

![](Aspose.Words.42dac42c-ff96-4ab6-9a84-e21f8560cfbf.005.png)

**Figure 4.** Selecting Datacollect hook in CORE.

**Before running the service:**

Traffic\_Service.py is a custom ‘config service’ (see <https://coreemu.github.io/core/configservices.html> to learn more about ‘config servicec’). To use it at a node in CORE, add the following entry to the **/etc/core/core.conf** file, and store this python script in the custom\_services directory.

**custom\_config\_services\_dir = /home/<user>/.coregui/custom\_services**


1. The **OLSRd\_Service.py** enables OLSRd at a node, which is the Linux installation of optimized link state routing (OLSR) protocol and is based on RFC 3626 (<https://www.rfc-editor.org/rfc/rfc3626.html>). Read more about OLSRd at <https://manpages.ubuntu.com/manpages/trusty/man8/olsrd.8.html> and <https://github.com/OLSR/olsrd>. Follow the commands given below to install OLSRd in CORE.


\-----------------------------------------

sudo apt install build-essential 

sudo apt install cmake

#If needed, 

#sudo apt install python3

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

make build\_all

sudo make install\_all

\# Make all script files executable

sudo chmod a+x /core/\*.sh; ls -l /core

\# If needed

#To uninstall OLSRd: uninstall uninstall\_libs

#To clean OLSRd implementation: uberclean clean\_libs  

\-----------------------------------------

Once OLSRd is successfully installed, check the defaultOlsrd.conf file. It includes the different input parameters one can use, such as MainIP and Interface. Each CORE node must have its own OLSR configuration file, which is automatically created by ‘OLSRd\_Service.py’. This python script is based on the custom ‘service’ template provided at <https://coreemu.github.io/core/services.html#creating-new-services>.

**Before running the service:**

Keep the OLSRd\_Service.py inside /home/<user>/.coregui/custom\_services/ folder and add the following entry in the **/etc/core/core.conf** file. 

**custom\_services\_dir = /home/<user>/.coregui/custom\_services**

To make OLSR as the default routing protocol, user must remove the other routing protocol (such as OSPF, BGP) already enabled at the CORE node. The steps to select OLSR routing protocol at a node are as follows:

1. Right click on the CORE node and select ‘Services (Deprecated)’
1. Click on ‘maXentric’ under ‘Groups’, then click ‘OLSRdService’ under ‘Services’.
1. As shown in Figure 5, OLSRdService will appear under ‘Selected’ label. Then press ‘Save’. 
1. User can check the details of this service by clicking on ‘Configure’. The first option is Files under which you will see the ‘myOlsrd.conf’ and ‘myOlsrd.sh’ files that will be created. Under the Startup/Shutdown label, you will see two commands. ‘chmod +x myOlsrd.sh’ makes the file executable, and “./myOlsrd.sh” runs the file.
1. To disable other routing protocol at a CORE node, right click and select ‘Configure Services’. Under the ‘Selected’ label, you will see all the services selected for this node. Click on the unwanted service, then click ‘Remove’, followed by ‘Save’.

To check if a service is running on a CORE node once the CORE session starts, open the terminal at the CORE node and execute command ‘**top**’. You should see ‘myOlsrd’ service (see Figure 6 for reference). To see OLSR in action (i.e., get the 1- and 2-hop neighbors), run command ‘**./myOlsrd.sh**’. If you do not see the **myOlsrd** service running, check if the myOlsrd.conf and myOlsrd.sh files are in the CORE node’s local directory, and ensure that myOlsrd.sh is an executable file (use command **ls -la**  to see files and their permissions). If these files are not in the directory, copy them to the CORE node’s local directory and execute the commands given under the Startup/Shutdown label.

![](Aspose.Words.42dac42c-ff96-4ab6-9a84-e21f8560cfbf.006.png)

**Figure 5**. Selecting OLSRd service at CORE node n2.

![](Aspose.Words.42dac42c-ff96-4ab6-9a84-e21f8560cfbf.007.png) 

Figure 6. A 6-node network topology is shown on the left. Each node has OLSRd service enabled. When the CORE session starts, an executable myOlsrd.sh file is created at each node (see top center). The ‘top’ command shows the myOlsrd.sh service in the bottom center. The routes found at node n1 using OLSR is shown on the right.
