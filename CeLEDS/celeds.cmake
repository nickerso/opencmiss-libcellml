DECLARE_EXTENSION(celeds)
DECLARE_IDL(CeLEDS)
DECLARE_IDL_DEPENDENCY(MaLaES)
DECLARE_IDL_DEPENDENCY(CellML_APISPEC)
DECLARE_EXTENSION_END(celeds)

INCLUDE_DIRECTORIES(CeLEDS/sources)

ADD_LIBRARY(celeds
  CeLEDS/sources/CeLEDSImpl.cpp)
TARGET_LINK_LIBRARIES(celeds cellml malaes)
INSTALL(TARGETS celeds DESTINATION lib)

DECLARE_BOOTSTRAP("CeLEDSBootstrap" "CeLEDS" "CeLEDSBootstrap" "cellml_services" "createCeLEDSBootstrap" "CreateCeLEDSBootstrap" "CeLEDSBootstrap.hpp" "CeLEDS/sources" "celeds")
