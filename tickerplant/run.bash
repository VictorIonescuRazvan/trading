#!/bin/bash
docker run \
	-p 5000:5000 \
	-v /etc/tickerplant:/etc/tickerplant:ro \
	-v /var/tickerplant:/var/tickerplant:rw \
	-v /var/log/tickerplant:/var/log/tickerplant:rw \
tickerplant:latest