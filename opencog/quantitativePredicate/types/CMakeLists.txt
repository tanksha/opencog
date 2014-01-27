#SET_DIRECTORY_PROPERTIES(PROPERTIES CLEAN_NO_CUSTOM true)
OPENCOG_ADD_ATOM_TYPES(
	atom_types.script
	atom_types.h
	atom_types.definitions
	atom_types.inheritance
	quantitative_types.scm
)
ADD_CUSTOM_TARGET(quantitative_atom_types DEPENDS atom_types.h)

# The atom_types.h file is written to the build directory
INCLUDE_DIRECTORIES(${CMAKE_BINARY_DIR})

ADD_LIBRARY (quantitative-types SHARED
	atom_types
	QuantitativeTypes
)

# Without this, parallel make will race and crap up the generated files.
ADD_DEPENDENCIES(quantitative-types quantitative_atom_types)

IF (WIN32)
    INSTALL (TARGETS quantitative-types DESTINATION "lib${LIB_DIR_SUFFIX}/opencog")
ELSEIF (CYGWIN)
    INSTALL (TARGETS quantitative-types DESTINATION "lib${LIB_DIR_SUFFIX}/opencog")
ELSE (WIN32)
    INSTALL (TARGETS quantitative-types LIBRARY DESTINATION "lib${LIB_DIR_SUFFIX}/opencog")
ENDIF (WIN32)

INSTALL (FILES
	${CMAKE_CURRENT_BINARY_DIR}/atom_types.h
	DESTINATION "include/${PROJECT_NAME}/quantitativePredicate/types"
)
