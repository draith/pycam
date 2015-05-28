#!/usr/bin/python

# original script by brainflakes, improved by pageauc, peewee2 and Kesthal
# www.raspberrypi.org/phpBB3/viewtopic.php?f=43&t=45235

# You need to install PIL to run this script
# type "sudo apt-get install python-imaging-tk" in an terminal window to do this

# import StringIO
import io
import subprocess
import os
import time
from datetime import datetime
from PIL import Image
import picamera
from fractions import Fraction

# Motion detection settings:
# Threshold          - how much a pixel has to change by to be marked as "changed"
# Sensitivity        - how many changed pixels before capturing an image, needs to be higher if noisy view
# ForceCapture       - whether to force an image to be captured every forceCaptureTime seconds, values True or False
# filepath           - location of folder to save photos
# filenamePrefix     - string that prefixes the file name for easier identification of files.
# diskSpaceToReserve - Delete oldest images to avoid filling disk. How much byte to keep free on disk.
# cameraSettings     - "" = no extra settings; "-hf" = Set horizontal flip of image; "-vf" = Set vertical flip; "-hf -vf" = both horizontal and vertical flip
threshold = 10
sensitivity = 20
forceCapture = True
forceCaptureTime = 60 * 60 # Once an hour
sendMailInterval = 60 * 60 # Once an hour
filepath = "/home/pi/usbdrv"
#filenamePrefix = "motion"
diskSpaceToReserve = 100 * 1024 * 1024 # Keep 100 mb free on disk
theCamera = False

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
testBorders = [ [[1,testWidth],[23,47]] ]  # [ [[start pixel on left side,end pixel on right side],[start pixel on top side,stop pixel on bottom side]] ]
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
testImageCaptures = 0
motionDetected = False

def filenamePrefix():
  if (motionDetected):
    return 'motion'
  else:
    return 'forced'
    
# Capture a small test image (for motion detection)
def captureTestImage(width, height):
  global testImageCaptures
  imageData = io.BytesIO()
  theCamera.capture(imageData, format='jpeg', use_video_port=True, resize=(width, height))
  testImageCaptures += 1
  imageData.seek(0)
  im = Image.open(imageData)
  buffer = im.load()
  imageData.close()
  return im, buffer

# Save a full size image to disk
def saveImage(width, height, quality, diskSpaceToReserve):
    #keepDiskSpaceFree(diskSpaceToReserve)
    now = datetime.now()
    if motionDetected:
      start = time.time()
      filename = filepath + "/%s-%04d%02d%02d-%02d_%02d_%02d%s.jpg" % (filenamePrefix(), now.year, now.month, now.day, now.hour, now.minute, now.second, "%s")
      camera.capture_sequence((
        filename % i
        for i in range(10)
        ), use_video_port=True) # 3fps vs 0.5fps in non-video mode
      print('Captured 10 images at %.2ffps' % (10 / (time.time() - start)))
    else:
      filename = filepath + "/%s-%04d%02d%02d-%02d_%02d_%02d%1d.jpg" % (filenamePrefix(), now.year, now.month, now.day, now.hour, now.minute, now.second, now.microsecond/100000)
      theCamera.capture(filename, format='jpeg', use_video_port=True)
      os.system("echo '{0}' >> /home/pi/camera/ftper.txt".format(filename))
    print "\nCaptured %s" % filename
    
# Keep free space above given level
def keepDiskSpaceFree(bytesToReserve):
    if (getFreeSpace() < bytesToReserve):
        for filename in sorted(os.listdir(filepath + "/")):
            if filename.startswith(filenamePrefix) and filename.endswith(".jpg"):
                os.remove(filepath + "/" + filename)
                print "Deleted %s/%s to avoid filling disk" % (filepath,filename)
                if (getFreeSpace() > bytesToReserve):
                    return

# Get available disk space
def getFreeSpace():
    st = os.statvfs(filepath + "/")
    du = st.f_bavail * st.f_frsize
    return du

# Start FTP sender
# os.system('/home/pi/camera/ftper.sh &');

# Reset last capture time
lastCapture = 0
lastEmail = 0

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
      takePicture = False
      motionDetected = False
      totalPixels = 0
      totalLevel = 0
      

      if (debugMode): # in debug mode, save a bitmap-file with marked changed pixels and with visible testarea-borders
          debugimage = Image.new("RGB",(testWidth, testHeight))
          debugim = debugimage.load()

      for z in xrange(0, testAreaCount): # = xrange(0,1) with default-values = z will only have the value of 0 = only one scan-area = whole picture
          for x in xrange(testBorders[z][0][0]-1, testBorders[z][0][1]): # = xrange(0,100) with default-values
              for y in xrange(testBorders[z][1][0]-1, testBorders[z][1][1]):   # = xrange(0,75) with default-values; testBorders are NOT zero-based, buffer1[x,y] are zero-based (0,0 is top left of image, testWidth-1,testHeight-1 is botton right)
                  if (debugMode):
                      debugim[x,y] = buffer2[x,y]
                      if ((x == testBorders[z][0][0]-1) or (x == testBorders[z][0][1]-1) or (y == testBorders[z][1][0]-1) or (y == testBorders[z][1][1]-1)):
                          # print "Border %s %s" % (x,y)
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

      # Check force capture
      if forceCapture:
        if time.time() - lastCapture > forceCaptureTime:
          # Forcing capture..
          print "Forcing capture..."
          takePicture = True
          lastCapture = time.time()
      # Check and adjust exposure level
      meanLevel = totalLevel / totalPixels
      if meanLevel > 100 and shutterSpeed > 8000:
        shutterSpeed = max(shutterSpeed * 75 / meanLevel, 8000)
        camera.shutter_speed = shutterSpeed
        print "Exposure decreased to {}ms".format(shutterSpeed/1000)
        testImageCaptures = 0
        image2, buffer2 = captureTestImage(testWidth, testHeight)
      elif meanLevel < 50 and shutterSpeed < 400000:
        shutterSpeed = min(shutterSpeed * 75 / meanLevel, 400000)
        camera.shutter_speed = shutterSpeed
        print "Exposure increased to {}ms".format(shutterSpeed/1000)
        print "Camera shutter speed = {}".format(camera.shutter_speed)
        testImageCaptures = 0
        image2, buffer2 = captureTestImage(testWidth, testHeight)
      elif (changedPixels > sensitivity and testImageCaptures > 3):
        motionDetected = True
        takePicture = True # will shoot the photo later
        if (debugMode):
          now = datetime.now()
          filename = filepath + "/debug-%02d_%02d_%02d.bmp" % (now.hour, now.minute, now.second)
          debugimage.save(filename) # save debug image as bmp
          print "%s saved, %s changed pixels, captures = %s" % (filename, changedPixels, testImageCaptures)
          print "Mean level = {}".format(meanLevel)
          
      if takePicture:
          saveImage(saveWidth, saveHeight, saveQuality, diskSpaceToReserve)
          if motionDetected and time.time() - lastEmail > sendMailInterval:
              # Send alert email (see http://iqjar.com/jar/sending-emails-from-the-raspberry-pi/)
              os.system('/home/pi/pycam/mailer.sh')
              lastEmail = time.time()

      # Shift comparison buffers
      image1, buffer1 = image2, buffer2
