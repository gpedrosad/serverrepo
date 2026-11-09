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

-- Tope de cualquier monto de oro: el C++ (build i386) guarda el oro en int de 32 bits.
NPC_MAX_GOLD = 1000000000

-- Monto de oro escrito por el jugador: "10000", "10k", "1kk". "all"/"todo" = todo lo que tiene
-- en `source` ('money' = encima, cualquier otro valor = banco). nil si no es un monto válido:
-- vacío, cero, negativo, decimales, notación científica ("1e12") o más de NPC_MAX_GOLD.
function npcResolveGoldAmount(cid, text, source)
	text = npcTrim(text)
	if text == 'all' or text == 'todo' then
		if source == 'money' then
			return getPlayerMoney(cid)
		end
		return getPlayerBankBalance(cid)
	end

	local digits, ks = string.match(text, '^(%d+)(k*)$')
	if digits == nil or string.len(digits) > 10 or string.len(ks) > 2 then
		return nil
	end
	local amount = tonumber(digits) * (1000 ^ string.len(ks))
	if amount <= 0 or amount > NPC_MAX_GOLD then
		return nil
	end
	return amount
end

-- 1500 -> "1.5k", 2000 -> "2k", 250 -> "250gp", 5010 -> "5010gp" (no se redondea a "5.0k").
function npcFormatPrice(p)
	if p >= 1000 and math.fmod(p, 100) == 0 then
		local k = p / 1000
		if k == math.floor(k) then
			return tostring(k) .. 'k'
		end
		return string.format('%.1fk', k)
	end
	return tostring(p) .. 'gp'
end
