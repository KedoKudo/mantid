#ifndef MANTID_DATAHANDLING_LOADEVENTNEXUSINDEXSETUP_H_
#define MANTID_DATAHANDLING_LOADEVENTNEXUSINDEXSETUP_H_

#include "MantidDataHandling/DllConfig.h"
#include "MantidAPI/MatrixWorkspace.h"
#include "MantidIndexing/IndexInfo.h"

namespace Mantid {
namespace DataHandling {

/** Helper for LoadEventNexus dealing with setting up indices (spectrum numbers
  an detector ID mapping) for workspaces.

  Copyright &copy; 2017 ISIS Rutherford Appleton Laboratory, NScD Oak Ridge
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
class MANTID_DATAHANDLING_DLL LoadEventNexusIndexSetup {
public:
  LoadEventNexusIndexSetup(API::MatrixWorkspace_const_sptr instrumentWorkspace,
                           const int32_t min, const int32_t max,
                           const std::vector<int32_t> range);

  std::pair<int32_t, int32_t> eventIDLimits() const;

  Indexing::IndexInfo makeIndexInfo();
  Indexing::IndexInfo makeIndexInfo(const std::vector<std::string> &bankNames);
  Indexing::IndexInfo
  makeIndexInfo(const std::pair<std::vector<int32_t>, std::vector<int32_t>> &
                    spectrumDetectorMapping,
                const bool monitorsOnly);

private:
  Indexing::IndexInfo filterIndexInfo(const Indexing::IndexInfo &indexInfo);

  const API::MatrixWorkspace_const_sptr m_instrumentWorkspace;
  int32_t m_min;
  int32_t m_max;
  std::vector<int32_t> m_range;
};

} // namespace DataHandling
} // namespace Mantid

#endif /* MANTID_DATAHANDLING_LOADEVENTNEXUSINDEXSETUP_H_ */
