-- Chameleon Rune (2291) — copies the look of the target creature.

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
	return doChameleon(cid, centerpos)
end
