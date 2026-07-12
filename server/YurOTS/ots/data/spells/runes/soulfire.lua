-- Soulfire Rune (2308) — alias for soul fire.lua (spells.xml lowercases name to soulfire).

attackType = ATTACK_FIRE
animationEffect = NM_ANI_FIRE

hitEffect = NM_ME_HITBY_FIRE
damageEffect = NM_ME_HITBY_FIRE
animationColor = RED
offensive = true
drawblood = false
minDmg = 10
maxDmg = 10
subDelayTick = 2000
subDamageCount = 10

SoulFireObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, minDmg, maxDmg)
SubSoulFireObject = MagicDamageObject(attackType, NM_ANI_NONE, NM_ME_NONE, damageEffect, animationColor, offensive, drawblood, minDmg, maxDmg)

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
	return doTargetExMagic(cid, centerpos, SoulFireObject:ordered(),
		subDelayTick, subDamageCount, SubSoulFireObject:ordered())
end
