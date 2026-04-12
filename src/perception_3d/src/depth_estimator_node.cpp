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

class DepthEstimatorNode : public rclcpp::Node {
public:
    DepthEstimatorNode() : Node("depth_estimator_node") {
        pc_pub_ = this->create_publisher<sensor_msgs::msg::PointCloud2>("perception/point_cloud", 10);
        
        depth_sub_ = this->create_subscription<sensor_msgs::msg::Image>(
            "camera/depth/image_rect_raw", 10, std::bind(&DepthEstimatorNode::depth_cb, this, _1));
        info_sub_ = this->create_subscription<sensor_msgs::msg::CameraInfo>(
            "camera/depth/camera_info", 10, std::bind(&DepthEstimatorNode::info_cb, this, _1));
            
        RCLCPP_INFO(this->get_logger(), "Depth Estimator Node Initialized (High-Speed CPU Math Mode)");
    }

private:
    void info_cb(const sensor_msgs::msg::CameraInfo::SharedPtr msg) {
        if (!has_cam_info_) {
            cam_model_.fromCameraInfo(msg);
            
            // CACHE INTRINSICS: Do this once, not 2.3 million times a second!
            fx_ = cam_model_.fx();
            fy_ = cam_model_.fy();
            cx_ = cam_model_.cx();
            cy_ = cam_model_.cy();
            
            has_cam_info_ = true;
            RCLCPP_INFO(this->get_logger(), "Camera Intrinsics Locked. Ready for 3D Projection.");
        }
    }

    void depth_cb(const sensor_msgs::msg::Image::SharedPtr msg) {
        if (!has_cam_info_) return;

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

        // PRE-ALLOCATE MEMORY: Prevents the CPU from pausing to request RAM thousands of times per frame
        cloud->points.reserve((cv_ptr->image.rows / 2) * (cv_ptr->image.cols / 2));

        for (int v = 0; v < cv_ptr->image.rows; v += 2) { 
            for (int u = 0; u < cv_ptr->image.cols; u += 2) {
                uint16_t depth = cv_ptr->image.at<uint16_t>(v, u);
                
                // FILTER: Ignore blind spots (0) and objects beyond 4 meters (4000mm)
                if (depth == 0 || depth > 4000) continue; 

                float z = depth * 0.001f; 
                
                // --- OPTIMIZED ARM MATH ---
                // Replaced the heavy matrix projection with direct scalar math
                pcl::PointXYZ pt;
                pt.x = (u - cx_) * z / fx_;
                pt.y = (v - cy_) * z / fy_;
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
    
    // Cached Intrinsics
    float fx_, fy_, cx_, cy_;
};

int main(int argc, char **argv) {
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<DepthEstimatorNode>());
    rclcpp::shutdown();
    return 0;
}