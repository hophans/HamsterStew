#!/bin/bash
exec 1>> /home/hamsterstew/disk.log 2>&1
times=$(date "+%d.%m-%H.%M.%S")

if ps ax | grep -v grep | grep 'runserver poop.dk:4040' > /dev/null
then
    echo "$times HamsterStew Front End is running" 
else
	echo "Backend 1 was restarted"
     /usr/bin/python3 /storage/hamsterstew/live/manage.py runserver poop.dk:4040 & > /dev/null

fi
