#!/bin/sh
set -eu
set -a
. /config/demo.env
set +a
exec java -jar /app/app.jar
