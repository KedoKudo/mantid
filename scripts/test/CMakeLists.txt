set(TEST_PY_FILES
    AbsorptionShapesTest.py
    CalculateMuonAsymmetryTest.py
    ConvertToWavelengthTest.py
    CrystalFieldMultiSiteTest.py
    CrystalFieldTest.py
    DirectEnergyConversionTest.py
    DirectPropertyManagerTest.py
    DirectReductionHelpersTest.py
    DoublePulseFitTest.py
    IndirectCommonTests.py
    InelasticDirectDetpackmapTest.py
    ISISDirecInelasticConfigTest.py
    PyChopTest.py
    pythonTSVTest.py
    ReductionSettingsTest.py
    ReductionWrapperTest.py
    ReflectometryQuickAuxiliaryTest.py
    RunDescriptorTest.py
    SANSDarkRunCorrectionTest.py
    SANSIsisInstrumentTest.py
    SANSUserFileParserTest.py
    SANSUtilityTest.py
    SettingsTest.py
    StitchingTest.py
    VesuvioBackgroundTest.py
    VesuvioFittingTest.py
    VesuvioProfileTest.py)

# these are gui tests that currently only work in pyqt4
set(TEST_PYQT4_FILES
    SANSBatchModeTest.py
    SANSCentreFinderTest.py
    SANSCommandInterfaceTest.py
    SansIsisGuiSettings.py
    SANSReducerTest.py
    SANSReductionStepsUserFileTest.py)

pyunittest_add_test(${CMAKE_CURRENT_SOURCE_DIR} python.scripts
  ${TEST_PY_FILES})

set(PYUNITTEST_QT_API pyqt) # force to use qt4
pyunittest_add_test(${CMAKE_CURRENT_SOURCE_DIR} python.scriptsQt4
                      ${TEST_PYQT4_FILES})
unset(PYUNITTEST_QT_API)


# Additional tests
add_subdirectory(Abins)
add_subdirectory(directtools)
add_subdirectory(Calibration)
add_subdirectory(corelli)
add_subdirectory(MultiPlotting)
add_subdirectory(Muon)
add_subdirectory(sample_transmission_calculator)
add_subdirectory(SANS)
add_subdirectory(TOFTOF)
