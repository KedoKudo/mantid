#ifndef MANTID_ALGORITHMS_FindPeakBackground_H_
#define MANTID_ALGORITHMS_FindPeakBackground_H_

#include "MantidAPI/Algorithm.h"
#include "MantidAPI/ITableWorkspace.h"
#include "MantidKernel/cow_ptr.h"

namespace Mantid {

namespace HistogramData {
class HistogramX;
class HistogramY;
}

namespace Algorithms {

/** FindPeakBackground : Calculate Zscore for a Matrix Workspace

  Copyright &copy; 2012 ISIS Rutherford Appleton Laboratory, NScD Oak Ridge
  National Laboratory & European Spallation Source

  This file is part of Mantid.

  Mantid is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 3 of the License, or
  (at your option) any later version.

  Mantid is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.

  File change history is stored at: <https://github.com/mantidproject/mantid>
  Code Documentation is available at: <http://doxygen.mantidproject.org>
*/

class DLLExport FindPeakBackground : public API::Algorithm {
public:
  /// Algorithm's name for identification overriding a virtual method
  const std::string name() const override { return "FindPeakBackground"; }
  /// Summary of algorithms purpose
  const std::string summary() const override {
    return "Separates background from signal for spectra of a workspace.";
  }

  /// Algorithm's version for identification overriding a virtual method
  int version() const override { return 1; }

  /// process inputs
  void processInputProperties();

  /// Algorithm's category for identification overriding a virtual method
  const std::string category() const override { return "Utility\\Calculation"; }

  /// set histogram data to find background
  // void setHistogram(HistogramData &histogram);

  /// set sigma constant
  void setSigma(const double &sigma);

  /// set background order
  void setBackgroundOrder(size_t order);

  /// set fit window
  void setFitWindow(const std::vector<double> &window);

  /// find background (main algorithm)
  void findPeakBackground();

  /// get result
  void getBackgroundResult();

private:
  std::string m_backgroundType; //< The type of background to fit

  /// Implement abstract Algorithm methods
  void init() override;
  /// Implement abstract Algorithm methods
  void exec() override;
  double moment4(MantidVec &X, size_t n, double mean);
  void estimateBackground(const HistogramData::HistogramX &X,
                          const HistogramData::HistogramY &Y,
                          const size_t i_min, const size_t i_max,
                          const size_t p_min, const size_t p_max,
                          const bool hasPeak, double &out_bg0, double &out_bg1,
                          double &out_bg2);

  /// create output workspace
  void createOutputWorkspaces();

  struct cont_peak {
    size_t start;
    size_t stop;
    double maxY;
  };
  struct by_len {
    bool operator()(cont_peak const &a, cont_peak const &b) {
      return a.maxY > b.maxY;
    }
  };

  void findStartStopIndex(size_t &istart, size_t &istop);

  // define parameters

  /// histogram data to find peak background
  // HistogramData::Histogram m_histogram;
  /// fit window
  std::vector<double> m_vecFitWindows;
  /// background order: 0 for flat, 1 for linear, 2 for quadratic
  size_t m_backgroundOrder;
  /// constant sigma
  double m_sigmaConstant;
  /// output workspace (table of result)
  API::ITableWorkspace_sptr m_outPeakTableWS;
};

} // namespace Algorithms
} // namespace Mantid

#endif /* MANTID_ALGORITHMS_FindPeakBackground_H_ */
