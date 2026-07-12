-- Antidote Rune (2266) — cures poison on target creature.

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
	return doCurePoison(cid, centerpos)
end
