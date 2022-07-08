# ntrip_ros
NTRIP client, imports RTCM streams to ROS topic

This was forked from [https://github.com/ros-agriculture/ntrip_ros.git]

Just added **is_new_stream** Ros parameter which allows you to change the **Mountpoint** while the node is still running. For that you just have to set the new value of the **ntrip_stream** parameter and set to **True** the **is_new_stream**

Usefull to automatically set the **nearest Mountpoint** when you are using CORS network, in my setup I used it with : [CentipedeRTK network](https://centipede.fr/) CORS correction server, [U-blox ZED-F9P driver](https://github.com/ros-agriculture/ublox_f9p.git) and [Ntrip Browser](https://github.com/mcognie/ntripbrowser_ros.git) to find the nearest base station 
