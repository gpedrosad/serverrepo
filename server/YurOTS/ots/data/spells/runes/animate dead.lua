-- Animate Dead Rune (2316) — raises a skeleton from a corpse.

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
	return doAnimateDead(cid, centerpos)
end
