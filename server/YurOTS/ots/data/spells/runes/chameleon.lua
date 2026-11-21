-- Chameleon Rune (2291) — disguises the caster as a moveable item on the target tile (~200s).

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
	return doChameleon(cid, centerpos)
end
