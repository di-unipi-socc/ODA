#!/bin/sh

if uname -m | grep -iq "arm"; then
    docker compose -f compose.yml -f arm.yml down
else
    docker compose -f compose.yml down
fi