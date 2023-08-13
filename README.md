# gingrwrapp

A python client library and API for [gingr](gingrapp.com).

## Design

### Client
Automatically handles auth, session cookies, ratelimiting, timeouts for making requests to gingr.

```python
from gingrwrapp import Client

# 2 ways to create a client
client = Client(subdomain, username, password)
# GINGR_SUBDOMAIN, GINGR_USERNAME, GINGR_PASSWORD
client = Client.from_env()

# example usage
images = client.get_untagged_images()
```

### Sync
Uses the client library store historical and live data from gingr in a local database.
Think of it like a cache/proxy layer for gingr. This way any number of scripts or applications
can make use of gingr data without having to get it directly from gingr. `sync_local` is meant
to be run as a long runnig daemon.

```python
from datetime import date
from gingrwrapp import sync_local

# crawl gingr for all images, report cards, reservations since after date
# Also continuously poll gingr for new icons, untagged images, reservations
sync_local(after=date(2022, 1, 1))
```

### API
Django Rest Framework app that serves the local data from gingr. I want a REST API instead of
a python library so code using the data can be written in any language.

```python
from datetime import date
import requests

params = {
    "from_date": date(2023, 1, 1),
    "to_date": date(2023, 1, 4),
}

session = requests.Session()
session.headers.update("X-Api-Key", "<your api key>")

session.get("https://gingrwrapp.<your-domain>.com/api/reservations", params)
```


## Dev

All dev tasks can be accomplished with the `run.sh` script.

```sh
./run.sh install                  # configure venv and install deps
./run.sh install dev,doc          # optional dependencies
./run.sh tests                    # run full set of client tests
./run.sh test get_reservations    # run test for single func/method
./run.sh lint                     # ruff
./run.sh clean                    # rm files not source controlled
./run.sh build                    # whl and sdist
./run.sh docs                     # local pdoc
./run.sh help                     # print this helpful message
```

## TODO
- `Client.upload_image`
- `Client.tag_images`
- `sync_local`
- rest api
