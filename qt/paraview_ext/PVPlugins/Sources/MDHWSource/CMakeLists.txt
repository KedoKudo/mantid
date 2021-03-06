project(MantidParaViewMDHWSource)
include_directories(SYSTEM ${PARAVIEW_INCLUDE_DIRS})
add_paraview_plugin(MantidParaViewMDHWSourceSMPlugin
                    "1.0"
                    SERVER_MANAGER_XML
                    MDHWSource.xml
                    SERVER_MANAGER_SOURCES
                    vtkMDHWSource.cxx)
set_pvplugin_properties(MantidParaViewMDHWSourceSMPlugin QT_VERSION 4)

include_directories(SYSTEM ${QWT5_INCLUDE_DIR})

target_link_libraries(MantidParaViewMDHWSourceSMPlugin
                      LINK_PRIVATE
                      ${CORE_MANTIDLIBS}
                      DataObjects
                      VatesAPI
                      ${POCO_LIBRARIES}
                      ${Boost_LIBRARIES}
                      ${vtkjsoncpp_LIBRARIES}
                      ${QWT5_LIBRARIES}
                      Qt4::QtCore)

if(${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
  set_target_properties(
    MantidParaViewMDHWSourceSMPlugin
    PROPERTIES
      INSTALL_RPATH
      "@loader_path/../../../Contents/Frameworks;@loader_path/../../../Contents/MacOS"
    )
elseif(${CMAKE_SYSTEM_NAME} STREQUAL "Linux")
  set_target_properties(MantidParaViewMDHWSourceSMPlugin
                        PROPERTIES INSTALL_RPATH "\$ORIGIN/../../../${LIB_DIR}")
endif()

install_pvplugin(MantidParaViewMDHWSourceSMPlugin QT_VERSION 4)
