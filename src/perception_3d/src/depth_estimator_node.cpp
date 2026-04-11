#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <sensor_msgs/msg/camera_info.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <cv_bridge/cv_bridge.h>
#include <image_geometry/pinhole_camera_model.h>
#include <pcl_conversions/pcl_conversions.h>
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>

using std::placeholders::_1;
using std::placeholders::_2;

class DepthEstimatorNode : public rclcpp::Node {
public:
    DepthEstimatorNode() : Node("depth_estimator_node") {
        // Publishers and Subscribers
        pc_pub_ = this->create_publisher<sensor_msgs::msg::PointCloud2>("perception/point_cloud", 10);
        
        // We need both the depth image and the camera info to project 2D to 3D
        depth_sub_ = this->create_subscription<sensor_msgs::msg::Image>(
            "camera/depth/image_rect_raw", 10, std::bind(&DepthEstimatorNode::depth_cb, this, _1));
        info_sub_ = this->create_subscription<sensor_msgs::msg::CameraInfo>(
            "camera/depth/camera_info", 10, std::bind(&DepthEstimatorNode::info_cb, this, _1));
            
        RCLCPP_INFO(this->get_logger(), "Depth Estimator Node Initialized (PCL backend)");
    }

private:
    void info_cb(const sensor_msgs::msg::CameraInfo::SharedPtr msg) {
        cam_model_.fromCameraInfo(msg);
        has_cam_info_ = true;
    }

    void depth_cb(const sensor_msgs::msg::Image::SharedPtr msg) {
        if (!has_cam_info_) {
            RCLCPP_WARN_THROTTLE(this->get_logger(), *this->get_clock(), 2000, "Waiting for camera info...");
            return;
        }

        cv_bridge::CvImagePtr cv_ptr;
        try {
            cv_ptr = cv_bridge::toCvCopy(msg, sensor_msgs::image_encodings::TYPE_16UC1);
        } catch (cv_bridge::Exception& e) {
            RCLCPP_ERROR(this->get_logger(), "cv_bridge exception: %s", e.what());
            return;
        }

        pcl::PointCloud<pcl::PointXYZ>::Ptr cloud(new pcl::PointCloud<pcl::PointXYZ>());
        cloud->header.frame_id = msg->header.frame_id;
        pcl_conversions::toPCL(msg->header.stamp, cloud->header.stamp);

        for (int v = 0; v < cv_ptr->image.rows; v += 2) { 
            for (int u = 0; u < cv_ptr->image.cols; u += 2) {
                uint16_t depth = cv_ptr->image.at<uint16_t>(v, u);
                if (depth == 0) continue; 

                float z = depth * 0.001f; 
                cv::Point2d pt_cv(u, v);
                cv::Point3d pt_3d = cam_model_.projectPixelTo3dRay(pt_cv);

                pcl::PointXYZ pt;
                pt.x = pt_3d.x * z;
                pt.y = pt_3d.y * z;
                pt.z = z;
                cloud->points.push_back(pt);
            }
        }

        sensor_msgs::msg::PointCloud2 pc2_msg;
        pcl::toROSMsg(*cloud, pc2_msg);
        pc2_msg.header.stamp = msg->header.stamp;
        pc_pub_->publish(pc2_msg);
    }

    rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr pc_pub_;
    rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr depth_sub_;
    rclcpp::Subscription<sensor_msgs::msg::CameraInfo>::SharedPtr info_sub_;
    
    image_geometry::PinholeCameraModel cam_model_;
    bool has_cam_info_ = false;
};

int main(int argc, char **argv) {
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<DepthEstimatorNode>());
    rclcpp::shutdown();
    return 0;
}