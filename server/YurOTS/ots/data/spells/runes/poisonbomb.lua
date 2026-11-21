area = {
	{1, 1, 1},
	{1, 1, 1},
	{1, 1, 1}
}

attackType = ATTACK_POISON
needDirection = false
areaEffect = NM_ME_POISEN_RINGS
animationEffect = NM_ANI_FLYPOISONFIELD

hitEffect = NM_ME_POISEN
damageEffect = NM_ME_POISEN_RINGS
animationColor = GREEN
offensive = true
drawblood = false
minDmg = 6
maxDmg = 6

PoisonBombObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)
SubPoisonBombObject1 = MagicDamageObject(attackType, NM_ANI_NONE, NM_ME_NONE, damageEffect, animationColor, offensive, drawblood, minDmg, maxDmg)
SubPoisonBombObject2 = MagicDamageObject(attackType, NM_ANI_NONE, NM_ME_NONE, damageEffect, animationColor, offensive, drawblood, 6, 6)

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}

	-- Single stage on 1490 (120s, multiple of DECAY_INTERVAL=5000) to avoid TransformMap key collision.
	return doAreaGroundMagic(cid, centerpos, needDirection, areaEffect, area, PoisonBombObject:ordered(),
		0, 1, SubPoisonBombObject1:ordered(),
		5000, 7, SubPoisonBombObject2:ordered(),
		2, 120000, 1490, 1)
end
