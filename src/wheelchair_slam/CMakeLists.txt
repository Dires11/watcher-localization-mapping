cmake_minimum_required(VERSION 3.8)
project(wheelchair_slam)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(PROGRAMS
  wheelchair_slam/pointcloud_merger.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME pointcloud_merger
)

install(DIRECTORY
  launch
  config
  urdf
  rviz
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
