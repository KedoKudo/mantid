#ifndef VTK_STRUCTURED_GRID_FACTORY_TEST_H_
#define VTK_STRUCTURED_GRID_FACTORY_TEST_H_

#include <gmock/gmock.h>
#include <gtest/gtest.h>
#include <cxxtest/TestSuite.h>
#include "MantidVatesAPI/vtkStructuredGridFactory.h"
#include "MantidVatesAPI/TimeStepToTimeStep.h"

using namespace Mantid;

//=====================================================================================
// Test Helpers Types
//=====================================================================================
namespace vtkStructuredGridFactoryTestHelpers
{
  ///Helper class. Concrete instance of IMDDimension.
  class FakeIMDDimension: public Mantid::Geometry::IMDDimension
  {
  private:
    std::string m_id;
    const unsigned int m_nbins;
  public:
    FakeIMDDimension(std::string id, unsigned int nbins=10) : m_id(id), m_nbins(nbins) {}
    std::string getName() const {throw std::runtime_error("Not implemented");}
    std::string getUnits() const {throw std::runtime_error("Not implemented");}
    std::string getDimensionId() const {return m_id;}
    double getMaximum() const {return 10;}
    double getMinimum() const {return 0;}
    size_t getNBins() const {return m_nbins;}
    std::string toXMLString() const {throw std::runtime_error("Not implemented");}
    double getX(size_t) const {throw std::runtime_error("Not implemented");}
    virtual ~FakeIMDDimension()
    {
    }
  };

  /// Mock IMDDimension.
  class MockIMDWorkspace: public Mantid::API::IMDWorkspace
  {
  public:

    MOCK_CONST_METHOD0(id, const std::string());
    MOCK_CONST_METHOD0(getMemorySize, size_t());
    MOCK_CONST_METHOD1(getPoint,const Mantid::Geometry::SignalAggregate&(size_t index));
    MOCK_CONST_METHOD1(getCell,const Mantid::Geometry::SignalAggregate&(size_t dim1Increment));
    MOCK_CONST_METHOD2(getCell,const Mantid::Geometry::SignalAggregate&(size_t dim1Increment, size_t dim2Increment));
    MOCK_CONST_METHOD3(getCell,const Mantid::Geometry::SignalAggregate&(size_t dim1Increment, size_t dim2Increment, size_t dim3Increment));
    MOCK_CONST_METHOD4(getCell,const Mantid::Geometry::SignalAggregate&(size_t dim1Increment, size_t dim2Increment, size_t dim3Increment, size_t dim4Increment));

    MOCK_CONST_METHOD0(getWSLocation,std::string());
    MOCK_CONST_METHOD0(getGeometryXML,std::string());

    MOCK_CONST_METHOD0(getNPoints, uint64_t());
    MOCK_CONST_METHOD4(getSignalAt, signal_t(size_t index1, size_t index2, size_t index3, size_t index4));
    MOCK_CONST_METHOD0(getNonIntegratedDimensions, Mantid::Geometry::VecIMDDimension_const_sptr());

    const Mantid::Geometry::SignalAggregate& getCell(...) const
    {
      throw std::runtime_error("Not Implemented");
    }

    virtual ~MockIMDWorkspace() {}
  };
}

using namespace vtkStructuredGridFactoryTestHelpers;

//=====================================================================================
// Functional Tests
//=====================================================================================
class vtkStructuredGridFactoryTest: public CxxTest::TestSuite
{

public:

  void testCopy()
  {
    using namespace Mantid::VATES;
    using namespace Mantid::Geometry;
    using namespace testing;

    MockIMDWorkspace* pMockWs = new MockIMDWorkspace;
    pMockWs->addDimension(new FakeIMDDimension("x"));
    pMockWs->addDimension(new FakeIMDDimension("y"));
    pMockWs->addDimension(new FakeIMDDimension("z"));
    pMockWs->addDimension(new FakeIMDDimension("t"));
    EXPECT_CALL(*pMockWs, getSignalAt(_, _, _, _)).Times(AtLeast(1)).WillRepeatedly(Return(1));

    Mantid::API::IMDWorkspace_sptr ws_sptr(pMockWs);

    //Constructional method ensures that factory is only suitable for providing mesh information.
    vtkStructuredGridFactory<TimeStepToTimeStep> factoryA =
      vtkStructuredGridFactory<TimeStepToTimeStep> ("signal", 0);
    factoryA.initialize(ws_sptr);

    vtkStructuredGridFactory<TimeStepToTimeStep> factoryB(factoryA);
    //Test factory copies indirectly via the products.
    vtkStructuredGrid* productA = factoryA.create();
    vtkStructuredGrid* productB = factoryB.create();

    TSM_ASSERT_EQUALS("Not copied correctly. Mesh data mismatch.", productA->GetNumberOfPoints(), productB->GetNumberOfPoints());
    TSM_ASSERT_EQUALS("Not copied correctly. Signal data mismatch.", std::string(productA->GetCellData()->GetArray(0)->GetName()), std::string(productB->GetCellData()->GetArray(0)->GetName()));
    productA->Delete();
    productB->Delete();
  }

  void testAssignment()
  {
    using namespace Mantid::VATES;
    using namespace Mantid::Geometry;
    using namespace testing;

    MockIMDWorkspace* pMockWs = new MockIMDWorkspace;
    EXPECT_CALL(*pMockWs, getSignalAt(_, _, _, _)).Times(AtLeast(1)).WillRepeatedly(Return(1));
    pMockWs->addDimension(new FakeIMDDimension("x"));
    pMockWs->addDimension(new FakeIMDDimension("y"));
    pMockWs->addDimension(new FakeIMDDimension("z"));
    pMockWs->addDimension(new FakeIMDDimension("t"));

    Mantid::API::IMDWorkspace_sptr ws_sptr(pMockWs);

    //Constructional method ensures that factory is only suitable for providing mesh information.
    vtkStructuredGridFactory<TimeStepToTimeStep> factoryA =
      vtkStructuredGridFactory<TimeStepToTimeStep> ("signal", 0);
    factoryA.initialize(ws_sptr);

    vtkStructuredGridFactory<TimeStepToTimeStep> factoryB =
      vtkStructuredGridFactory<TimeStepToTimeStep> ("other", 0);
    factoryB.initialize(ws_sptr);

    factoryB = factoryA;
    //Test factory assignments indirectly via the factory products.
    vtkStructuredGrid* productA = factoryA.create();
    vtkStructuredGrid* productB = factoryB.create();

    TSM_ASSERT_EQUALS("Not assigned correctly. Mesh data mismatch.", productA->GetNumberOfPoints(), productB->GetNumberOfPoints());
    TSM_ASSERT_EQUALS("Not assigned correctly. Signal data mismatch.", std::string(productA->GetCellData()->GetArray(0)->GetName()), std::string(productB->GetCellData()->GetArray(0)->GetName()));
    productA->Delete();
    productB->Delete();
  }

  void testMeshOnly()
  {
    using namespace Mantid::VATES;
    using namespace Mantid::Geometry;
    using namespace testing;

    MockIMDWorkspace* pMockWs = new MockIMDWorkspace;
    EXPECT_CALL(*pMockWs, getSignalAt(_, _, _, _)).Times(0); //Shouldn't access getSignal At
    pMockWs->addDimension(new FakeIMDDimension("x"));
    pMockWs->addDimension(new FakeIMDDimension("y"));
    pMockWs->addDimension(new FakeIMDDimension("z"));
    pMockWs->addDimension(new FakeIMDDimension("t"));

    Mantid::API::IMDWorkspace_sptr ws_sptr(pMockWs);

    //Constructional method ensures that factory is only suitable for providing mesh information.
    vtkStructuredGridFactory<TimeStepToTimeStep> factory =
      vtkStructuredGridFactory<TimeStepToTimeStep>::constructAsMeshOnly();
    factory.initialize(ws_sptr);

    //Invoke mocked methods on MockIMDWorkspace.
    vtkStructuredGrid* product = factory.createMeshOnly();

    int predictedNPoints = (10 + 1) * (10 + 1) * (10 + 1);
    TSM_ASSERT_EQUALS("Wrong number of points generated", predictedNPoints, product->GetNumberOfPoints());
    TSM_ASSERT("This is not a mesh-only product.", testing::Mock::VerifyAndClearExpectations(pMockWs));
    product->Delete();
  }

  void testMeshOnlyCausesThrow()
  {
    using namespace Mantid::VATES;
    using namespace Mantid::Geometry;
    using namespace testing;

    MockIMDWorkspace* pMockWs = new MockIMDWorkspace;
    pMockWs->addDimension(new FakeIMDDimension("z"));
    pMockWs->addDimension(new FakeIMDDimension("y"));
    pMockWs->addDimension(new FakeIMDDimension("z"));
    pMockWs->addDimension(new FakeIMDDimension("t"));
    Mantid::API::IMDWorkspace_sptr ws_sptr(pMockWs);

    //Constructional method ensures that factory is only suitable for providing mesh information.
    vtkStructuredGridFactory<TimeStepToTimeStep> factory =
      vtkStructuredGridFactory<TimeStepToTimeStep>::constructAsMeshOnly();
    factory.initialize(ws_sptr);

    TSM_ASSERT_THROWS("Cannot access non-mesh information when factory constructed as mesh-only", factory.createScalarArray(), std::runtime_error);
  }

  void testSignalAspects()
  {
    using namespace Mantid::VATES;
    using namespace Mantid::Geometry;
    using namespace testing;
    TimeStepToTimeStep timeMapper;

    MockIMDWorkspace* pMockWs = new MockIMDWorkspace;
    EXPECT_CALL(*pMockWs, getSignalAt(_, _, _, _)).WillRepeatedly(Return(1)); //Shouldn't access getSignal At
    pMockWs->addDimension(new FakeIMDDimension("x"));
    pMockWs->addDimension(new FakeIMDDimension("y"));
    pMockWs->addDimension(new FakeIMDDimension("z"));
    pMockWs->addDimension(new FakeIMDDimension("t"));

    Mantid::API::IMDWorkspace_sptr ws_sptr(pMockWs);

    //Constructional method ensures that factory is only suitable for providing mesh information.
    vtkStructuredGridFactory<TimeStepToTimeStep> factory =
      vtkStructuredGridFactory<TimeStepToTimeStep> ("signal", 1);
    factory.initialize(ws_sptr);

    vtkDataSet* product = factory.create();
    TSM_ASSERT_EQUALS("A single array should be present on the product dataset.", 1, product->GetCellData()->GetNumberOfArrays());
    vtkDataArray* signalData = product->GetCellData()->GetArray(0);
    TSM_ASSERT_EQUALS("The obtained cell data has the wrong name.", std::string("signal"), signalData->GetName());
    const int correctCellNumber = (10) * (10) * (10);
    TSM_ASSERT_EQUALS("The number of signal values generated is incorrect.", correctCellNumber, signalData->GetSize());
    product->Delete();
  }

  void testIsValidThrowsWhenNoWorkspace()
  {
    using namespace Mantid::VATES;
    using namespace Mantid::API;

    IMDWorkspace* nullWorkspace = NULL;
    Mantid::API::IMDWorkspace_sptr ws_sptr(nullWorkspace);

    vtkStructuredGridFactory<TimeStepToTimeStep> factory("signal", 1);

    TSM_ASSERT_THROWS("No workspace, so should not be possible to complete initialization.", factory.initialize(ws_sptr), std::runtime_error);
  }

  void testIsValidThrowsWhenNoTDimension()
  {
    using namespace Mantid::VATES;
    using namespace Mantid::API;
    using namespace Mantid::Geometry;
    using namespace testing;

    IMDDimension* nullDimension = NULL;
    MockIMDWorkspace* pMockWs = new MockIMDWorkspace;
    pMockWs->addDimension(nullDimension);

    Mantid::API::IMDWorkspace_sptr ws_sptr(pMockWs);
    vtkStructuredGridFactory<TimeStepToTimeStep> factory("signal", 1);

    TSM_ASSERT_THROWS("No T dimension, so should not be possible to complete initialization.", factory.initialize(ws_sptr), std::runtime_error);
  }

  void testTypeName()
  {
    using namespace Mantid::VATES;
    vtkStructuredGridFactory<TimeStepToTimeStep> factory("signal", 1);
    TS_ASSERT_EQUALS("vtkStructuredGridFactory", factory.getFactoryTypeName());
  }

};

//=====================================================================================
// Performance tests
//=====================================================================================
class vtkStructuredGridFactoryTestPerformance : public CxxTest::TestSuite
{
public:
 MockIMDWorkspace* pMockWs;

  void setUp()
  {
    using namespace Mantid::VATES;
    using namespace Mantid::Geometry;
    using namespace testing;

    //20 by 20 by 20 by 20 workspace.
    pMockWs = new MockIMDWorkspace;
    pMockWs->addDimension(new FakeIMDDimension("x", 100));
    pMockWs->addDimension(new FakeIMDDimension("y", 100));
    pMockWs->addDimension(new FakeIMDDimension("z", 100));
    pMockWs->addDimension(new FakeIMDDimension("t", 100));
  }

  void testGenerateVTKDataSet()
  {
    using namespace Mantid::VATES;
    using namespace Mantid::Geometry;
    using namespace testing;

    Mantid::API::IMDWorkspace_sptr ws_sptr(pMockWs);

    //Constructional method ensures that factory is only suitable for providing mesh information.
    vtkStructuredGridFactory<TimeStepToTimeStep> factory =
      vtkStructuredGridFactory<TimeStepToTimeStep>::constructAsMeshOnly();
    factory.initialize(ws_sptr);

    //Invoke mocked methods on MockIMDWorkspace.
    TS_ASSERT_THROWS_NOTHING(factory.createMeshOnly());
  }
};


#endif
