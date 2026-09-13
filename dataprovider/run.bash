#!/bin/bash
docker run \
	-p 5000:5000 \
	-v /etc/dataprovider:/etc/dataprovider:ro \
	-v /var/log/dataprovider:/var/log/dataprovider:rw \
dataprovider:latest