#!/usr/bin/python

import rospy
from datetime import datetime

#from nmea_msgs.msg import Sentence
from rtcm_msgs.msg import Message

from base64 import b64encode
from threading import Thread

from httplib import HTTPConnection
from httplib import IncompleteRead

import socket

''' This is to fix the IncompleteRead error
    http://bobrochel.blogspot.com/2010/11/bad-servers-chunked-encoding-and.html'''
import httplib
def patch_http_response_read(func):
    def inner(*args):
        try:
            return func(*args)
        except IncompleteRead, e:
            return e.partial
    return inner
httplib.HTTPResponse.read = patch_http_response_read(httplib.HTTPResponse.read)

REMOTE_SERVER = "1.1.1.1"
def is_connected(hostname):
    try:
        s = socket.create_connection((hostname, 53))
        s.close()
        return True
    except:
        pass
    return False

class ntripconnect(Thread):
    def __init__(self, ntc):
        super(ntripconnect, self).__init__()
        self.ntc = ntc
        self.stop = False

    def run(self):
        headers = {
            'Ntrip-Version': 'Ntrip/2.0',
            'User-Agent': 'NTRIP ntrip_ros',
            'Connection': 'close',
            'Authorization': 'Basic ' + b64encode(self.ntc.ntrip_user + ':' + str(self.ntc.ntrip_pass))
        }
        ''' Waits until an internet connection is established '''
        connected = False
        while not connected:
            if is_connected(REMOTE_SERVER):
                rospy.loginfo("Connected to internet")
                connected = True
            else:
                rospy.logwarn("No internet connection")
                rospy.sleep(5)
        connection = HTTPConnection(self.ntc.ntrip_server,timeout=10)
        connection.request('GET', '/'+self.ntc.ntrip_stream, self.ntc.nmea_gga, headers)
        response = connection.getresponse()
        if response.status != 200: raise Exception("blah")
        buf = ""
        rmsg = Message()
        restart_count = 0
        reconnect = False
        while not self.stop:
            self.ntc.is_new_stream = rospy.get_param('~is_new_stream')
            
            '''
            data = response.read(100)
            pos = data.find('\r\n')
            if pos != -1:
                rmsg.message = buf + data[:pos]
                rmsg.header.seq += 1
                rmsg.header.stamp = rospy.get_rostime()
                buf = data[pos+2:]
                self.ntc.pub.publish(rmsg)
            else: buf += data
            '''

            ''' This now separates individual RTCM messages and publishes each one on the same topic '''
            try:
                data = response.read(1)
            except (socket.timeout) as e:
                reconnect = is_connected(REMOTE_SERVER)
                rospy.logwarn(e) 
            except:
                pass

            if len(data) != 0 and not(self.ntc.is_new_stream) and not(reconnect):
                if ord(data[0]) == 211:
                    buf += data
                    data = response.read(2)
                    buf += data
                    cnt = ord(data[0]) * 256 + ord(data[1])
                    data = response.read(2)
                    buf += data
                    typ = (ord(data[0]) * 256 + ord(data[1])) / 16
                    print (str(datetime.now()), cnt, typ)
                    cnt = cnt + 1
                    for x in range(cnt):
                        data = response.read(1)
                        buf += data
                    rmsg.message = buf
                    rmsg.header.seq += 1
                    rmsg.header.stamp = rospy.get_rostime()
                    self.ntc.pub.publish(rmsg)
                    buf = ""
                else: print (data)
            else:
                if self.ntc.is_new_stream:
                    self.ntc.ntrip_stream = rospy.get_param('~ntrip_stream')
                    print("connecting to new MountPoint : " + "\"" 
                        + self.ntc.ntrip_stream + "\"")
                    rospy.set_param('~is_new_stream', False)
                else:
                    ''' If zero length data, close connection and reopen it '''
                    restart_count = restart_count + 1
                    print("Zero length ", restart_count)
                connection.close()
                while reconnect:
                    if is_connected(REMOTE_SERVER):
                        rospy.loginfo("Connected to internet")
                        reconnect = False
                    else:
                        rospy.logwarn("No internet connection")
                        rospy.sleep(5)
                connection = HTTPConnection(self.ntc.ntrip_server, timeout=10)
                connection.request('GET', '/'+self.ntc.ntrip_stream, self.ntc.nmea_gga, headers)
                response = connection.getresponse()
                if response.status != 200: raise Exception("blah")
                buf = ""

        connection.close()

class ntripclient:
    def __init__(self):
        rospy.init_node('ntripclient', anonymous=True)

        self.rtcm_topic = rospy.get_param('~rtcm_topic', 'rtcm')
        self.nmea_topic = rospy.get_param('~nmea_topic', 'nmea')

        self.ntrip_server = rospy.get_param('~ntrip_server')
        self.ntrip_user = rospy.get_param('~ntrip_user')
        self.ntrip_pass = rospy.get_param('~ntrip_pass')
        self.ntrip_stream = rospy.get_param('~ntrip_stream')
        self.nmea_gga = rospy.get_param('~nmea_gga')
        
        rospy.set_param('~is_new_stream', False)
        
        self.pub = rospy.Publisher(self.rtcm_topic, Message, queue_size=10)

        self.connection = None
        self.connection = ntripconnect(self)
        self.connection.start()

    def run(self):
        rospy.spin()
        if self.connection is not None:
            self.connection.stop = True

if __name__ == '__main__':
    c = ntripclient()
    c.run()

