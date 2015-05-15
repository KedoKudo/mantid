#include "MantidGeometry/Instrument/CompAssembly.h"
#include <boost/python/class.hpp>

using Mantid::Geometry::CompAssembly;
using Mantid::Geometry::ICompAssembly;
using Mantid::Geometry::Component;
using namespace boost::python;

/**
 * Enables boost.python to automatically "cast" an object up to the
 * appropriate CompAssembly leaf type 
 */
// clang-format off
void export_CompAssembly()
// clang-format on
{
  class_<CompAssembly, bases<ICompAssembly, Component>, boost::noncopyable>("CompAssembly", no_init)
    ;
}

