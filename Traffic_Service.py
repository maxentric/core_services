from typing import Dict, List

from core.config import ConfigString, ConfigBool, Configuration
from core.configservice.base import ConfigService, ConfigServiceMode, ShadowDir

# Additional imports
from threading import Thread
from time import sleep
from datetime import datetime
from itertools import product
# To get node icon
from core.api.grpc import client
from core.gui.appconfig import LOCAL_ICONS_PATH # Icon directory
import os

# Traffic flow log storage directory
DEFAULT_SESSION_LOGS_DIR = f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/.coregui/SessionLogs/"

# Service and Group names
GroupName = "maXentric"
ServerServiceName = "FlowDestination"
ClientServiceName = "FlowSource"


#-------------------------------------
# Common functions
#-------------------------------------

# Create a directory if it does not exist
def makeDirectory(directoryName):
    try:
        if not os.path.exists(directoryName):
            os.makedirs(directoryName)
        #print(f"Directory {directoryName} exists!")
        return True
    except:
        print(f"***Could not create the directory: {directoryName}")
        return False
    
# Update node's icon
def nodeIconUpdate (node, icon):
    # Create grpc client and connect
    core = client.CoreGrpcClient()
    core.connect()
    _ = core.edit_node(node.session.id, node.id, str(LOCAL_ICONS_PATH)+"/"+icon)
    #print(f"***New node icon for node {node.name} is {node.icon}.")        
    return

# Get initial node location
def getInitialNodeLocations(self):
    InitialNodeLocations = {}
    for thisNode in self.node.session.nodes.values():
        if (("emane" not in thisNode.name) & ("CtrlNet" not in thisNode.name) & ("PtpNet" not in thisNode.name)):
            InitialNodeLocations[thisNode.name] = thisNode.getposition()
    print("\n***Node: ", self.node.name, "Initial GPS locations: ", InitialNodeLocations,"\n")
    return InitialNodeLocations

# Returns True when any node moves to indicate that initial setup is done
def isInitialSetupDone(node,InitialNodeLocations):
    initializationDone = False
    #print("***Node location: ",InitialNodeLocations)
                        
    for thisNode in node.session.nodes.values():
        if (thisNode.name in InitialNodeLocations):

            # Has the location changed?
            old_loc = InitialNodeLocations[thisNode.name]
            new_loc = thisNode.getposition()
            #print("Old loc: ",old_loc, "new loc:",new_loc)

            # Used 1.0 below as threshold to avoid rounding error. Potential cause: float to int conversion.
            if(((old_loc[0]-new_loc[0])**2 + (old_loc[1] -new_loc[1])**2)**0.5 > 1.0):
                print(f"\n***At node: {node.name}. Node {thisNode.name} has moved! Old location: {old_loc} New location: {new_loc}\n")
                initializationDone = True
                break

    return initializationDone

# Returns True is a node is serving at least one traffic flow. Ow, moves the files to user-defined directory.
def stillServingTraffic(node,database,nodeType,SESSION_LOGS_DIR):
    
    servingTraffic = False

    # If CORE session is stopped while service is running, pycore.1 folder does not exist. Avoid the exception.
    try:
        tmpFile = f"/tmp/pycore.1/{node.name}.conf/portCheck.log"
        node.cmd(f"ps aux > {tmpFile}", wait=True, shell=True); # Need shell and wait True
                    
        # Logic: A port becomes free when the traffic completes.
        with open(tmpFile) as f_:
            for line,eachSrc in product(f_,database):
                if (database[eachSrc]["Command"] in line):
                    #print("\n\n Service is still running:",line,"\n\n")
                    servingTraffic = True
                    break

        # Delete the file
        node.cmd(f"rm {tmpFile}", wait=False, shell=False)

        # All traffic flows are complete
        if (not servingTraffic):
            print(f"\n***All traffic flows are complete at {nodeType} node: {node.name}\n")
            
            # Change the node icon
            nodeIconUpdate(node,"document-save.gif")

            # Move the files
            for eachSrc in database:
                node.cmd(f"cp {database[eachSrc]['Filename']} {SESSION_LOGS_DIR}", wait=False, shell=False)
            print(f"\n***{nodeType} files have been moved to {SESSION_LOGS_DIR}\n")

    except:
        print(f"\n***Cannot check port. Abort service at node: {node.name}! \nPotential reason: CORE session is stopped.\n")
        servingTraffic = False
        
    return servingTraffic


#----------------------------------------------------------------------#
#                 Server service (destination node)                    #
#----------------------------------------------------------------------#

# class that subclasses ConfigService
class ServerService(ConfigService):
    # unique name for your service within CORE
    name: str = ServerServiceName
    # the group your service is associated with, used for display in GUI
    group: str = GroupName
    # directories that the service should shadow mount, hiding the system directory
    directories: List[str] = [] 
    # files that this service should generate, defaults to nodes home directory
    # or can provide an absolute path to a mounted directory
    files: List[str] = []
    # executables that should exist on path, that this service depends on
    executables: List[str] = []
    # other services that this service depends on, can be used to define service start order
    dependencies: List[str] = []
    # commands to run to start this service
    startup: List[str] = []
    # commands to run to validate this service
    validate: List[str] = []
    # commands to run to stop this service
    shutdown: List[str] = []
    # validation mode, blocking, non-blocking, and timer
    validation_mode: ConfigServiceMode = ConfigServiceMode.BLOCKING
    
    # configurable values that this service can use, for file generation
    default_configs: List[Configuration] = [
        ConfigString(id="Sources", 
                     default="*", 
                     label="Source Nodes (Use * to consider all nodes with FlowSource service. Or specify nodes as, <n2,n3,n4>)"),
        ConfigString(id="ServiceStartOption",
                     default="Any node moves",
                     label="When to start the service",
                     options=["Core session starts","Any node moves"]),
        ConfigString(id="LogDirectory",
                     default=DEFAULT_SESSION_LOGS_DIR,
                     label="Directory where the files will be moved once traffic flow completes"),
    ]
    # Check 'man iperf3' to add more parameters.
    
    # sets of values to set for the configuration defined above, can be used to
    # provide convenient sets of values to typically use
    modes: Dict[str, Dict[str, str]] = {} #e.g., {"mode1": {"Sources": "n1", "DataRate": "0.5Mbits", "SimulationDuration": "50"},}
    
    # defines directories that this service can help shadow within a node
    shadow_directories: List[ShadowDir] = []

       
    # Achieves following tasks:
    # 1. Waits for user initialization, 
    # 2. Gets user inputs for traffic setup, 
    # 3. Starts traffic flow, 
    # 4. Moves files upon completion.
    def traffic_worker (self,node,InitialNodeLocations):
        
        # Current time
        now = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

        # Get parameters to setup traffic
        config = node.config_services.get(self.name).render_config(); #print("Config: ",config)

        # Create directory to store log files
        # a. User-specified directory
        if (makeDirectory(config["LogDirectory"])):
            # Update the log directory
            SESSION_LOGS_DIR = config["LogDirectory"]
        # b. Create directory (hard-coded)
        else:
            makeDirectory(DEFAULT_SESSION_LOGS_DIR)
            SESSION_LOGS_DIR = DEFAULT_SESSION_LOGS_DIR
        print("***Session Log dir:",SESSION_LOGS_DIR)

        # Decide whether to wait until the initial setup is done or right away, to start the service
        if ("Any node moves" in config["ServiceStartOption"]):
        
            #--------------------------------------------
            # Wait until user initialization is complete
            # (i.e., wait until any node moves)
            #--------------------------------------------

            while (not isInitialSetupDone(node,InitialNodeLocations)):
                sleep(1.0)
            # Initialization done!

        #else:
        #    print("***Skipping the initialization setup!")
        
        # Change the node icon 
        nodeIconUpdate(node,"alert.png")


        #--------------------------------
        # Set up traffic flows
        #--------------------------------

        # Find potential source nodes
        sources_str = config["Sources"]; sources = {}
        for thisNode in node.session.nodes.values():
            if ((thisNode.name is not node.name) & (thisNode.name in InitialNodeLocations)):
                
                # If default setting (i.e., *), consider all nodes with Source service enabled. Otherwise, consider user-defined nodes.
                if (('*' in sources_str) or (('*' not in sources_str) & (thisNode.name in sources_str.split(",")))):
                    
                    try:
                        for serviceName in thisNode.config_services:
                            if ClientServiceName in str(serviceName):
                                print("\n***Source service is enabled at node: ", thisNode.name,"\n")                            

                                # Create iperf3 command
                                port = 5200+int(thisNode.name[1:])
                                FILENAME = f"/tmp/pycore.1/{node.name}.conf/Server_{node.name}_Client_{thisNode.name}_Port_{port}_Time_{now}.txt"
                                cmd = f"iperf3 --server --port {port} --one-off --logfile {FILENAME}"
                                sources[thisNode.name] = {"Port":port,"Filename":FILENAME,"Command": cmd}

                                
                                #-------------------------------
                                # Start traffic (in background)
                                #-------------------------------

                                node.cmd(f"{cmd}", wait=False, shell=False)
                                break # Check next node
                    finally:
                        # Skip those nodes which do not have config services, such as emane, wlan, etc.
                        continue
        
        
        #--------------------------------------------------
        # Change node icon when all traffic flows complete
        #--------------------------------------------------
        
        # Wait until all traffic flows complete
        if (len(sources)):
            while stillServingTraffic(node,sources,"Destination",SESSION_LOGS_DIR):
                sleep(5.0)
            #print("\n***All traffic flows are complete at destination node:",node.name,"\n")
            
        # No traffic flow was set up. Change the node icon to the original
        else:
            nodeIconUpdate(node,"mdr.png")
            print("\n***No source node found for destination node:",node.name)
        return
        

    def run_startup(self, wait:bool) -> None:
        #print("***In run_startup. wait:",wait)
        super().run_startup(wait)

        # Create a trigger to setup and track traffic flow
        t = Thread(target=self.traffic_worker, args=(self.node,getInitialNodeLocations(self)))
        t.start()


#----------------------------------------------------------------------#
#                   Client service (source node)                       #
#----------------------------------------------------------------------#

# class that subclasses ConfigService
class ClientService(ConfigService):
    # unique name for your service within CORE
    name: str = ClientServiceName
    # the group your service is associated with, used for display in GUI
    group: str = GroupName
    # directories that the service should shadow mount, hiding the system directory
    directories: List[str] = [] 
    # files that this service should generate, defaults to nodes home directory
    # or can provide an absolute path to a mounted directory
    files: List[str] = []
    # executables that should exist on path, that this service depends on
    executables: List[str] = []
    # other services that this service depends on, can be used to define service start order
    dependencies: List[str] = []
    # commands to run to start this service
    startup: List[str] = []
    # commands to run to validate this service
    validate: List[str] = []
    # commands to run to stop this service
    shutdown: List[str] = []
    # validation mode, blocking, non-blocking, and timer
    validation_mode: ConfigServiceMode = ConfigServiceMode.BLOCKING
    
    # configurable values that this service can use, for file generation
    default_configs: List[Configuration] = [
        ConfigString(id="Destinations", 
                     default="*", 
                     label="Destination Node(s) (* to consider all nodes with FlowDestination service. Ow specify nodes as, <n2,n3,n4>)"),
        ConfigString(id="DataRate", 
                     default="*", 
                     label="Data Rate (Use '*' for default, which corresponds to 1 Mbps for UDP and unlimited for TCP/SCTP. Usage <rate[K|M|G|T]bits>)"),
        ConfigString(id="LogDirectory",
                     default=DEFAULT_SESSION_LOGS_DIR,
                     label="Directory where the files will be moved once traffic flow completes"),
        ConfigString(id="ServiceStartOption",
                     default="Any node moves",
                     label="When to start the service",
                     options=["Core session starts","Any node moves"]),
        ConfigString(id="TransportProtocol", 
                     default="TCP", 
                     label="Transport Protocol",
                     options=["TCP","UDP","SCTP"]),
        ConfigString(id="Omit", 
                     default="0", 
                     label="Omit initial duration (in second)"),
        ConfigString(id="Interval", 
                     default="1", 
                     label="Pause Time (in second) between periodic throughput reports. Use '0' to disable."),
        ConfigString(id="TrafficGenerationOption", 
                     default="Simulation Duration", 
                     label="Traffic Generation Option",
                     options=["Simulation Duration","No. of Blocks","No. of Bytes"]),
        ConfigString(id="SimulationDuration", 
                     default="100", 
                     label="Simulation Duration (in second)"),
        ConfigString(id="TotalBlocks", 
                     default="0", 
                     label="No. of Blocks (in packets)"),
        ConfigString(id="TotalBytes", 
                     default="1G", 
                     label="No. of Bytes. Use [KMGT] for KB/MB/GB/TB"),
        ConfigString(id="Format", 
                     default="*", 
                     label="Format. Use '*' for default.",
                     options=["*","Kbits","Mbits","Gbits","Tbits"]),
        ConfigString(id="BufferLength", 
                     default="*", 
                     label="Buffer Length. Use '*' for default, which corresponds to 128 KB for TCP, 1460 MB for UDP, and 64 KB for SCTP. Usage <val[KMGT]>."),
    ]
    # Check 'man iperf3' for more details.


    # sets of values to set for the configuration defined above, can be used to
    # provide convenient sets of values to typically use
    modes: Dict[str, Dict[str, str]] = {} #e.g., {"mode1": {"Sources": "n1", "DataRate": "0.5Mbits", "SimulationDuration": "50"},}
    
    # defines directories that this service can help shadow within a node
    shadow_directories: List[ShadowDir] = []
    

    # Achieves following tasks:
    # 1. Waits for user initialization, 
    # 2. Gets user inputs for traffic setup, 
    # 3. Starts traffic flow, 
    # 4. Moves files upon completion.
    def traffic_worker (self,node,InitialNodeLocations):
        
        # Current time
        now = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

        # Get parameters for traffic setup
        config = node.config_services.get(self.name).render_config(); #print("Config: ",config)

        # Create directory to store log files
        # a. User-specified directory
        if (makeDirectory(config["LogDirectory"])):
            # Update the log directory
            SESSION_LOGS_DIR = config["LogDirectory"]
        # b. Create directory (hard-coded)
        else:
            makeDirectory(DEFAULT_SESSION_LOGS_DIR)
            SESSION_LOGS_DIR = DEFAULT_SESSION_LOGS_DIR
        print("***Session Log dir:",SESSION_LOGS_DIR)
        
        # Decide whether to wait until the initial setup is done or right away, to start the service
        if ("Any node moves" in config["ServiceStartOption"]):
        
            #--------------------------------------------
            # Wait until user initialization is complete
            # (i.e., wait until any node moves)
            #--------------------------------------------

            while (not isInitialSetupDone(node,InitialNodeLocations)):
                sleep(1.0)
            # Initialization done!
        
        #else:
        #    print("***Skipping the initialization setup!")
        
        # Change the node icon 
        nodeIconUpdate(node,"alert.png")

        # Need additional wait at source node to allow destination (server) node to start listening on the ports
        sleep(10.0)


        #--------------------------------
        # Set up traffic flows
        #--------------------------------

        # Get port
        port = 5200+int(node.name[1:])
        extraArgs = f"--port {port}"
        
        # Buffer length
        bufferSize = config["BufferLength"]
        if '*' not in bufferSize:
            extraArgs += f" --length {bufferSize}"

        # Data rate
        dataRate = config["DataRate"]
        if '*' not in dataRate:
            extraArgs += f" --bitrate {dataRate}"
        
        # Format
        format = config["Format"]
        if '*' not in format:
            extraArgs += f" --format {format}"

        # Interval
        extraArgs += f" --interval {config['Interval']}"

        # Omit duration
        extraArgs += f" --omit {config['Omit']}"

        # Traffic generation option
        trafficOption = config["TrafficGenerationOption"]
        match trafficOption:
            case "No. of Blocks":
                extraArgs += f" --blockcount {config['TotalBlocks']}"
            case "No. of Bytes":
                extraArgs += f" --bytes {config['TotalBytes']}"
            case _:
                # Default is simulation duration
                extraArgs += f" --time {config['SimulationDuration']}"

        # Transport layer protocol
        transportProtocol = config["TransportProtocol"]
        if "UDP" == transportProtocol:
            extraArgs += f" --udp"
        elif "SCTP" == transportProtocol:
            extraArgs += f" --sctp"
        # Default is TCP        
        
        print("ExtraArgs:",extraArgs)

        
        # Find potential destination nodes
        dest_str = config["Destinations"]; destinations = {}
        for thisNode in node.session.nodes.values():
            if ((thisNode.name is not node.name) & (thisNode.name in InitialNodeLocations)):

                # If default setting (i.e., *), consider all nodes with Destination service enabled. Otherwise, consider user-defined nodes.
                if (('*' in dest_str) or (('*' not in dest_str) & (thisNode.name in dest_str.split(",")))):
                    
                    try:
                        for serviceName in thisNode.config_services:
                            if ServerServiceName in str(serviceName):
                                print("\n***Destination service is enabled at node: ", thisNode.name,"\n")                            

                                # Create iperf3 command
                                IpAddress = str((thisNode.get_ifaces()[0]).get_ip4 ().ip)
                                FILENAME = f"/tmp/pycore.1/{node.name}.conf/Client_{node.name}_Server_{thisNode.name}_Port_{port}_Time_{now}.json"
                                cmd = f"iperf3 --client {IpAddress} {extraArgs} --logfile {FILENAME} -J --get-server-output"
                                destinations[thisNode.name] = {"Port":port,"IpAddress":IpAddress,"Filename":FILENAME,"Command": cmd}

                                #-------------------------------
                                # Start traffic (in background)
                                #-------------------------------

                                node.cmd(f"{cmd}", wait=False, shell=False)
                                sleep(0.001)   # as precaution, use delay between multiple traffic flows 
                                break # Check next node
                    finally:
                        # Skip those nodes which do not have config services, such as emane, wlan, etc.
                        continue
        
        
        #--------------------------------------------------
        # Change node icon when all traffic flows complete
        #--------------------------------------------------
        
        # Wait until traffic flow continues
        if (len(destinations)):
            while stillServingTraffic(node,destinations,"Source",SESSION_LOGS_DIR):
                sleep(5.0)            
            #print("\n***All traffic flows are complete at source node:",node.name,"\n")
            
        # No traffic flow was set up. Change the node icon to the original
        else:
            nodeIconUpdate(node,"mdr.png")
            print("\n***No destination node found for source node:",node.name,"\n")
        return
    

    def run_startup(self, wait:bool) -> None:
        #print("***In run_startup. wait:",wait)
        super().run_startup(wait)
        
        # Create a trigger to setup and track traffic flow
        t = Thread(target=self.traffic_worker, args=(self.node,getInitialNodeLocations(self)))
        t.start()
