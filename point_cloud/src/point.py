#!/usr/bin/env python

import cv2
import numpy as np 
from timeit import default_timer as timer

import rospy
import tf as ros_tf
from sensor_msgs.msg import Image
from sensor_msgs.msg import CameraInfo
from sensor_msgs.msg import PointCloud2
from sensor_msgs.msg import PointField
from cv_bridge import CvBridge, CvBridgeError
from image_geometry import PinholeCameraModel


class CNN:

    def __init__(self,resize_width,resize_height):
        self.resize_width = resize_width
        self.resize_height = resize_height
        self.bridge = CvBridge()

        
        camera_info = rospy.wait_for_message('/usb_cam/camera_info', CameraInfo, timeout=5)
        # except(rospy.ROSException), e:
        #     print ("Camera info topic not available")
        #     print (e)
        #     exit()
        waf = float(resize_width) / camera_info.width
        haf = float(resize_height) / camera_info.height
        camera_info.height = resize_height
        camera_info.width = resize_width

        # adjust the camera matrix
        K = camera_info.K
        camera_info.K = (K[0]*waf,         0.,  K[2]*waf,
                                0.,  K[4]*haf,  K[5]*haf,
                                0.,        0.,         1.)

        # adjust the projection matrix
        P = camera_info.P
        camera_info.P = (P[0]*waf,        0.,  P[2]*waf,  0.,
                               0.,  P[5]*haf,  P[6]*haf,  0.,
                               0.,        0.,        1.,  0.)

        self.camera_model = PinholeCameraModel()
        self.camera_model.fromCameraInfo(camera_info)
        print (camera_info)
	print(1)
        transform_listener = ros_tf.TransformListener()
        transform_listener.waitForTransform('/base_link', '/camera_rgb_frame', rospy.Time(0), rospy.Duration(5.0))
        cam_transform_translation, cam_transform_rotation = transform_listener.lookupTransform('/base_link', '/camera_rgb_frame', rospy.Time(0))
        self.cam_transform_rotation_matrix = ros_tf.transformations.quaternion_matrix(cam_transform_rotation)[:-1,:-1]
        self.cam_transform_translation = np.asarray(cam_transform_translation)
        print (self.cam_transform_translation)
        print (self.cam_transform_rotation_matrix)

	self.init_point_cloud_array()
        #self.im_publisher = rospy.Publisher(publisher_topic, Image, queue_size=1)
        self.cloud_publisher = rospy.Publisher("/semantic_segmentation_cloud", PointCloud2, queue_size=1)
	self.subscriber = rospy.Subscriber("/image_topic", Image, self.image_callback, queue_size=1, buff_size=10**8)
    def init_point_cloud_array(self):
        world_points_array = np.empty( (self.resize_height,self.resize_width,3), dtype=np.float32)
        for r,c in np.ndindex(self.resize_height,self.resize_width):
            ray = np.asarray( self.camera_model.projectPixelTo3dRay( (c,r) ) )
            ray_in_world = np.matmul( self.cam_transform_rotation_matrix, ray )
            scale = -self.cam_transform_translation[2] / ray_in_world[2]
            world_point = scale * ray_in_world + self.cam_transform_translation
            world_points_array[r,c] = [world_point[0], world_point[1], world_point[2]]
        self.world_point_array = world_points_array
	print(2)

    def image_callback(self, image_msg):
	print(3)        
	start = timer()
        try:
             cv_image = self.bridge.imgmsg_to_cv2(image_msg, "bgr8")
        except CvBridgeError as e:
            print(e)
        cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        cv_image = cv2.resize(cv_image, (self.resize_width, self.resize_height))
        im = np.asarray(cv_image)
        #image_pl = self.graph.get_tensor_by_name('Placeholder_1:0')
        #softmax = self.graph.get_tensor_by_name('Validation/decoder/Softmax:0')

        #output = self.sess.run([softmax], feed_dict={image_pl: im})
        shape = im.shape
        output_image = im
        # cv2.imshow('fig',im)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        threshold = 0.5
        im_threshold = output_image

        world_points = self.world_point_array[im_threshold]

        cv_output = np.uint8(im_threshold)
        #cv_output = cv2.cvtColor(im_threshold, cv2.COLOR_GRAY2BGR)
        msg_out = self.bridge.cv2_to_imgmsg(cv_output, 'bgr8')
        msg_out.header.stamp = image_msg.header.stamp
        #self.im_publisher.publish(msg_out)

        points = world_points
        cloud_msg = PointCloud2()
        cloud_msg.header.stamp = image_msg.header.stamp
        cloud_msg.header.frame_id = 'base_link'
        cloud_msg.height = 1
        cloud_msg.width = len(world_points)
        cloud_msg.fields = [
            PointField('x', 0, PointField.FLOAT32, 1),
            PointField('y', 4, PointField.FLOAT32, 1),
            PointField('z', 8, PointField.FLOAT32, 1)]
        cloud_msg.is_bigendian = False
        cloud_msg.point_step = 4
        cloud_msg.row_step = 3 * len(world_points)
        cloud_msg.data = world_points.tostring()

        self.cloud_publisher.publish(cloud_msg)
        end = timer()
	print end - start



if __name__ == '__main__':
    rospy.init_node('cnn')
    img=cv2.imread('1.jpg')
    VideoRaw = rospy.Publisher('image_topic', Image, queue_size=10)
    #image_topic = rospy.get_param('/image_topic')
    msg_frame = CvBridge().cv2_to_imgmsg(frame)
    image_topic.publish(msg_frame, "bgr8")
    CNN(100,100)

    try:
        rospy.spin()
    except KeyboardInterrupt:
        print("Shutting down")
