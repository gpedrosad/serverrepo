dofile("data/actions/scripts/shovel.lua")
local dig = onUse
dofile("data/actions/scripts/rope.lua")
local rope = onUse

function onUse(cid, item, frompos, item2, topos)
	local result = dig(cid, item, frompos, item2, topos)
	if result ~= 0 then
		return result
	end
	return rope(cid, item, frompos, item2, topos)
end
