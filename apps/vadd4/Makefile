NAME = vadd4
SRCS = main.c vadd4.S
# Keep the C checking code scalar; the vector operation is explicit in vadd4.S.
CC_OPT = -O2 -fno-tree-vectorize
include $(AM_HOME)/Makefile.app
