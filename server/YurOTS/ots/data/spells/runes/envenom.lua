-- Envenom Rune (2292) — applies poison damage-over-time (classic 7.6 DoT, poison counterpart to Soulfire).

attackType = ATTACK_POISON
animationEffect = NM_ANI_FLYPOISONFIELD

hitEffect = NM_ME_POISEN_RINGS
damageEffect = NM_ME_POISEN
animationColor = GREEN
offensive = true
drawblood = false
minDmg = 6
maxDmg = 10
subDelayTick = 2000
subDamageCount = 10

EnvenomObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, minDmg, maxDmg)
SubEnvenomObject = MagicDamageObject(attackType, NM_ANI_NONE, NM_ME_NONE, damageEffect, animationColor, offensive, drawblood, minDmg, maxDmg)

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
	return doTargetExMagic(cid, centerpos, EnvenomObject:ordered(),
		subDelayTick, subDamageCount, SubEnvenomObject:ordered())
end
