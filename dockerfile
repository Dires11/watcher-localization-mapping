# Stage 1: Base Image with ZED SDK and CUDA
FROM stereolabs/zed:5.2-gl-devel-cuda12.8-ubuntu24.04
# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# System setup & Locales
RUN apt-get update && apt-get install -y locales && \
    locale-gen en_US en_US.UTF-8 && \
    update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
ENV LANG=en_US.UTF-8

# Install ROS 2 Repository Tools
RUN apt-get update && apt-get install -y software-properties-common curl && \
    add-apt-repository universe && \
    export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F\" '{print $4}') && \
    curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb" && \
    apt install -y /tmp/ros2-apt-source.deb && \
    apt-get update && apt-get install -y ros-dev-tools nano

# Install ROS 2 Jazzy Desktop
RUN apt-get update && apt-get install -y ros-jazzy-desktop

# Install SLAM, localization, and perception dependencies
RUN apt-get update && apt-get install -y \
    ros-jazzy-rtabmap \
    ros-jazzy-rtabmap-ros \
    ros-jazzy-rtabmap-rviz-plugins \
    ros-jazzy-robot-localization \
    ros-jazzy-pointcloud-to-laserscan \
    ros-jazzy-tf2-sensor-msgs \
    ros-jazzy-robot-state-publisher \
    ros-jazzy-joint-state-publisher \
    ros-jazzy-xacro \
    ros-jazzy-tf2-ros \
    ros-jazzy-tf2-geometry-msgs \
    ros-jazzy-tf2-sensor-msgs \
    ros-jazzy-nav2-map-server \
    ros-jazzy-rqt-tf-tree \
    ros-jazzy-rqt-graph \
    && rm -rf /var/lib/apt/lists/*

# Setup Workspace
WORKDIR /root/ros2_ws
RUN mkdir -p src && \
    cd src && \
    git clone https://github.com/stereolabs/zed-ros2-wrapper.git && \
    git clone https://github.com/stereolabs/zed-ros2-interfaces.git

# Install Dependencies using rosdep
RUN rosdep init && rosdep update && \
    apt-get update && \
    rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy

# Build the Workspace
# We use /opt/ros/jazzy/setup.sh to source the environment for the build
RUN . /opt/ros/jazzy/setup.sh && \
    colcon build --symlink-install \
    --cmake-args=-DCMAKE_BUILD_TYPE=Release \
    --packages-skip zed_debug zed_ros2 \
    --parallel-workers $(nproc)

# Environment Configuration
RUN echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc && \
    echo "source /root/ros2_ws/install/setup.bash" >> ~/.bashrc

ENTRYPOINT ["/bin/bash"]