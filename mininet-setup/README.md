# Mininet and freeRADIUS server set up

After you modify the neccessary IP address as stated in the README under the repository root, we will use the followings lines to start the freeRADIUS server in your local VM. 

'''sh
sudo su
/etc/init.d/freeradius stop
freeradius -X
'''

The freeRADIUS server supposely needs run im the backgound awaits for the authentication request from the authenticor. But for the teesting purposes, we do not need it to be running as `test.py` provides a stub message already. 