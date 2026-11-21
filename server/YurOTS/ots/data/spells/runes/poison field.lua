area = {
	{0, 0, 0},
	{0, 1, 0},
	{0, 0, 0}
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
minDmg = 10
maxDmg = 10

PoisonFieldObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)
SubPoisonFieldObject1 = MagicDamageObject(attackType, NM_ANI_NONE, NM_ME_NONE, damageEffect, animationColor, offensive, drawblood, minDmg, maxDmg)
SubPoisonFieldObject2 = MagicDamageObject(attackType, NM_ANI_NONE, NM_ME_NONE, damageEffect, animationColor, offensive, drawblood, 5, 5)

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}

	return doAreaGroundMagic(cid, centerpos, needDirection, areaEffect, area, PoisonFieldObject:ordered(),
		0, 1, SubPoisonFieldObject1:ordered(),
		5000, 5, SubPoisonFieldObject2:ordered(),
		2, 50000, 1490, 1)
end
