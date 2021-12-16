## SDN Captive Portal Application on Ryu Controller

You will need to install and run two VMs for this exercise. The first will be used to run the Ryu controller and the two SDN applications. The second will be use to run Mininet and also host the web server on the VM host. You will also host a web application ont he first VM for testing and redirection purposes.
**Configure the VM so that they are in the same network subnet. I have them configured on the same private network**

The Ryu Controller (VM1): 192.168.2.90
The Mininet + Capport machine (VM2): 192.168.2.99

# 1. Setting up the Ryu Controller
When you have installed and started up your first VM. You will need to install Ryu in the appropriate environment. Follow the follow directions

A. Start and virtual and install the packages in the requirements.txt file
B. Install Ryu: `pip install ryu`
C. Clone this directory into the VM

# 2. Setting up the Mininet test
 A. Download the Mininet VM from the Mininet website or run the following commands in your second VM:

##Option 1: Mininet VM Installation (easy, recommended)
VM installation is the easiest and most foolproof way of installing Mininet, so it’s what we recommend to start with.

Follow these steps for a VM install:

Download a Mininet VM Image from Mininet Releases.

Download and install a virtualization system. We recommend one of the following free options:

VirtualBox (GPL, macOS/Windows/Linux)
VMware Fusion (macOS)
VMware Workstation Player (Windows/Linux)

You can also use any of:

Qemu (free, GPL) for any platform
Microsoft Hyper-V (Windows)
KVM (free, GPL, Linux)
Optional, but recommended! Sign up for the mininet-discuss mailing list. This is the source for Mininet support and discussion with the friendly Mininet community. ;-) (And don’t forget the FAQ and documentation.)

Run through the VM Setup Notes to log in to the VM and customize it as desired.

Follow the Walkthrough to get familiar with Mininet commands and typical usage.

(In addition to the above resources, we’ve prepared a helpful Mininet FAQ as well as Documentation which you can refer to at any time! We recommend consulting them first if you have any questions.)

Once you’ve completed the Walkthrough, you should have a clear idea for what Mininet is and what you might use it for. The Introduction to Mininet explains the basics of Mininet’s Python API.

If you are interested in OpenFlow and Software-Defined Networking, you may wish to complete the OpenFlow tutorial as well. Good luck, and have fun!

##Option 2: Native Installation from Source

This option works well for local VM, remote EC2, and native installation. It assumes the starting point of a fresh Ubuntu, Debian, or (experimentally) Fedora installation.

We strongly recommend more recent Ubuntu or Debian releases, because they include newer versions of Open vSwitch. (Fedora also includes recent OvS releases.)

To install natively from source, first you need to get the source code:

`git clone git://github.com/mininet/mininet`

Note that the above git command will check out the latest and greatest Mininet (which we recommend!) If you want to run the last tagged/released version of Mininet - or any other version - you may check that version out explicitly:

```cd mininet
git tag  # list available versions
git checkout -b mininet-2.3.0 2.3.0  # or whatever version you wish to install
cd ..```

Once you have the source tree, the command to install Mininet is:

```mininet/util/install.sh [options]```

Typical install.sh options include:

* `-a`: install everything that is included in the Mininet VM, including dependencies like Open vSwitch as well the additions like the OpenFlow wireshark dissector and POX. By default these tools will be built in directories created in your home directory.
* `-nfv`: install Mininet, the OpenFlow reference switch, and Open vSwitch
* `-s mydir`: use this option before other options to place source/build trees in a specified directory rather than in your home directory.

So, you will probably wish to use one (and only one) of the following commands:

```To install everything (using your home directory): install.sh -a
To install everything (using another directory for build): install.sh -s mydir -a
To install Mininet + user switch + OvS (using your home dir): install.sh -nfv
To install Mininet + user switch + OvS (using another dir:) install.sh -s mydir -nfv```

You can find out about other useful options (e.g. installing the OpenFlow wireshark dissector, if it’s not already included in your version of wireshark) using

``install.sh -h```

After the installation has completed, test the basic Mininet functionality:

``sudo mn --switch ovsbr --test pingall``


# Run testbed

1. On the Controller (you can use TMUX or run in the background):
Start the stub webserver (make sure to start your virtual env): 
 ```	cd cse-550-finalproject-mtunzi/openflow/test-server
 	sudo python3 -m http.server 80 &
```

Start the stub authenticator (to pass authentication messages):
```    cd cse-550-finalproject-mtunzi/openflow/auth
       sudo python3 server.py &
```

Start the controller with the learning switch and redirection application: ``
* It is important that you are in the directory you cloned to gain access to the applications.
 ```    cd cse-550-finalproject-mtunzi/openflow/controller
 	ryu-manager --verbose ryu.app.simple_switch_13 tcpredirect.py
```

2. On the mininetVM start mininet with NAT
 Start the stub authenticator (to pass authentication messages):
  ```    cd cse-550-finalproject-mtunzi/openflow/host
  	sudo python3 server.py &
  ```
Start the captive portal
```    cd cse-550-finalproject-mtunzi/openflow/capport
       sudo python3 -m http.server 80
```

Start Mininet (change the IP to reflect the your controller IP)
 ```
 sudo mn --topo single,5 --mac --controller=remote,ip=192.168.2.90,port=6653 --nat
 mininet> xterm h1 s1
 ```


 Once you have these to set up, you can make curl requests from each of the host. After 30 seconds host 'h1' will have all of its rules removes and will have access to the internet while the others will not. The server.py file assume that your IPs are as listed above.

