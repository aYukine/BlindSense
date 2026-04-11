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

class SpatialFusionNode : public rclcpp::Node {
public:
    SpatialFusionNode() : Node("spatial_fusion_node") {
        // Publishers
        semantic_pc_pub_ = this->create_publisher<sensor_msgs::msg::PointCloud2>("fusion/semantic_cloud", 10);
        
        // Subscribers
        info_sub_ = this->create_subscription<sensor_msgs::msg::CameraInfo>(
            "camera/depth/camera_info", 10, std::bind(&SpatialFusionNode::info_cb, this, _1));
            
        mask_sub_ = this->create_subscription<sensor_msgs::msg::Image>(
            "inference/segmentation_mask", 10, std::bind(&SpatialFusionNode::mask_cb, this, _1));
            
        pc_sub_ = this->create_subscription<sensor_msgs::msg::PointCloud2>(
            "perception/point_cloud", 10, std::bind(&SpatialFusionNode::pc_cb, this, _1));
            
        RCLCPP_INFO(this->get_logger(), "Spatial Fusion Node Initialized: Ready to merge 2D AI with 3D Space");
    }

private:
    void info_cb(const sensor_msgs::msg::CameraInfo::SharedPtr msg) {
        cam_model_.fromCameraInfo(msg);
        has_cam_info_ = true;
    }

    void mask_cb(const sensor_msgs::msg::Image::SharedPtr msg) {
        try {
            latest_mask_ = cv_bridge::toCvCopy(msg, "bgr8")->image;
        } catch (cv_bridge::Exception& e) {
            RCLCPP_ERROR(this->get_logger(), "cv_bridge exception: %s", e.what());
        }
    }

    void pc_cb(const sensor_msgs::msg::PointCloud2::SharedPtr msg) {
        if (!has_cam_info_ || latest_mask_.empty()) {
            RCLCPP_WARN_THROTTLE(this->get_logger(), *this->get_clock(), 2000, "Waiting for Camera Info and Fast-SCNN Mask...");
            return;
        }

        pcl::PointCloud<pcl::PointXYZ>::Ptr cloud_in(new pcl::PointCloud<pcl::PointXYZ>());
        pcl::fromROSMsg(*msg, *cloud_in);

        pcl::PointCloud<pcl::PointXYZRGB>::Ptr semantic_cloud(new pcl::PointCloud<pcl::PointXYZRGB>());
        semantic_cloud->header = cloud_in->header;

        for (const auto& pt : cloud_in->points) {
            if (!std::isfinite(pt.z)) continue;

            // Project 3D point (XYZ) back to 2D pixel (u, v)
            cv::Point3d pt_3d(pt.x, pt.y, pt.z);
            cv::Point2d pt_2d = cam_model_.project3dToPixel(pt_3d);

            int u = std::round(pt_2d.x);
            int v = std::round(pt_2d.y);

            if (u >= 0 && u < latest_mask_.cols && v >= 0 && v < latest_mask_.rows) {
                pcl::PointXYZRGB color_pt;
                color_pt.x = pt.x;
                color_pt.y = pt.y;
                color_pt.z = pt.z;

                cv::Vec3b color = latest_mask_.at<cv::Vec3b>(v, u);
                color_pt.b = color[0];
                color_pt.g = color[1];
                color_pt.r = color[2];

                semantic_cloud->points.push_back(color_pt);
            }
        }

        sensor_msgs::msg::PointCloud2 out_msg;
        pcl::toROSMsg(*semantic_cloud, out_msg);
        out_msg.header = msg->header;
        semantic_pc_pub_->publish(out_msg);
    }

    rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr semantic_pc_pub_;
    rclcpp::Subscription<sensor_msgs::msg::CameraInfo>::SharedPtr info_sub_;
    rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr mask_sub_;
    rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr pc_sub_;
    
    image_geometry::PinholeCameraModel cam_model_;
    bool has_cam_info_ = false;
    cv::Mat latest_mask_;
};

int main(int argc, char **argv) {
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<SpatialFusionNode>());
    rclcpp::shutdown();
    return 0;
}