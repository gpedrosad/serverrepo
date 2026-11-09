-- Orlan (promoción: nivel 20 + 20.000 gp; info de premium).
talk_state = 0

local function onMessage(cid, msg)
	if talk_state == 1 then
		if npcHandlePendingYesNo(cid, msg, function()
			if pay(cid, 20000) then
				selfSay('/promote ' .. creatureGetName(cid))
				if isPromoted(cid) then
					selfSay('Congratulations! You are promoted.')
				else
					selfSay('Promotion failed. Try again or contact a gamemaster.')
				end
			else
				selfSay('You need 20,000 gold.')
			end
		end) then
			talk_state = 0
		end
		return
	end

	if msgcontains(msg, 'promotion') or msgcontains(msg, 'promote') then
		if isPromoted(cid) then
			selfSay('You are already promoted.')
		elseif getPlayerLevel(creatureGetName(cid)) < 20 then
			selfSay('You need level 20 for promotion.')
		else
			selfSay('Promotion costs 20,000 gp. Do you want to buy it? (yes or si)')
			talk_state = 1
		end
	elseif msgcontains(msg, 'premium') or msgcontains(msg, 'premmy') then
		selfSay('Premium donations at https://retro76.cl. Premium boosts regen further. Use !premmy to check your time.')
	elseif npcIsHelp(msg) then
		selfSay('Promotion: level 20 and 20,000 gp for everyone. Premium accounts regen faster (https://retro76.cl).')
	end
end

npcDefine{
	greet = function(cid) return 'Hello ' .. creatureGetName(cid) .. '. I handle promotions. Say "promotion" if you are interested.' end,
	onMessage = onMessage,
}
