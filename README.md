# gingrwrapp

A python client library for [gingr](https://gingrapp.com) that automatically handles auth,
session cookies, ratelimiting and timeouts when making requests to gingr.

### Usage

```python
from gingrwrapp import Client, GingrClientError

# 2 ways to create a client
client = Client(subdomain, username, password)
# GINGR_SUBDOMAIN, GINGR_USERNAME, GINGR_PASSWORD
client = Client.from_env()

# example usage
try:
    images = client.get_untagged_images()
except GingrClientError:
    # handle the error ...
```

## Dev

All dev tasks can be accomplished with the `run.sh` script.

```sh
./run.sh install                  # configure venv and install deps
./run.sh install dev,doc          # optional dependencies
./run.sh tests                    # run full set of client tests
./run.sh test get_reservations    # run test for single func/method
./run.sh lint                     # ruff and mypy
./run.sh clean                    # rm files not source controlled
./run.sh build                    # whl and sdist
./run.sh docs                     # local pdoc server
./run.sh help                     # print this helpful message
```

## TODO

- Figure out google url signing for `Client.upload_image`
- Figure out what format postdata needs to be in for `Client.tag_images`
- Docs need a lot of work
    + Especially some of the response_objects like `Icons`
- Better Exceptions
    + `BadLoginCredentials`, `Timeout`, `UnexpectedResponse`
