-- Wild Growth Rune (2269) -> places solid blocking Wild Growth field (1499).
-- 45s real duration (multiple of DECAY_INTERVAL = 5000ms). Destroyable with Desintegrate (2310).

animationEffect = NM_ANI_ENERGY
offensive = true
magicDamageListCount = 0
durationTicks = 45000
itemid = 1499
transformCount = 1

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}

	return doTargetGroundMagic(cid, centerpos, animationEffect, offensive,
		magicDamageListCount, durationTicks, itemid, transformCount)
end
