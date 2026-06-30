# Makefile for YurOTS (legacy OTServ 7.6) on Linux/gcc
# Generated for the Docker build. XML-based accounts (no MySQL).

CXX      = g++
CXXFLAGS = -g -O0 -std=gnu++14 -Wno-deprecated -fpermissive \
           -include linux_compat.h \
           -I/usr/include/libxml2 -I/usr/include/lua5.1 \
           -DEXCEPTION_TRACER -DTLM_BUY_SELL -DTLM_SERVER_SAVE -DTLM_HOUSE_SYSTEM \
           -DBDB_UTEVO_LUX -DWOLV_LOAD_NPC -DBD_HOUSE_WINDOW -DTR_ANTI_AFK_DISABLED \
           -DELEM_VIP_LIST -DTR_SUMMONS -DTRS_GM_INVISIBLE -DTLM_SKULLS_PARTY \
           -DBRN_EXIVA -DSD_BURST_ARROW -DBDB_REPLACE_SPEARS -DBD_ITEM_LOOK \
           -DSM_RELOAD_CONFIG -DJD_DEATH_LIST -DCT_EXANI_TERA -DCVS_DAY_CYCLE \
           -DTJ_MONSTER_BLOOD -DJD_WANDS -D__DEBUG_PLAYERS__ -DYUR_CVS_MODS \
           -DYUR_ICE_RAPIER -DYUR_AOL -DYUR_LOGIN_QUEUE -DYUR_MULTIPLIERS \
           -DYUR_BOH -DYUR_SOFT_BOOTS -DYUR_NPC_EXT -DYUR_GUILD_SYSTEM -DYUR_CMD_EXT -DYUR_ITEM_EXT \
           -DYUR_ACT_EXT -DYUR_NO_MONSTER_HEAL -DYUR_PVP_ARENA -DYUR_TRAINING_AREA -DYUR_RINGS_AMULETS \
           -DYUR_CONFIG_CAP -DYUR_FIGHT_MODE -DYUR_READABLES -DYUR_LEARN_SPELLS \
           -DYUR_HEAL_EXHAUST -DYUR_SHUTDOWN -DYUR_ROOKGARD -DYUR_LIGHT_ITEM \
           -DYUR_CLEAN_MAP -DYUR_GM_LOOK -DYUR_HIGH_LEVELS -DYUR_PREMIUM_PROMOTION \
           -DYUR_INVISIBLE -DYUR_DRAINS            -DYUR_BUILTIN_AAC \
           -D_atoi64=atoll \
           -Dlua_dofile=luaL_dofile \
           -Dluaopen_loadlib=luaopen_package

LDFLAGS  = -lxml2 -llua5.1 -lboost_regex -lpthread -lz

SRCS     = $(filter-out mdump.cpp bounty.cpp, $(wildcard *.cpp))
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
