#!/bin/sh
WORKING_DIR=$(dirname $0)
cd $WORKING_DIR && curl -O http://geolite.maxmind.com/download/geoip/database/GeoLiteCountry/GeoIP.dat.gz && gunzip -f GeoIP.dat.gz
