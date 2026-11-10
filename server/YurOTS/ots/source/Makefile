# Makefile for YurOTS (legacy OTServ 7.6) on Linux/gcc
# Generated for the Docker build. XML-based accounts (no MySQL).

CXX      = g++
LOCAL_PREFIX ?= $(shell if [ -d /opt/homebrew ]; then echo /opt/homebrew; elif [ -d /usr/local ]; then echo /usr/local; else echo /usr; fi)
LUA_CFLAGS ?= $(shell pkg-config --cflags luajit 2>/dev/null || pkg-config --cflags lua5.1 2>/dev/null || echo -I/usr/include/lua5.1)
LUA_LIBS   ?= $(shell pkg-config --libs luajit 2>/dev/null || pkg-config --libs lua5.1 2>/dev/null || echo -llua5.1)
# Las 54 opciones -DYUR_*/TLM_*/... que iban acá estaban siempre activas: su código quedó fijo
# con unifdef (nov 2026) y los bloques que nunca se activaban se borraron.
# Optimizado (antes -O0, el modo de depurar). -g deja los símbolos para leer crashes con gdb y
# addr2line; -fno-strict-aliasing evita que -O2 rompa código viejo que reinterpreta punteros.
# Para depurar paso a paso: make OPT=-O0
OPT     ?= -O2
CXXFLAGS = -g $(OPT) -fno-strict-aliasing -std=gnu++14 -Wno-deprecated -fpermissive \
           -include linux_compat.h \
           -I/usr/include/libxml2 -I$(LOCAL_PREFIX)/include $(LUA_CFLAGS) \
           -D_atoi64=atoll \
           -Dlua_dofile=luaL_dofile \
           -Dluaopen_loadlib=luaopen_package

LDFLAGS  = -L$(LOCAL_PREFIX)/lib -lxml2 $(LUA_LIBS) -lboost_regex -lpthread -lz

SRCS     = $(filter-out mdump.cpp, $(wildcard *.cpp))
OBJS     = $(SRCS:.cpp=.o)
TARGET   = yurots

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) -o $@ $(OBJS) $(LDFLAGS)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c -o $@ $<

clean:
	rm -f $(OBJS) $(TARGET) otserv.map

.PHONY: all clean
