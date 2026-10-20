#pragma once

// Supply missing platform declarations without modifying the pinned upstream files.
#include <optional>

#ifdef __APPLE__
#define fseeko64 fseeko
#endif
