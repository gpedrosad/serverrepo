focus = 0
talk_start = 0
target = 0
following = false
attacking = false
talk_state = 0

function onThingMove(creature, thing, oldpos, oldstackpos)
end

function onCreatureAppear(creature)
end

function onCreatureDisappear(cid, pos)
	npcOnCreatureDisappear(cid)
end

function onCreatureTurn(creature)
end

function onCreatureSay(cid, type, msg)
	msg = string.lower(msg)

	local state = npcHandleMessage(
		cid,
		msg,
		'Hola ' .. creatureGetName(cid) .. '. Gestiono la promotion. Di "promotion" si te interesa.'
	)
	if state ~= 'focused' then
		return
	end

	if talk_state == 1 then
		if npcHandlePendingYesNo(cid, msg, function()
			if not isPremium(cid) then
				selfSay('Necesitas premium activo para comprar la promotion.')
				return
			end
			if pay(cid, 20000) then
				selfSay('/promote ' .. creatureGetName(cid))
				if isPromoted(cid) then
					selfSay('Felicidades! Ya tienes promotion.')
				else
					selfSay('No se pudo completar la promotion. Necesitas premium activo.')
				end
			else
				selfSay('Necesitas 20,000 gold.')
			end
		end) then
			talk_state = 0
		end
		return
	end

	if msgcontains(msg, 'promotion') or msgcontains(msg, 'promote') then
		if isPromoted(cid) then
			selfSay('Ya tienes promotion.')
		elseif getPlayerLevel(creatureGetName(cid)) < 20 then
			selfSay('Necesitas nivel 20 para la promotion.')
		elseif not isPremium(cid) then
			selfSay('Necesitas premium activo. Puedes donar por premium en retro76.cl.')
		else
			selfSay('La promotion cuesta 20,000 gp. Quieres comprarla? (yes o si)')
			talk_state = 1
		end
	elseif msgcontains(msg, 'premium') or msgcontains(msg, 'premmy') then
		selfSay('Donacion premium en retro76.cl. Usa !premmy para ver el tiempo restante.')
	elseif npcIsHelp(msg) then
		selfSay('Promotion: 20,000 gp, nivel 20 y cuenta premium activa.')
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
