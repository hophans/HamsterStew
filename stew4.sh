#!/bin/bash
exec 1>> /home/hamsterstew/disk.log 2>&1
times=$(date "+%d.%m-%H.%M.%S")

if ps ax | grep -v grep | grep 'autostew_back.py -i 4' > /dev/null
then
    echo "$times Backend 4 is running" 
else
	echo "$times Backend 4 was restarted"
     /usr/bin/python3 /storage/hamsterstew/live/autostew_back.py -i 4 & 
fi
