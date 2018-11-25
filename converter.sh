#!/bin/sh
PROCS=$(ps -e | grep -o 'converter.sh' | wc -l)
if [ $PROCS -gt 2 ]
then
	echo 'converter.sh already running'
else
	# First, empty our queue of files to upload
	echo -n '' > /home/pi/pycam/converter.txt
	# Then monitor and process any files added to the list
	tail -f /home/pi/pycam/converter.txt | while read rampath
	do
		# Convert .h264 file in ram to .mp4 file in usb drive
		base=$(basename $rampath .h264)
		dest=/home/pi/usbdrv/$base.mp4
		MP4Box -add $rampath $dest -fps 8
		# Queue mp4 file for upload by FTP
		echo $dest >> /home/pi/camera/ftper.txt
		# delete .h264 file
		rm $rampath
	done
fi
