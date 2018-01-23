#include "ReflSettingsPresenter.h"
#include "IReflSettingsTabPresenter.h"
#include "IReflSettingsView.h"
#include "MantidAPI/AlgorithmManager.h"
#include "MantidAPI/AnalysisDataService.h"
#include "MantidAPI/IAlgorithm.h"
#include "MantidAPI/MatrixWorkspace.h"
#include "MantidGeometry/Instrument.h"
#include "MantidQtWidgets/Common/AlgorithmHintStrategy.h"
#include "First.h"
#include "GetInstrumentParameter.h"
#include "ExperimentOptionDefaults.h"
#include "InstrumentOptionDefaults.h"
#include <type_traits>

namespace MantidQt {
namespace CustomInterfaces {

using namespace Mantid::API;
using namespace MantidQt::MantidWidgets;
using namespace Mantid::Geometry;
using namespace MantidQt::MantidWidgets::DataProcessor;

/** Constructor
* @param view :: The view we are handling
* @param group :: The number of the group this settings presenter's settings
* correspond to.
*/
ReflSettingsPresenter::ReflSettingsPresenter(IReflSettingsView *view, int group)
    : m_view(view), m_group(group) {

  // Create the 'HintingLineEdits'
  createStitchHints();
}

/** Destructor
*/
ReflSettingsPresenter::~ReflSettingsPresenter() {}

/** Used by the view to tell the presenter something has changed
*
* @param flag :: A flag used by the view to tell the presenter what happened
*/
void ReflSettingsPresenter::notify(IReflSettingsPresenter::Flag flag) {
  switch (flag) {
  case IReflSettingsPresenter::ExpDefaultsFlag:
    getExpDefaults();
    break;
  case IReflSettingsPresenter::InstDefaultsFlag:
    getInstDefaults();
    break;
  case IReflSettingsPresenter::SettingsChangedFlag:
    handleSettingsChanged();
    break;
  case IReflSettingsPresenter::SummationTypeChanged:
    handleSummationTypeChange();
    break;
  }
  // Not having a 'default' case is deliberate. gcc issues a warning if there's
  // a flag we aren't handling.
}

void ReflSettingsPresenter::handleSettingsChanged() {
  m_tabPresenter->settingsChanged(m_group);
}

void ReflSettingsPresenter::acceptTabPresenter(
    IReflSettingsTabPresenter *tabPresenter) {
  m_tabPresenter = tabPresenter;
}

bool ReflSettingsPresenter::hasReductionTypes(
    const std::string &summationType) const {
  return summationType == "SumInQ";
}

void ReflSettingsPresenter::handleSummationTypeChange() {
  auto summationType = m_view->getSummationType();
  m_view->setReductionTypeEnabled(hasReductionTypes(summationType));
}

/** Sets the current instrument name and changes accessibility status of
* the polarisation corrections option in the view accordingly
* @param instName :: [input] The name of the instrument to set to
*/
void ReflSettingsPresenter::setInstrumentName(const std::string &instName) {
  m_currentInstrumentName = instName;
  bool enable = instName != "INTER" && instName != "SURF";
  m_view->setIsPolCorrEnabled(enable);
  m_view->setPolarisationOptionsEnabled(enable);
}

OptionsQMap ReflSettingsPresenter::transmissionOptionsMap() const {
  OptionsQMap options;
  addTransmissionOptions(options, {"AnalysisMode", "StartOverlap", "EndOverlap",
                                   "MonitorIntegrationWavelengthMin",
                                   "MonitorIntegrationWavelengthMax",
                                   "MonitorBackgroundWavelengthMin",
                                   "MonitorBackgroundWavelengthMax",
                                   "WavelengthMin", "WavelengthMax",
                                   "I0MonitorIndex", "ProcessingInstructions"});
  return options;
}

/** Returns global options for 'CreateTransmissionWorkspaceAuto'. Note that
 * this must include all applicable options, even if they are empty, because
 * the GenericDataProcessorPresenter has no other way of knowing which options
 * are applicable to the preprocessing algorithm (e.g. for options that might
 * be specified on the Runs tab instead). We get around this by providing the
 * full list here and overriding them if they also exist on the Runs tab.
 *
 * @todo This is not idea and really we should just be passing through the
 * non-preprocessed transmission runs to ReflectometryReductionOneAuto, which
 * would then run CreateTransmissionWorkspaceAuto as a child algorithm and do
 * all of this for us. However, the transmission runs would need to be loaded
 * prior to running the processing algorithm, which is not currently possible.
 * @return :: Global options for 'CreateTransmissionWorkspaceAuto'
 */
OptionsQMap ReflSettingsPresenter::getTransmissionOptions() const {

  // This step is necessessary until the issue above is addressed.
  // Otherwise either group of options may be missed out by
  // experimentSettingsEnabled or instrumentSettingsEnabled being disabled.
  OptionsQMap options = transmissionOptionsMap();

  if (m_view->experimentSettingsEnabled()) {
    setTransmissionOption(options, "AnalysisMode", m_view->getAnalysisMode());
    setTransmissionOption(options, "StartOverlap", m_view->getStartOverlap());
    setTransmissionOption(options, "EndOverlap", m_view->getEndOverlap());
  }

  if (m_view->instrumentSettingsEnabled()) {
    setTransmissionOption(options, "MonitorIntegrationWavelengthMin",
                          m_view->getMonitorIntegralMin());
    setTransmissionOption(options, "MonitorIntegrationWavelengthMax",
                          m_view->getMonitorIntegralMax());
    setTransmissionOption(options, "MonitorBackgroundWavelengthMin",
                          m_view->getMonitorBackgroundMin());
    setTransmissionOption(options, "MonitorBackgroundWavelengthMax",
                          m_view->getMonitorBackgroundMax());
    setTransmissionOption(options, "WavelengthMin", m_view->getLambdaMin());
    setTransmissionOption(options, "WavelengthMax", m_view->getLambdaMax());
    setTransmissionOption(options, "I0MonitorIndex",
                          m_view->getI0MonitorIndex());
    setTransmissionOption(options, "ProcessingInstructions",
                          m_view->getProcessingInstructions());
  }

  return options;
}

void ReflSettingsPresenter::setTransmissionOption(OptionsQMap &options,
                                                  const QString &key,
                                                  const QString &value) const {
  options[key] = value;
}

void ReflSettingsPresenter::setTransmissionOption(
    OptionsQMap &options, const QString &key, const std::string &value) const {
  options[key] = QString::fromStdString(value);
}

void ReflSettingsPresenter::addTransmissionOptions(
    OptionsQMap &options, std::initializer_list<QString> keys) const {
  for (auto &&key : keys)
    setTransmissionOption(options, key, QString());
}

void ReflSettingsPresenter::addIfNotEmpty(OptionsQMap &options,
                                          const QString &key,
                                          const QString &value) const {
  if (!value.isEmpty())
    setTransmissionOption(options, key, value);
}

void ReflSettingsPresenter::addIfNotEmpty(OptionsQMap &options,
                                          const QString &key,
                                          const std::string &value) const {
  if (!value.empty())
    setTransmissionOption(options, key, value);
}

QString ReflSettingsPresenter::asAlgorithmPropertyBool(bool value) {
  return value ? "1" : "0";
}

/** Returns global options for 'ReflectometryReductionOneAuto'
 * @return :: Global options for 'ReflectometryReductionOneAuto'
 */
OptionsQMap ReflSettingsPresenter::getReductionOptions() const {

  OptionsQMap options;

  if (m_view->experimentSettingsEnabled()) {
    addIfNotEmpty(options, "AnalysisMode", m_view->getAnalysisMode());
    addIfNotEmpty(options, "CRho", m_view->getCRho());
    addIfNotEmpty(options, "CAlpha", m_view->getCAlpha());
    addIfNotEmpty(options, "CAp", m_view->getCAp());
    addIfNotEmpty(options, "CPp", m_view->getCPp());
    addIfNotEmpty(options, "PolarizationAnalysis",
                  m_view->getPolarisationCorrections());
    addIfNotEmpty(options, "ScaleFactor", m_view->getScaleFactor());
    addIfNotEmpty(options, "MomentumTransferStep",
                  m_view->getMomentumTransferStep());
    addIfNotEmpty(options, "StartOverlap", m_view->getStartOverlap());
    addIfNotEmpty(options, "EndOverlap", m_view->getEndOverlap());
    addIfNotEmpty(options, "FirstTransmissionRun",
                  m_view->getTransmissionRuns());

    auto summationType = m_view->getSummationType();
    addIfNotEmpty(options, "SummationType", summationType);

    if (hasReductionTypes(summationType))
      addIfNotEmpty(options, "ReductionType", m_view->getReductionType());
  }

  if (m_view->instrumentSettingsEnabled()) {
    addIfNotEmpty(options, "NormalizeByIntegratedMonitors",
                  m_view->getIntMonCheck());
    addIfNotEmpty(options, "MonitorIntegrationWavelengthMin",
                  m_view->getMonitorIntegralMin());
    addIfNotEmpty(options, "MonitorIntegrationWavelengthMax",
                  m_view->getMonitorIntegralMax());
    addIfNotEmpty(options, "MonitorBackgroundWavelengthMin",
                  m_view->getMonitorBackgroundMin());
    addIfNotEmpty(options, "MonitorBackgroundWavelengthMax",
                  m_view->getMonitorBackgroundMax());
    addIfNotEmpty(options, "WavelengthMin", m_view->getLambdaMin());
    addIfNotEmpty(options, "WavelengthMax", m_view->getLambdaMax());
    addIfNotEmpty(options, "I0MonitorIndex", m_view->getI0MonitorIndex());
    addIfNotEmpty(options, "ProcessingInstructions",
                  m_view->getProcessingInstructions());
    addIfNotEmpty(options, "DetectorCorrectionType",
                  m_view->getDetectorCorrectionType());
    auto const correctDetectors =
        asAlgorithmPropertyBool(m_view->detectorCorrectionEnabled());
    options["CorrectDetectors"] = correctDetectors;
  }

  return options;
}

std::string ReflSettingsPresenter::getTransmissionRuns() const {
  if (m_view->experimentSettingsEnabled())
    return m_view->getTransmissionRuns();
  else
    return "";
}

/** Returns global options for 'Stitch1DMany'
 * @return :: Global options for 'Stitch1DMany'
 */
std::string ReflSettingsPresenter::getStitchOptions() const {

  if (m_view->experimentSettingsEnabled())
    return m_view->getStitchOptions();
  else
    return "";
}

/** Creates hints for 'Stitch1DMany'
*/
void ReflSettingsPresenter::createStitchHints() {

  // The algorithm
  IAlgorithm_sptr alg = AlgorithmManager::Instance().create("Stitch1DMany");
  // The blacklist
  std::set<std::string> blacklist = {"InputWorkspaces", "OutputWorkspace",
                                     "OutputWorkspace"};
  AlgorithmHintStrategy strategy(alg, blacklist);

  m_view->createStitchHints(strategy.createHints());
}

template <typename T>
boost::optional<T> firstFromParameterFile(Instrument_const_sptr instrument,
                                          std::string const &parameterName) {
  return first(getInstrumentParameter<T>(instrument, parameterName));
}

class InstrumentParameters {
public:
  explicit InstrumentParameters(Instrument_const_sptr instrument)
      : m_instrument(std::move(instrument)) {}

  template <typename T> T valueOrEmpty(std::string const &parameterName) {
    static_assert(!std::is_arithmetic<T>::value, "Use valueOrZero instead.");
    return valueFromFileOrDefaultConstruct<T>(parameterName);
  }

  template <typename T> T valueOrZero(std::string const &parameterName) {
    static_assert(std::is_arithmetic<T>::value, "Use valueOrEmpty instead.");
    return valueFromFileOrDefaultConstruct<T>(parameterName);
  }

  template <typename T>
  boost::optional<T> optional(std::string const &parameterName) {
    return valueFromFile<T>(parameterName);
  }

  template <typename T> T mandatory(std::string const &parameterName) {
    if (auto value = firstFromParameterFile<T>(m_instrument, parameterName)) {
      return value.get();
    } else {
      m_missingValueErrors.emplace_back(parameterName);
      return T();
    }
  }

  std::vector<InstrumentParameterTypeMissmatch> const &typeErrors() const {
    return m_typeErrors;
  }
  bool hasTypeErrors() const { return !m_typeErrors.empty(); }

  std::vector<MissingInstrumentParameterValue> const &missingValues() const {
    return m_missingValueErrors;
  }
  bool hasMissingValues() const { return !m_missingValueErrors.empty(); }

private:
  template <typename T>
  T valueFromFileOrDefaultConstruct(std::string const &parameterName) {
    return valueFromFile<T>(parameterName).value_or(T());
  }

  template <typename T>
  boost::optional<T> valueFromFile(std::string const &parameterName) {
    try {
      return firstFromParameterFile<T>(m_instrument, parameterName);
    } catch (InstrumentParameterTypeMissmatch const &ex) {
      m_typeErrors.emplace_back(ex);
      return boost::none;
    }
  }

  Instrument_const_sptr m_instrument;
  std::vector<InstrumentParameterTypeMissmatch> m_typeErrors;
  std::vector<MissingInstrumentParameterValue> m_missingValueErrors;
};

/** Fills experiment settings with default values
*/
void ReflSettingsPresenter::getExpDefaults() {
  auto alg = createReductionAlg();
  auto instrument = createEmptyInstrument(m_currentInstrumentName);
  auto parameters = InstrumentParameters(instrument);

  auto defaults = ExperimentOptionDefaults();

  defaults.AnalysisMode = parameters.optional<std::string>("AnalysisMode")
                              .value_or(alg->getPropertyValue("AnalysisMode"));
  defaults.PolarizationAnalysis =
      parameters.optional<std::string>("PolarizationAnalysis")
          .value_or(alg->getPropertyValue("PolarizationAnalysis"));

  defaults.CRho = parameters.optional<std::string>("crho").value_or("1");
  defaults.CAlpha = parameters.optional<std::string>("calpha").value_or("1");
  defaults.CAp = parameters.optional<std::string>("cAp").value_or("1");
  defaults.CPp = parameters.optional<std::string>("cPp").value_or("1");

  defaults.MomentumTransferStep = parameters.optional<double>("dQ/Q");
  defaults.ScaleFactor = parameters.optional<double>("Scale");
  defaults.StitchParams = parameters.optional<std::string>("Params");

  if (m_currentInstrumentName != "SURF" && m_currentInstrumentName != "CRISP") {
    defaults.TransRunStartOverlap =
        parameters.optional<double>("TransRunStartOverlap");
    defaults.TransRunEndOverlap =
        parameters.optional<double>("TransRunEndOverlap");
  } else {
    defaults.TransRunStartOverlap =
        parameters.mandatory<double>("TransRunStartOverlap");
    defaults.TransRunEndOverlap =
        parameters.mandatory<double>("TransRunEndOverlap");
  }

  m_view->setExpDefaults(std::move(defaults));

  if (parameters.hasTypeErrors() || parameters.hasMissingValues()) {
    m_view->showOptionLoadErrors(parameters.typeErrors(),
                                 parameters.missingValues());
  }
}

/** Fills instrument settings with default values
*/
void ReflSettingsPresenter::getInstDefaults() {
  auto alg = createReductionAlg();
  auto instrument = createEmptyInstrument(m_currentInstrumentName);
  auto parameters = InstrumentParameters(instrument);
  auto defaults = InstrumentOptionDefaults();

  defaults.NormalizeByIntegratedMonitors =
      parameters.optional<bool>("IntegratedMonitors")
          .value_or(boost::lexical_cast<bool>(
              alg->getPropertyValue("NormalizeByIntegratedMonitors")));
  defaults.MonitorIntegralMin =
      parameters.mandatory<double>("MonitorIntegralMin");
  defaults.MonitorIntegralMax =
      parameters.mandatory<double>("MonitorIntegralMax");
  defaults.MonitorBackgroundMin =
      parameters.mandatory<double>("MonitorBackgroundMin");
  defaults.MonitorBackgroundMax =
      parameters.mandatory<double>("MonitorBackgroundMax");
  defaults.LambdaMin = parameters.mandatory<double>("LambdaMin");
  defaults.LambdaMax = parameters.mandatory<double>("LambdaMax");
  defaults.I0MonitorIndex = parameters.mandatory<int>("I0MonitorIndex");
  defaults.ProcessingInstructions =
      parameters.optional<std::string>("ProcessingInstructions");
  defaults.DetectorCorrectionType =
      parameters.optional<std::string>("DetectorCorrectionType")
          .value_or(alg->getPropertyValue("DetectorCorrectionType"));

  m_view->setInstDefaults(std::move(defaults));

  if (parameters.hasTypeErrors() || parameters.hasMissingValues()) {
    m_view->showOptionLoadErrors(parameters.typeErrors(),
                                 parameters.missingValues());
  }
}

/** Generates and returns an instance of the ReflectometryReductionOneAuto
* algorithm
* @return :: ReflectometryReductionOneAuto algorithm
*/
IAlgorithm_sptr ReflSettingsPresenter::createReductionAlg() {
  return AlgorithmManager::Instance().create("ReflectometryReductionOneAuto");
}

/** Creates and returns an example empty instrument given an instrument name
* @return :: Empty instrument of a name
*/
Instrument_const_sptr
ReflSettingsPresenter::createEmptyInstrument(const std::string &instName) {
  IAlgorithm_sptr loadInst =
      AlgorithmManager::Instance().create("LoadEmptyInstrument");
  loadInst->setChild(true);
  loadInst->setProperty("OutputWorkspace", "outWs");
  loadInst->setProperty("InstrumentName", instName);
  loadInst->execute();
  MatrixWorkspace_const_sptr ws = loadInst->getProperty("OutputWorkspace");
  return ws->getInstrument();
}
}
}
