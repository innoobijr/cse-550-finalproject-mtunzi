# Captive portal

The captive portal flask applicaion will run indepently in a seperate terminal. This submission form will currently take one of the two credentials, either one should work to test the capptive portal submission 

'''sh
email: firn@test.com
password: 1234 

or 

email: alice
password: passme

'''

These two are the only ones that are already registered to backend of the freeRADIUS server. 


Follow the following instruction to test the user login flow of the captive portal.

1. Start the freeRADIUS server by following the README files located on the root of the repo and inside its directory.

2. Comment out line #67 and insteads use line #68 under the 'auth.py' file inside the '../authenticator/' directory. On a terminal, start the authenticator to listen to the form submission.  

Note: assume that you have already activated your virtual environment

```sh
    python3 auth.py
```

3. In the current `capport` directory, runs

```sh
    ./run
```

4. Open a browser and direct to 'localhost' port 5000

5. Now the most exciting time! Fill in login credential (i.e. one of the two above). 


After you submit, you should be expecting a changes in messages in the freeRADIUS server terminal. This means that the credential has passed along from the capport app --> authenticator & freeRADIUS server.

However, as per time constraint, the communication back to capport from authenticator that will lead to redirection was not successful as we did not have enough time to integrte the actual controller. So the path backward from authenticator ---> capport will complains as an error in the terminal. 

