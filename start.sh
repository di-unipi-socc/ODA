#!/bin/sh

if uname -m | grep -iq "arm"; then
    docker compose -f compose.yml -f arm.yml up -d
else
    docker compose -f compose.yml up -d
fi