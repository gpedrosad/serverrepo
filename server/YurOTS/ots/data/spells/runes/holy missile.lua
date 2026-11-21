-- Holy Missile Rune (2295) — single-target paladin rune (adapted to 7.6 like exori san).
attackType = ATTACK_ENERGY
animationEffect = NM_ANI_POWERBOLT

hitEffect = NM_ME_YELLOW_RINGS
damageEffect = NM_ME_YELLOW_RINGS
animationColor = YELLOW
offensive = true
drawblood = false

HolyMissileObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}

	HolyMissileObject.minDmg = (level * 1.5 + maglv * 2.4) * 0.45
	HolyMissileObject.maxDmg = (level * 1.5 + maglv * 2.4) * 0.85

	return doTargetMagic(cid, centerpos, HolyMissileObject:ordered())
end
