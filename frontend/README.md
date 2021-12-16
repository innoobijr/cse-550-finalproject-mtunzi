# Authentication Process

## Installations

In order to run the code, you'll need to install:
- `Python 3.6.1`
- `virtualenv`
- `pip`

Create an environment for *python3* by run the code below

```sh 
virtualenv -p python3 env  
```

We we will then activate the environment by running

```sh
source env/bin/activate
```

Lastly, you will need additional libraries such as ```flask passlib```.
These should be installed after you have activate the environment

```sh 
pip install flask eventlet passlib radius
```

## Instructions

Next, before we start testing the authentication process. You must have the freeradius server running on
the local VM with all the neccessary modifications listed on README at the root of this repo. 

You are required to have 2 different terminals running the commands requentially one after another. 
Please also make sure the directory that you are under the directory where you have installed
the virtual environment above (i.e should be under `frontend` directory).


Terminal #1 for the authenticator, to open the non-blocking socket. You will run 

```sh
cd authenticator
python3 auth.py
```

Most importantly, terminal #2 is for testing the communication flow. 
The major tasks of the `test.py` will be 

1. Making a fake submission and composing a stub message to send to the authenticator 
as if it comes from the actual captive portal. This message will use to authenticate the
user on the freeRADIUS server.
2. Then it listens for the response from the authenticator for the
authentication result. 
3. Sends a stub message back to the authenticator that the flow rule has been adjusted based on the authentication result previusly

After the communication complete, the user supposely will be unblocked from the waiting page and redirected to dashboard page. But in the current implemenation, we expect to see the success message as a reponse. 

Please execute the following line in the terminal #2

```
python3 test.py
```