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

function npcTryCatalogBuy(cid, msg, entries)
	local entry = npcFindCatalogEntry(msg, entries)
	if entry then
		local qty = entry.count or 1
		local price = entry.price or (entry.unitPrice * qty)
		buy(cid, entry.itemid, qty, price)
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

function npcCatalogKeyLength(entry)
	local keys = entry.keys
	if type(keys) == 'string' then
		return string.len(keys)
	end

	local maxLen = 0
	for i = 1, table.getn(keys) do
		local len = string.len(keys[i])
		if len > maxLen then
			maxLen = len
		end
	end
	return maxLen
end

function npcFindMatchOffset(msg, keys)
	if type(keys) == 'string' then
		keys = {keys}
	end
	local bestOffset = nil
	local bestLen = 0
	for i = 1, table.getn(keys) do
		local key = keys[i]
		local start = 1
		while true do
			local s = string.find(msg, key, start, true)
			if not s then break end
			local leftOk = (s == 1) or string.match(string.sub(msg, s-1, s-1), '%W') ~= nil
			local e = s + string.len(key) - 1
			local rightOk = (e >= string.len(msg)) or string.match(string.sub(msg, e+1, e+1), '%W') ~= nil
			if leftOk and rightOk then
				if bestOffset == nil or s < bestOffset or (s == bestOffset and string.len(key) > bestLen) then
					bestOffset = s
					bestLen = string.len(key)
				end
			end
			start = s + 1
		end
	end
	return bestOffset, bestLen
end

-- Mejor coincidencia: la clave que aparece primero en el mensaje y, a igual posición, la más
-- larga ("round blue pillow" gana a "blue pillow", "fire sword" a "sword"). La usan compra,
-- venta y temas, así el resultado no depende del orden de la tabla.
function npcFindCatalogEntry(msg, entries)
	local best = nil
	local bestOffset = math.huge
	local bestLen = 0

	for i = 1, table.getn(entries) do
		local entry = entries[i]
		local offset, len = npcFindMatchOffset(msg, entry.keys)
		if offset ~= nil then
			if offset < bestOffset or (offset == bestOffset and len > bestLen) then
				best = entry
				bestOffset = offset
				bestLen = len
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

function npcTryCatalogSell(cid, msg, entries)
	local entry = npcFindCatalogEntry(msg, entries)
	if entry then
		sell(cid, entry.itemid, entry.count or 1, entry.price)
		return true
	end

	return false
end
