#!/bin/sh
# Poll web state of camera every 10 seconds and switch camera on/off if told to.
while [ 1 ]
do
    camState=$(curl http://www.mekeke.co.uk/picam/camState.txt)
    echo "Web state = " $camState
    if [ -n "$(pgrep pycam.py)" ]
    then
        # Pycam is running: Stop if told to.
        if [ "$camState" = "Stopping" ]
        then
            sudo /etc/init.d/pycam stop
        else
            # Else ensure web state is up to date.
            if [ "$camState" != "Running" ]
            then
                echo "Updating web state to Running"
                curl http://www.mekeke.co.uk/picam/setCamState.php?id=mypicam&state=Running
            fi
        fi
    else
        # Pycam is not running: Start if told to.
        if [ "$camState" = "Starting" ]
        then
            sudo /etc/init.d/pycam start
        else
            # Else ensure web state is up to date.
            if [ "$camState" != "Stopped" ]
            then
                echo "Updating web state to Stopped"
                curl http://www.mekeke.co.uk/picam/setCamState.php?id=mypicam&state=Stopped
            fi
        fi
    fi
    sleep 10
done
