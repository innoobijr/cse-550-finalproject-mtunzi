# Authentication Process

## Instructions

In order to run the code, you'll need to install:
- `Python 3.6.1`
- `virtualenv`
- `pip`

Create an environment for *python3* by run the code below

``` 
virtualenv -p python3 env  
```



We we will then activate the environment by running

```
source env/bin/activate
```

Lastly, you will need additional libraries such as ```flask passlib```. These should be installed after you have activate the environment

``` 
pip install flask eventlet passlib radius json
```


Now you are good to go!

``` 
./run 
```