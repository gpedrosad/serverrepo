-- Destroy Field Rune (2261) — removes fire/energy/poison fields (excludes magic wall & wild growth).

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
	return doDestroyField(cid, centerpos)
end
