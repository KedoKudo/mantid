project(MantidParaViewNexusPeaksReader)
include_directories(SYSTEM ${PARAVIEW_INCLUDE_DIRS})
add_paraview_plugin(MantidParaViewNexusPeaksReaderSMPlugin
                    "1.0"
                    SERVER_MANAGER_XML
                    NexusPeaksReader.xml
                    SERVER_MANAGER_SOURCES
                    vtkNexusPeaksReader.cxx)
set_pvplugin_properties(MantidParaViewNexusPeaksReaderSMPlugin QT_VERSION 4)

target_link_libraries(MantidParaViewNexusPeaksReaderSMPlugin
                      LINK_PRIVATE
                      ${CORE_MANTIDLIBS}
                      DataObjects
                      VatesAPI
                      ${POCO_LIBRARIES}
                      ${Boost_LIBRARIES}
                      ${NEXUS_LIBRARIES}
                      ${NEXUS_C_LIBRARIES})

if(${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
  set_target_properties(
    MantidParaViewNexusPeaksReaderSMPlugin
    PROPERTIES
      INSTALL_RPATH
      "@loader_path/../../../Contents/Frameworks;@loader_path/../../../Contents/MacOS"
    )
elseif(${CMAKE_SYSTEM_NAME} STREQUAL "Linux")
  set_target_properties(MantidParaViewNexusPeaksReaderSMPlugin
                        PROPERTIES INSTALL_RPATH "\$ORIGIN/../../../${LIB_DIR}")
endif()

install_pvplugin(MantidParaViewNexusPeaksReaderSMPlugin QT_VERSION 4)
