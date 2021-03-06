// Mantid Repository : https://github.com/mantidproject/mantid
//
// Copyright &copy; 2010 ISIS Rutherford Appleton Laboratory UKRI,
//   NScD Oak Ridge National Laboratory, European Spallation Source,
//   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
// SPDX - License - Identifier: GPL - 3.0 +
#pragma once

#include "MantidKernel/System.h"
/**
  Creates a single marker at a given position

  @date 23/02/2015
 */

class vtkPolyData;

namespace Mantid {
namespace VATES {
class DLLExport vtkSinglePeakMarker {
public:
  vtkSinglePeakMarker();
  ~vtkSinglePeakMarker();
  vtkPolyData *createSinglePeakMarker(double x, double y, double z,
                                      double radius);
};
} // namespace VATES
} // namespace Mantid