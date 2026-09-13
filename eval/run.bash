#!/bin/bash
docker run \
	-p 5001:5001 \
	-v /etc/eval:/etc/eval:ro \
	-v /var/log/eval:/var/log/eval:rw \
	-d \
eval:latest
