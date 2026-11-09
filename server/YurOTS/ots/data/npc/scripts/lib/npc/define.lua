-- npcDefine: arma los callbacks que npc.cpp llama (onCreatureSay, onThink, ...) a partir
-- de una descripción. Cada NPC declara solo lo suyo; el resto es igual para todos.
-- Parte de lib/npc.lua (ver docs/gameplay/NPC_SYSTEM.md).
--
-- npcDefine{
--   greet   = string | function(cid)    saludo al decir hi/hola (obligatorio salvo con onSay)
--   busy    = string | function(cid)    si ya atiende a otro (default: "One moment, <name>! ...")
--   bye     = string | function(cid)    despedida (default: "Bye, <name>! ...")
--   state   = {talk_state = 0, ...}     globales propias del NPC con su valor inicial
--   onMessage = function(cid, msg)      mensaje del jugador atendido (msg ya en minúsculas)
--   onGreet   = function(cid)           al empezar la charla (p. ej. limpiar pendientes)
--   onLeave   = function(cid)           si el jugador atendido desaparece (antes del cierre)
--   idleTimeout, idleMessage            timeout de la charla (default 30 s, "Next please...")
--   -- solo para NPCs con comportamiento propio:
--   onSay       = function(cid, msg)    reemplaza todo el manejo de mensajes
--   onThink     = function()            reemplaza el think por defecto
--   onAppear    = function(creature)
--   onDisappear = function(cid, pos)    reemplaza el manejo por defecto
-- }

local function npcResolveText(value, cid)
	if type(value) == 'function' then
		return value(cid)
	end
	return value
end

function npcDefine(spec)
	focus = 0
	talk_start = 0
	target = 0
	following = false
	attacking = false
	if spec.state ~= nil then
		for name, value in pairs(spec.state) do
			_G[name] = value
		end
	end

	function onThingMove(creature, thing, oldpos, oldstackpos)
	end

	function onCreatureTurn(creature)
	end

	function onCreatureChangeOutfit(creature)
	end

	function onCreatureAppear(creature)
		if spec.onAppear ~= nil then
			spec.onAppear(creature)
		end
	end

	function onCreatureDisappear(cid, pos)
		if spec.onDisappear ~= nil then
			spec.onDisappear(cid, pos)
			return
		end
		if spec.onLeave ~= nil and focus == cid then
			spec.onLeave(cid)
		end
		npcOnCreatureDisappear(cid)
	end

	function onThink()
		if spec.onThink ~= nil then
			spec.onThink()
			return
		end
		npcOnThink(spec.idleTimeout, spec.idleMessage)
	end

	function onCreatureSay(cid, msgType, msg)
		msg = string.lower(msg)
		if spec.onSay ~= nil then
			spec.onSay(cid, msg)
			return
		end

		local state = npcHandleMessage(cid, msg, npcResolveText(spec.greet, cid),
			npcResolveText(spec.busy, cid), npcResolveText(spec.bye, cid))
		if state == 'greet' and spec.onGreet ~= nil then
			spec.onGreet(cid)
			return
		end
		if state ~= 'focused' then
			return
		end
		spec.onMessage(cid, msg)
	end
end

-- Tienda estándar: ayuda -> compra (con cantidad) -> venta -> respuesta por tema.
-- npcCatalogHandler{help = '...', helpKeys = {'ammo'}, buys = {...}, sells = {...}, topics = {...}, maxQty = 100}
-- Devuelve una función onMessage(cid, msg) que retorna true si atendió el mensaje.
function npcCatalogHandler(shop)
	return function(cid, msg)
		if npcIsHelp(msg) or (shop.helpKeys ~= nil and npcMatchesAny(msg, shop.helpKeys)) then
			selfSay(shop.help)
			return true
		end
		if shop.buys ~= nil and npcTryCatalogBuyQuantity(cid, msg, shop.buys, shop.maxQty) then
			return true
		end
		if shop.sells ~= nil and npcTryCatalogSell(cid, msg, shop.sells) then
			return true
		end
		if shop.topics ~= nil and npcTryCatalogReply(msg, shop.topics) then
			return true
		end
		return false
	end
end
