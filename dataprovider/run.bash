#!/bin/bash
docker run \
	-v /etc/dataprovider:/etc/dataprovider:ro \
	-v /var/log/dataprovider:/var/log/dataprovider:rw \
	-d \
dataprovider:latest
