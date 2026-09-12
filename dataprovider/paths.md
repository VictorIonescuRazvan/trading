# format
- date-time: dataprovider-severity(syslog number)-function: description

# severities
- /var/log/dataprovider/config.log
    - config: informational
- /var/log/dataprovider/requests.log
    - successful requests to tickerplant: informational
    - failed requests to tickerplant: critical
- /var/log/dataprovider/worker_queue.log
    - added element to the worker queue (aggregator.queue): informational
    - failed public API due to rate limit: error
    - failed public API due to other reason: critical
    - pushed data to tickerplant successfully: informational (not actual content, only confirmation)
    - failed to push data to tickerplant: critical

# logs
- /var/log/dataprovider/config.log
    - logs loaded configuration on app load
- /var/log/dataprovider/requests.log
    - logs requests made to the tickerplant
- /var/log/dataprovider/worker_queue.log
    - logs adding and popping from dataprovider worker queue and pushing data to tickerplant