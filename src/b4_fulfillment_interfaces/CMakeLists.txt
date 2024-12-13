cmake_minimum_required(VERSION 3.8)
project(b4_fulfillment_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(sensor_msgs REQUIRED)  # Add this line to find sensor_msgs
find_package(rosidl_default_generators REQUIRED)

ament_export_dependencies(rosidl_default_runtime)
# uncomment the following section in order to fill in
# further dependencies manually.
# find_package(<dependency> REQUIRED)
set(msg_files
  "msg/Webcam.msg"
  "msg/Button.msg"
  "msg/RobotStatus.msg"
  "msg/ConvGoButton.msg"
  "msg/ConvStopButton.msg"
  "msg/RobotCoord.msg"
)

set(srv_files
  "srv/Coord.srv"
  "srv/Coordinate.srv"
  "srv/DataCollect.srv"
  "srv/MoveCoord.srv"
  "srv/StopMove.srv"
  "srv/DoGrip.srv"
  "srv/ConvStart.srv"
)

set(action_files
  "action/Conveyor.action"
  "action/MoveRobot.action"
)

rosidl_generate_interfaces(${PROJECT_NAME}
  ${msg_files}
  ${srv_files}
  ${action_files}
  DEPENDENCIES
    builtin_interfaces
    sensor_msgs  # Add sensor_msgs here as a dependency
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
