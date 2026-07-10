-- Convince Creature Rune (2290) — convinces a monster to fight for you.

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
	return doConvinceCreature(cid, centerpos)
end
