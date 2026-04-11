cmake_minimum_required(VERSION 3.8)
project(perception_3d)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(cv_bridge REQUIRED)
find_package(image_geometry REQUIRED)
find_package(PCL 1.10 REQUIRED)
find_package(pcl_conversions REQUIRED)
# uncomment the following section in order to fill in
# further dependencies manually.
# find_package(<dependency> REQUIRED)

include_directories(
  include
  ${PCL_INCLUDE_DIRS}
)

add_executable(depth_estimator_node src/depth_estimator_node.cpp)
ament_target_dependencies(depth_estimator_node
  rclcpp
  sensor_msgs
  cv_bridge
  image_geometry
  pcl_conversions
)
target_link_libraries(depth_estimator_node ${PCL_LIBRARIES})

add_executable(spatial_fusion_node src/spatial_fusion_node.cpp)
ament_target_dependencies(spatial_fusion_node
  rclcpp
  sensor_msgs
  cv_bridge
  image_geometry
  pcl_conversions
)
target_link_libraries(spatial_fusion_node ${PCL_LIBRARIES})

install(TARGETS
  depth_estimator_node
  spatial_fusion_node
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
