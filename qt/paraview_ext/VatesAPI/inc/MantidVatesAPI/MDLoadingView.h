// Mantid Repository : https://github.com/mantidproject/mantid
//
// Copyright &copy; 2011 ISIS Rutherford Appleton Laboratory UKRI,
//   NScD Oak Ridge National Laboratory, European Spallation Source,
//   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
// SPDX - License - Identifier: GPL - 3.0 +
#pragma once

#include "MantidKernel/System.h"

namespace Mantid {
namespace VATES {

/**
@class MDLoadingView
Abstract view for MDEW file loading and display.
@author Owen Arnold, Tessella plc
@date 05/08/2011
*/
class DLLExport MDLoadingView {
public:
  virtual double getTime() const = 0;
  virtual size_t getRecursionDepth() const = 0;
  virtual bool getLoadInMemory() const = 0;
  virtual ~MDLoadingView() {}
};
} // namespace VATES
} // namespace Mantid
