focus = 0
talk_start = 0
target = 0
following = false
attacking = false

RUNES_HELP = 'Runes: HMM 5gp, UH 40gp, GFB 60gp, explosion 60gp, SD 90gp, blank 5gp. Say "10 uh" or "100 sd" for bulk. Mana fluid 100gp, strong mana potion (SMP) 250gp. Say "wands" or "rods" for magic weapons.'

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
		'Hi ' .. creatureGetName(cid) .. '! I sell runes, mana fluids, strong mana potions, wands and rods. Say "help" for prices.'
	)
	if state ~= 'focused' then
		return
	end

	if npcIsHelp(msg) or msgcontains(msg, 'runes') then
		selfSay(RUNES_HELP)
	elseif msgcontains(msg, 'potions') or msgcontains(msg, 'potion') then
		selfSay('Mana fluid: 100gp. Strong mana potion: 250gp. Say "mana fluid" or "smp".')
	elseif msgcontains(msg, 'wands') then
		selfSay('Wands: inferno 15k, plague 5k, cosmic energy 10k, vortex 500gp, dragonbreath 1k.')
	elseif msgcontains(msg, 'rods') then
		selfSay('Rods: quagmire 10k, snakebite 500gp, tempest 15k, volcanic 5k, moonlight 1k.')
	elseif msgcontains(msg, 'inferno') then
		buy(cid, 2187, 1, 15000)
	elseif msgcontains(msg, 'plague') then
		buy(cid, 2188, 1, 5000)
	elseif msgcontains(msg, 'cosmic energy') then
		buy(cid, 2189, 1, 10000)
	elseif msgcontains(msg, 'vortex') then
		buy(cid, 2190, 1, 500)
	elseif msgcontains(msg, 'dragonbreath') then
		buy(cid, 2191, 1, 1000)
	elseif msgcontains(msg, 'quagmire') then
		buy(cid, 2181, 1, 10000)
	elseif msgcontains(msg, 'snakebite') then
		buy(cid, 2182, 1, 500)
	elseif msgcontains(msg, 'tempest') then
		buy(cid, 2183, 1, 15000)
	elseif msgcontains(msg, 'volcanic') then
		buy(cid, 2185, 1, 5000)
	elseif msgcontains(msg, 'moonlight') then
		buy(cid, 2186, 1, 1000)
	elseif msgcontains(msg, '100 hmm') then
		buy(cid, 2311, 100, 800)
	elseif msgcontains(msg, '10 hmm') then
		buy(cid, 2311, 10, 80)
	elseif msgcontains(msg, 'hmm') then
		buy(cid, 2311, 5, 40)
	elseif msgcontains(msg, '100 uh') then
		buy(cid, 2273, 100, 4000)
	elseif msgcontains(msg, '10 uh') then
		buy(cid, 2273, 10, 400)
	elseif msgcontains(msg, 'uh') then
		buy(cid, 2273, 1, 40)
	elseif msgcontains(msg, '100 gfb') then
		buy(cid, 2304, 100, 2000)
	elseif msgcontains(msg, '10 gfb') then
		buy(cid, 2304, 10, 200)
	elseif msgcontains(msg, 'gfb') then
		buy(cid, 2304, 3, 60)
	elseif msgcontains(msg, '100 explosion') then
		buy(cid, 2313, 100, 2000)
	elseif msgcontains(msg, '10 explosion') then
		buy(cid, 2313, 10, 200)
	elseif msgcontains(msg, 'explosion') then
		buy(cid, 2313, 3, 60)
	elseif msgcontains(msg, '100 sd') then
		buy(cid, 2268, 100, 9000)
	elseif msgcontains(msg, '10 sd') then
		buy(cid, 2268, 10, 900)
	elseif msgcontains(msg, 'sd') then
		buy(cid, 2268, 1, 90)
	elseif msgcontains(msg, 'blank') then
		buy(cid, 2260, 1, 5)
	elseif msgcontains(msg, 'strong mana potion') or msgcontains(msg, 'smp') or msgcontains(msg, 'strong mana') then
		buy(cid, 2006, 14, 250)
	elseif msgcontains(msg, 'manafluid') or msgcontains(msg, 'mana fluid') or msgcontains(msg, 'mana') then
		buy(cid, 2006, 7, 100)
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
