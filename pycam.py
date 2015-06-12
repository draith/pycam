#!/usr/bin/python

# original script by brainflakes, improved by pageauc, peewee2 and Kesthal
# www.raspberrypi.org/phpBB3/viewtopic.php?f=43&t=45235

# You need to install PIL to run this script
# type "sudo apt-get install python-imaging-tk" in an terminal window to do this

# import StringIO
import io
import os
import time
from datetime import datetime
from PIL import Image
import picamera

# Motion detection settings:
# Threshold          - how much a pixel has to change by to be marked as "changed"
# Sensitivity        - how many changed pixels before capturing an image, needs to be higher if noisy view
# ForceCapture       - whether to force an image to be captured every forceCaptureTime seconds, values True or False
# filepath           - location of folder to save photos
# filenamePrefix     - string that prefixes the file name for easier identification of files.
# diskSpaceToReserve - Delete oldest images to avoid filling disk. How much byte to keep free on disk.
# cameraSettings     - "" = no extra settings; "-hf" = Set horizontal flip of image; "-vf" = Set vertical flip; "-hf -vf" = both horizontal and vertical flip
threshold = 10
sensitivity = 100
forceCapture = True
forceCaptureTime = 60 * 60 # Once an hour
sendMailInterval = 60 * 60 # Once an hour
rampath = "/var/ram/"
filepath = "/home/pi/usbdrv/"
#filenamePrefix = "motion"
diskSpaceToReserve = 100 * 1024 * 1024 # Keep 100 mb free on disk
theCamera = False
movieJustTaken = False

# settings of the photos to save
saveWidth   = 1296
saveHeight  = 972
saveQuality = 15 # Set jpeg quality (0 to 100)
shutterSpeed = 80000 # 80 ms to start
# Test-Image settings
testWidth = 130
testHeight = 73

# this is the default setting, if the whole image should be scanned for changed pixel
testAreaCount = 1
testBorders = [ [[1,testWidth],[16,40]] ]  # [ [[start pixel on left side,end pixel on right side],[start pixel on top side,stop pixel on bottom side]] ]
# testBorders are NOT zero-based, the first pixel is 1 and the last pixel is testWith or testHeight

# with "testBorders", you can define areas, where the script should scan for changed pixel
# for example, if your picture looks like this:
#
#     ....XXXX
#     ........
#     ........
#
# "." is a street or a house, "X" are trees which move arround like crazy when the wind is blowing
# because of the wind in the trees, there will be taken photos all the time. to prevent this, your setting might look like this:

# testAreaCount = 2
# testBorders = [ [[1,50],[1,75]], [[51,100],[26,75]] ] # area y=1 to 25 not scanned in x=51 to 100

# even more complex example
# testAreaCount = 4
# testBorders = [ [[1,39],[1,75]], [[40,67],[43,75]], [[68,85],[48,75]], [[86,100],[41,75]] ]

# in debug mode, a file debug.bmp is written to disk with marked changed pixel an with marked border of scan-area
# debug mode should only be turned on while testing the parameters above
debugMode = True

# Capture a small test image (for motion detection)
def captureTestImage(width, height):
  imageData = io.BytesIO()
  theCamera.capture(imageData, format='jpeg', use_video_port=True, resize=(width, height))
  imageData.seek(0)
  im = Image.open(imageData)
  buffer = im.load()
  imageData.close()
  return im, buffer
    
# Get available disk space
def getFreeSpace():
    st = os.statvfs(filepath)
    du = st.f_bavail * st.f_frsize
    return du

# Keep free space above given level
def keepDiskSpaceFree(bytesToReserve):
    if (getFreeSpace() < bytesToReserve):
        for filename in sorted(os.listdir(filepath)):
            if filename.startswith(filenamePrefix) and filename.endswith(".h264"):
                os.remove(filepath + filename)
                print "Deleted %s%s to avoid filling disk" % (filepath,filename)
                if (getFreeSpace() > bytesToReserve):
                    return

# Start MP4 converter
os.system('/home/pi/pycam/converter.sh > /dev/null &');
# Start FTP sender
os.system('/home/pi/camera/ftper.sh 2> /dev/null &');

# Reset last capture time
lastCapture = 0
lastEmail = 0
# Initialize exposure variation monitoring
meanLevel = 75

with picamera.PiCamera() as camera:
    theCamera = camera
    # Set up the camera...
    camera.resolution = (1296, 730)
    camera.awb_mode = 'off'
    camera.awb_gains = (1.5, 1.2)
    camera.exposure_mode = 'sports'
    camera.framerate = 2
    camera.shutter_speed = shutterSpeed
    
    # Get first image
    image1, buffer1 = captureTestImage(testWidth, testHeight)
    
    while (True):
      # Get comparison image
      image2, buffer2 = captureTestImage(testWidth, testHeight)

      # Count changed pixels
      changedPixels = 0
      totalPixels = 0
      totalLevel = 0
      
      # in debug mode, save a bitmap-file with marked changed pixels and with visible testarea-borders
      if (debugMode): 
          debugimage = Image.new("RGB",(testWidth, testHeight))
          debugim = debugimage.load()

      # Scan test areas for changed pixels (motion) and mean light level.
      for z in xrange(0, testAreaCount): 
          for x in xrange(testBorders[z][0][0]-1, testBorders[z][0][1]): 
              for y in xrange(testBorders[z][1][0]-1, testBorders[z][1][1]):
                  if (debugMode):
                      debugim[x,y] = buffer2[x,y]
                      if ((x == testBorders[z][0][0]-1) or (x == testBorders[z][0][1]-1) or (y == testBorders[z][1][0]-1) or (y == testBorders[z][1][1]-1)):
                          debugim[x,y] = (0, 0, 255) # in debug mode, mark all border pixel to blue
                  
                  # Monitor exposure level
                  totalPixels += 1
                  totalLevel += buffer2[x,y][1]
                  
                  # Just check green channel as it's the highest quality channel
                  pixdiff = abs(buffer1[x,y][1] - buffer2[x,y][1])
                  
                  if pixdiff > threshold:
                      changedPixels += 1
                      if (debugMode):
                          r,g,b = debugim[x,y]
                          debugim[x,y] = (r, 255, b) # in debug mode, mark all changed pixel to green

      # Check and adjust exposure level
      lastMean = meanLevel
      meanLevel = totalLevel / totalPixels
      if meanLevel > 100 and shutterSpeed > 8000:
        shutterSpeed = max(shutterSpeed * 75 / meanLevel, 8000)
        camera.shutter_speed = shutterSpeed
        print "Mean level {0}; Exposure decreased to {1}ms".format(meanLevel,shutterSpeed/1000)
        image2, buffer2 = captureTestImage(testWidth, testHeight)
      elif meanLevel < 50 and shutterSpeed < 400000:
        shutterSpeed = min(shutterSpeed * 75 / meanLevel, 400000)
        camera.shutter_speed = shutterSpeed
        print "Mean level {0}; Exposure decreased to {1}ms".format(meanLevel,shutterSpeed/1000)
        image2, buffer2 = captureTestImage(testWidth, testHeight)
      elif movieJustTaken:
        # Make sure we have two captures to compare after the movie
        movieJustTaken = False
      elif changedPixels > sensitivity:
        # Motion detected: Record video...
        now = datetime.now()
        if (debugMode):
          filename = filepath + "debug-%02d_%02d_%02d.bmp" % (now.hour, now.minute, now.second)
          debugimage.save(filename) # save debug image as bmp
          print "%s saved, %s changed pixels" % (filename, changedPixels)
          print "Change in mean level = %d" % (meanLevel - lastMean)
        # Prevent light level changes from triggering motion detection..
        if abs(meanLevel - lastMean) < (threshold / 2):
          print('Motion detected: Recording video...................')
          filename = rampath + "motion-%04d%02d%02d-%02d_%02d_%02d.h264" % (now.year, now.month, now.day, now.hour, now.minute, now.second)
          theCamera.start_recording(filename, format='h264', quality=20)
          theCamera.wait_recording(10)
          theCamera.stop_recording()
          print('Done!')
          if time.time() - lastEmail > sendMailInterval:
            # Send alert email (see http://iqjar.com/jar/sending-emails-from-the-raspberry-pi/)
            os.system('/home/pi/pycam/mailer.sh')
            lastEmail = time.time()
          os.system("echo '{0}' >> /home/pi/pycam/converter.txt".format(filename))
            
          keepDiskSpaceFree(diskSpaceToReserve)
          movieJustTaken = True

      # Check force capture
      elif forceCapture:
        if time.time() - lastCapture > forceCaptureTime:
          # Forcing capture..
          print "Forcing capture..."
          now = datetime.now()
          #filename = filepath + "forced-%04d%02d%02d-%02d_%02d_%02d.jpg" % (now.year, now.month, now.day, now.hour, now.minute, now.second)
          filename = filepath + "snapshot.jpg"
          theCamera.capture(filename, format='jpeg', use_video_port=True)
          os.system("echo '{0}' >> /home/pi/camera/ftper.txt".format(filename))
          print "\nCaptured %s" % filename
          lastCapture = time.time()

      # Shift comparison buffers
      image1, buffer1 = image2, buffer2
