-- Catálogos de compra/venta: {keys=..., itemid=..., unitPrice|price=...}. Cantidades ("5 ham"), fluidos, runas y respuestas por tema.
-- Parte de lib/npc.lua (ver docs/gameplay/NPC_SYSTEM.md).


function npcTryCatalogReply(msg, entries)
	local entry = npcFindCatalogEntry(msg, entries)
	if entry and entry.reply then
		selfSay(entry.reply)
		return true
	end

	return false
end

function npcParseBuyQuantity(msg, maxQty)
	maxQty = maxQty or 100
	local qty = tonumber(string.match(msg, '(%d+)'))
	if qty == nil or qty < 1 then
		return 1
	end
	if qty > maxQty then
		return maxQty
	end
	return qty
end

-- Palabras que pueden rodear a una clave corta sin cambiarle el sentido ("sell 2 life please").
NPC_FILLER_WORDS = {}
for _, w in ipairs({'a', 'an', 'the', 'my', 'some', 'of', 'sell', 'buy', 'want', 'i', 'please', 'all', 'x',
		'un', 'una', 'unos', 'unas', 'mi', 'mis', 'el', 'la', 'los', 'las', 'de', 'vender', 'vendo', 'comprar',
		'compro', 'quiero', 'todo', 'todos', 'todas', 'por', 'favor'}) do
	NPC_FILLER_WORDS[w] = true
end

local function isFillerWord(word)
	return word == nil or NPC_FILLER_WORDS[word] or string.find(word, '^%d+$') ~= nil
end

-- Una clave corta ("life", "sword") solo vale si las palabras vecinas son relleno o números:
-- "2 life" compra, "what time is it" o "magic sword" no.
local function isAlone(msg, s, e)
	local before = string.match(string.sub(msg, 1, s - 1), '(%w+)%W*$')
	local after = string.match(string.sub(msg, e + 1), '^%W*(%w+)')
	return isFillerWord(before) and isFillerWord(after)
end

-- Dónde aparece la clave como palabra(s) completa(s), también en plural ("bows", "hams",
-- "torches"). Devuelve inicio, largo de la clave y si fue plural; nil si no aparece.
local function findKey(msg, key, alone)
	local start, len = 1, string.len(msg)
	while true do
		local s, e = string.find(msg, key, start, true)
		if not s then
			return nil
		end
		local plural = false
		if string.sub(msg, e + 1, e + 1) == 's' then
			plural, e = true, e + 1
		elseif string.sub(msg, e + 1, e + 2) == 'es' then
			plural, e = true, e + 2
		end
		local leftOk = s == 1 or string.find(string.sub(msg, s - 1, s - 1), '%W') ~= nil
		local rightOk = e >= len or string.find(string.sub(msg, e + 1, e + 1), '%W') ~= nil
		if not rightOk and plural then	-- "bolts" no es plural de "bolt" si sigue una letra
			e = s + string.len(key) - 1
			plural = false
			rightOk = e >= len or string.find(string.sub(msg, e + 1, e + 1), '%W') ~= nil
		end
		if leftOk and rightOk and (not alone or isAlone(msg, s, e)) then
			return s, string.len(key), plural
		end
		start = s + 1
	end
end

-- Mejor coincidencia de una entrada: keys normales y shortKeys (claves cortas que tienen que
-- ir solas, ver isAlone).
function npcFindMatchOffset(msg, keys, shortKeys)
	local best, bestLen, bestPlural = nil, 0, false
	local function try(list, alone)
		if list == nil then
			return
		end
		if type(list) == 'string' then
			list = {list}
		end
		for i = 1, table.getn(list) do
			local s, len, plural = findKey(msg, list[i], alone)
			if s ~= nil and (best == nil or s < best or (s == best and len > bestLen)) then
				best, bestLen, bestPlural = s, len, plural
			end
		end
	end
	try(keys, false)
	try(shortKeys, true)
	return best, bestLen, bestPlural
end

-- Mejor coincidencia: la clave que aparece primero en el mensaje; a igual posición la más
-- larga ("round blue pillow" gana a "blue pillow", "fire sword" a "sword") y a igual largo la
-- exacta antes que el plural ("swords" es el tema de precios, no vender una "sword"). La usan
-- compra, venta y temas, así el resultado no depende del orden de la tabla. Acepta varias
-- listas: npcFindCatalogEntry(msg, ventas, temas).
function npcFindCatalogEntry(msg, ...)
	local best = nil
	local bestOffset, bestLen, bestPlural = math.huge, 0, true
	for l = 1, select('#', ...) do
		local entries = select(l, ...)
		for i = 1, table.getn(entries or {}) do
			local entry = entries[i]
			local offset, len, plural = npcFindMatchOffset(msg, entry.keys, entry.shortKeys)
			if offset ~= nil and (offset < bestOffset
					or (offset == bestOffset and (len > bestLen or (len == bestLen and bestPlural and not plural)))) then
				best, bestOffset, bestLen, bestPlural = entry, offset, len, plural
			end
		end
	end
	return best
end

-- Nombre anterior (algunos scripts lo usan).
npcFindCatalogBuyEntry = npcFindCatalogEntry

function npcTryCatalogBuyQuantity(cid, msg, entries, maxQty)
	local entry = npcFindCatalogEntry(msg, entries)
	if entry == nil then
		return false
	end

	local qty = npcParseBuyQuantity(msg, maxQty)

	-- Sin ningún lugar libre no tiene sentido preguntar. No se exige un lugar por unidad: los
	-- apilables ("50 arrows") ocupan uno solo, y si falta lugar el C++ entrega lo que entra y
	-- devuelve el resto del oro.
	if getPlayerFreeSlots(cid) < 1 then
		selfSay('You do not have enough space in your backpack for that. Free up some slots first.')
		return true
	end

	if entry.fluidSubtype ~= nil then
		buyFluidQty(cid, entry.itemid, entry.fluidSubtype, qty, entry.unitPrice * qty)
	elseif entry.runeCharges ~= nil then
		buyRuneQty(cid, entry.itemid, qty, entry.runeCharges, entry.unitPrice * qty)
	elseif entry.itemQuantity ~= nil then
		buyItemQty(cid, entry.itemid, qty, entry.unitPrice * qty)
	else
		buy(cid, entry.itemid, qty, entry.unitPrice * qty)
	end
	return true
end

-- Cantidad a vender: "3 swords", "sell 3 sword" o "all"/"todo" (todos los que tenga).
function npcParseSellQuantity(cid, msg, entry)
	if npcMatchesAny(msg, {'all', 'todo', 'todos', 'todas'}) then
		return getPlayerItemCount(cid, entry.itemid)
	end
	return npcParseBuyQuantity(msg, 100)
end

function npcSellEntry(cid, msg, entry)
	local qty = entry.count or npcParseSellQuantity(cid, msg, entry)
	if qty < 1 then
		selfSay('You do not have any ' .. (entry.keys or entry.shortKeys)[1] .. '.')
		return
	end
	sell(cid, entry.itemid, qty, entry.price * qty)
end

function npcTryCatalogSell(cid, msg, entries)
	local entry = npcFindCatalogEntry(msg, entries)
	if entry then
		npcSellEntry(cid, msg, entry)
		return true
	end

	return false
end
