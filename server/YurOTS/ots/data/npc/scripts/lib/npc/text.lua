-- Texto y montos de oro: recortar espacios, leer "10000" / "all" / "todo", formatear precios.
-- Parte de lib/npc.lua (ver docs/gameplay/NPC_SYSTEM.md).

function npcTrim(text)
	if text == nil then
		return ''
	end
	text = string.gsub(text, '^%s+', '')
	text = string.gsub(text, '%s+$', '')
	return text
end

-- Monto de oro escrito por el jugador. "all"/"todo" = todo lo que tiene en `source`
-- ('money' = encima, cualquier otro valor = banco). nil si no es un monto válido (> 0).
function npcResolveGoldAmount(cid, text, source)
	text = npcTrim(text)
	if text == '' then
		return nil
	end

	if text == 'all' or text == 'todo' then
		if source == 'money' then
			return getPlayerMoney(cid)
		end
		return getPlayerBankBalance(cid)
	end

	local amount = tonumber(text)
	if amount == nil then
		return nil
	end

	amount = math.floor(amount)
	if amount <= 0 then
		return nil
	end

	return amount
end

-- 1500 -> "1.5k", 2000 -> "2k", 250 -> "250gp".
function npcFormatPrice(p)
	if p >= 1000 then
		local k = p / 1000
		if k == math.floor(k) then
			return tostring(k) .. 'k'
		end
		return string.format('%.1fk', k)
	end
	return tostring(p) .. 'gp'
end
