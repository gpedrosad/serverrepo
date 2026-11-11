-- Sharpshooter (utito tempo san), Paladin: +30 de skill durante 10 s (distancia y melee, como utito tempo).
--
-- Nov 2026, con la idea de las versiones nuevas. En ellas además baja la velocidad; acá no, porque
-- changeSpeed pisa el haste (utani hur) y al terminar lo cortaría. Doc: docs/gameplay/SPELLS_NOV2026.md.

attackType = ATTACK_NONE
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_NONE
damageEffect = NM_ME_YELLOW_RINGS
animationColor = GREEN
offensive = false
drawblood = false

BuffObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	local centerpos = {x = creaturePos.x, y = creaturePos.y, z = creaturePos.z}
	local ret = doTargetMagic(cid, centerpos, BuffObject:ordered())
	if ret then
		skillBuff(cid, 10, 30)
	end
	return ret
end
