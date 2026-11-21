-- Icicle Rune (2271) — single-target ice rune (adapted to 7.6 with pack "ice" effects).
attackType = ATTACK_PHYSICAL
animationEffect = NM_ANI_FROSTBALL

hitEffect = NM_ME_ICE_SHATTER
damageEffect = NM_ME_ICE_HIT
animationColor = LIGHT_BLUE
offensive = true
drawblood = false

IcicleObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}

	IcicleObject.minDmg = (level * 1.5 + maglv * 2.2) * 0.45
	IcicleObject.maxDmg = (level * 1.5 + maglv * 2.2) * 0.85

	return doTargetMagic(cid, centerpos, IcicleObject:ordered())
end
