-- Intenciones del jugador (inglés y español): saludo, despedida, sí, no, ayuda.
-- Parte de lib/npc.lua (ver docs/gameplay/NPC_SYSTEM.md).

function npcIsGreeting(msg)
	return msgcontains(msg, 'hi') or msgcontains(msg, 'hola') or msgcontains(msg, 'buenas') or msgcontains(msg, 'hey')
end

function npcIsFarewell(msg)
	return msgcontains(msg, 'bye') or msgcontains(msg, 'adios') or msgcontains(msg, 'chau') or msgcontains(msg, 'chao')
end

function npcIsYes(msg)
	if msg == 'y' or msg == 's' or msg == 'si' or msg == 'sí' then
		return true
	end
	return msgcontains(msg, 'yes') or msgcontains(msg, 'sip') or msgcontains(msg, 'dale')
end

function npcIsNo(msg)
	if msg == 'n' then
		return true
	end
	return msgcontains(msg, 'no') or msgcontains(msg, 'nop')
end

function npcIsHelp(msg)
	return msgcontains(msg, 'help') or msgcontains(msg, 'ayuda') or msgcontains(msg, 'list')
		or msgcontains(msg, 'lista') or msgcontains(msg, 'offer') or msgcontains(msg, 'oferta')
		or msgcontains(msg, 'prices') or msgcontains(msg, 'precios') or msgcontains(msg, 'trade')
		or msgcontains(msg, 'info')
end

function npcMatchesAny(msg, keys)
	if type(keys) == 'string' then
		return msgcontains(msg, keys)
	end

	for i = 1, table.getn(keys) do
		if msgcontains(msg, keys[i]) then
			return true
		end
	end

	return false
end
