#include "MantidKernel/WarningSuppressions.h"
//------------------------------------------------------------------------------
// This is a global 'include' file for the GSoap generated files in order to
// disable some warnings that we understand but do not want to touch as
// it is automatically generated code
//------------------------------------------------------------------------------
DIAG_OFF("cast-qual")
DIAG_OFF("conversion")
DIAG_OFF("unused-parameter")
DIAG_OFF("strict-aliasing")
DIAG_OFF("format")
DIAG_OFF("vla")
#if GCC_VERSION >= 40800 // 4.8.0
DIAG_OFF("literal-suffix")
#endif
#ifdef _WIN32
#pragma warning(disable : 4100)
#endif

#include "GSoapGenerated/ICat4C.cpp"
#include "GSoapGenerated/ICat4ICATPortBindingProxy.cpp"
