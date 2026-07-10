-- Paralyze Rune (2278) — slows target movement for 60 seconds.

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
	return doParalyze(cid, centerpos)
end
