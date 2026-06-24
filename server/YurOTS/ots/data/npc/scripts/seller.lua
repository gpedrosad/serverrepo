focus = 0
talk_start = 0
target = 0
following = false
attacking = false

SELLER_HELP = 'I sell rope (50gp), shovel (20gp), backpack (10gp), mana fluid (100gp), life fluid (60gp), fishing rod (100gp) and torch (2gp). I buy empty vials (10gp). Just say what you want!'

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
		'Hi ' .. creatureGetName(cid) .. '! ' .. SELLER_HELP
	)
	if state ~= 'focused' then
		return
	end

	if npcIsHelp(msg) then
		selfSay(SELLER_HELP)
	elseif msgcontains(msg, 'rope') or msgcontains(msg, 'cuerda') then
		buy(cid, 2120, 1, 50)
	elseif msgcontains(msg, 'shovel') or msgcontains(msg, 'pala') then
		buy(cid, 2554, 1, 20)
	elseif msgcontains(msg, 'backpack') or msgcontains(msg, 'mochila') then
		buy(cid, 1988, 1, 10)
	elseif msgcontains(msg, 'manafluid') or msgcontains(msg, 'mana fluid') or msgcontains(msg, 'mana') then
		buy(cid, 2006, 7, 100)
	elseif msgcontains(msg, 'lifefluid') or msgcontains(msg, 'life fluid') or msgcontains(msg, 'life') then
		buy(cid, 2006, 10, 60)
	elseif msgcontains(msg, 'fishing rod') or msgcontains(msg, 'cana') then
		buy(cid, 2580, 1, 100)
	elseif msgcontains(msg, 'torch') or msgcontains(msg, 'antorcha') then
		buy(cid, 2050, 1, 2)
	elseif msgcontains(msg, 'vial') or msgcontains(msg, 'flask') or msgcontains(msg, 'frasco') then
		sell(cid, 2006, 1, 10)
	end
end

function onCreatureChangeOutfit(creature)
end

function onThink()
	npcOnThink()
end
