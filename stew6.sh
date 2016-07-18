#!/bin/bash
exec 1>> /home/hamsterstew/disk.log 2>&1
times=$(date "+%d.%m-%H.%M.%S")

if ps ax | grep -v grep | grep 'autostew_back.py -i 6' > /dev/null
then
    echo "$times Backend 6 is running" 
else
	echo "$times Backend 6 was restarted"
     /usr/bin/python3 /storage/hamsterstew/live/autostew_back.py -i 6 & 
fi
