-- Biblioteca de NPCs. npc.cpp la carga en el estado Lua de cada NPC antes de su script.
-- Diálogos en inglés; acepta respuestas del jugador en inglés y español.
--
-- Componentes (cada uno en lib/npc/):
--   core.lua          distancia, movimiento, msgcontains
--   intents.lua       saludo / despedida / sí / no / ayuda
--   conversation.lua  foco, saludo-ocupado-despedida, timeout, confirmaciones sí/no
--   catalog.lua       compra/venta por catálogo, cantidades
--   text.lua          recortar texto, montos de oro ("all"/"todo"), formato de precios
--   define.lua        npcDefine{...} y npcCatalogHandler{...}: arman los callbacks del NPC
--
-- Documentación: docs/gameplay/NPC_SYSTEM.md. Pruebas: python3 scripts/npc/run_npc_tests.py

local NPC_LIB = 'data/npc/scripts/lib/npc/'
dofile(NPC_LIB .. 'core.lua')
dofile(NPC_LIB .. 'intents.lua')
dofile(NPC_LIB .. 'conversation.lua')
dofile(NPC_LIB .. 'catalog.lua')
dofile(NPC_LIB .. 'text.lua')
dofile(NPC_LIB .. 'define.lua')
