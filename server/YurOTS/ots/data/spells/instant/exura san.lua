-- Divine Healing (exura san), Paladin: se cura a sí mismo.
--
-- Nov 2026, con la idea de las versiones nuevas: la curación propia del paladin. Fórmula del servidor:
-- (nivel * 2 + magic level * 3) * 0.9 a * 1.4, entre exura gran y exura vita, más barata que exura vita.
-- Doc: docs/gameplay/SPELLS_NOV2026.md.

attackType = ATTACK_NONE
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_NONE
damageEffect = NM_ME_YELLOW_RINGS
animationColor = GREEN
offensive = false
drawblood = false

HealObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	local centerpos = {x = creaturePos.x, y = creaturePos.y, z = creaturePos.z}
	HealObject.minDmg = (level * 2 + maglv * 3) * 0.9
	HealObject.maxDmg = (level * 2 + maglv * 3) * 1.4
	return doTargetMagic(cid, centerpos, HealObject:ordered())
end
