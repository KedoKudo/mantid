#ifndef REGROUPTEST_H_
#define REGROUPTEST_H_

#include <cxxtest/TestSuite.h>

#include "MantidDataObjects/Workspace2D.h"
#include "MantidAPI/AnalysisDataService.h"
#include "MantidAlgorithms/Regroup.h"
#include "MantidAPI/WorkspaceProperty.h"
#include "MantidAPI/WorkspaceFactory.h"

using namespace Mantid::Kernel;
using namespace Mantid::DataObjects;
using namespace Mantid::API;
using namespace Mantid::Algorithms;
using Mantid::HistogramData::BinEdges;
using Mantid::HistogramData::Counts;
using Mantid::HistogramData::CountStandardDeviations;

class RegroupTest : public CxxTest::TestSuite {
public:
  void testworkspace1D_dist() {
    Workspace2D_sptr test_in1D = Create1DWorkspace(50);
    test_in1D->setDistribution(true);
    AnalysisDataService::Instance().add("test_in1D", test_in1D);

    Regroup regroup;
    regroup.initialize();
    regroup.setChild(true);
    regroup.setPropertyValue("InputWorkspace", "test_in1D");
    regroup.setPropertyValue("OutputWorkspace", "test_out");
    // Check it fails if "params" property not set
    TS_ASSERT_THROWS(regroup.execute(), std::runtime_error)
    TS_ASSERT(!regroup.isExecuted())
    // Trying to set the property with an error fails
    TS_ASSERT_THROWS(
        regroup.setPropertyValue("Params", "1.5,2.0,20,-0.1,15,1.0,35"),
        std::invalid_argument)
    // Now set the property
    TS_ASSERT_THROWS_NOTHING(
        regroup.setPropertyValue("Params", "1.5,1,19,-0.1,30,1,35"))

    TS_ASSERT(regroup.execute())
    TS_ASSERT(regroup.isExecuted())

    MatrixWorkspace_sptr rebindata = regroup.getProperty("OutputWorkspace");
    const Mantid::MantidVec outX = rebindata->dataX(0);

    TS_ASSERT_DELTA(outX[7], 12.5, 0.000001);
    TS_ASSERT_DELTA(outX[12], 20.75, 0.000001);

    AnalysisDataService::Instance().remove("test_in1D");
    AnalysisDataService::Instance().remove("test_out");
  }

private:
  Workspace2D_sptr Create1DWorkspace(int size) {
    auto retVal = createWorkspace<Workspace2D>(1, size, size - 1);
    double j = 1.0;
    for (int i = 0; i < size; i++) {
      retVal->dataX(0)[i] = j * 0.5;
      j += 1.5;
    }
    retVal->setCounts(0, size - 1, 3.0);
    retVal->setCountVariances(0, size - 1, 3.0);
    return retVal;
  }

  Workspace2D_sptr Create2DWorkspace(int xlen, int ylen) {
    BinEdges x1(xlen, 0.0);
    Counts y1(xlen - 1, 3.0);
    CountStandardDeviations e1(xlen - 1, sqrt(3.0));

    auto retVal = createWorkspace<Workspace2D>(ylen, xlen, xlen - 1);
    double j = 1.0;

    for (auto &x : x1) {
      x = j * 0.5;
      j += 1.5;
    }

    for (int i = 0; i < ylen; i++) {
      retVal->setBinEdges(i, x1);
      retVal->setCounts(i, y1);
      retVal->setCountStandardDeviations(i, e1);
    }

    return retVal;
  }
};
#endif /* REGROUPTEST */
