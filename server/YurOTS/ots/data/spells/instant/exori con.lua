-- Ethereal Spear (exori con), Paladin: lanza una lanza etérea contra el blanco marcado.
--
-- Hecho de cero (nov 2026) con la idea de las versiones nuevas (8.x en adelante): daño físico a distancia
-- que sube con el nivel y el skill de distancia, sin gastar munición (fórmula de TFS 1.x):
--   mínimo = nivel / 5 + distancia * 0.7
--   máximo = nivel / 5 + distancia + 5
-- Alcance: 7 casillas a los costados y 5 arriba y abajo (lo que entra en la pantalla de 7.6).
-- Sin blanco, en otro piso o fuera de alcance no se lanza (no gasta maná).
-- Proyectil: NM_ANI_ENCHANTED_SPEAR (16), la lanza azul que brilla de la Enchanted Spear. Con un cliente viejo
-- que no tiene ese efecto, el daño llega igual pero no se ve la lanza.
-- Usa getAttackedCreaturePos y getPlayerSkill (spells.cpp). Doc: docs/gameplay/SPELL_EXORI_CON.md.

attackType = ATTACK_PHYSICAL
animationEffect = NM_ANI_ENCHANTED_SPEAR
hitEffect = NM_ME_DRAW_BLOOD
damageEffect = NM_ME_ENERGY_AREA
animationColor = RED
offensive = true
drawblood = true

RANGE_X, RANGE_Y = 7, 5
SKILL_DIST = 4

SpearObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	local target = getAttackedCreaturePos(cid)
	if target.x == nil or target.z ~= creaturePos.z then
		return false
	end
	local dx = math.abs(target.x - creaturePos.x)
	local dy = math.abs(target.y - creaturePos.y)
	if (dx == 0 and dy == 0) or dx > RANGE_X or dy > RANGE_Y then
		return false
	end

	local distance = getPlayerSkill(cid, SKILL_DIST)
	if distance < 0 then
		return false
	end
	SpearObject.minDmg = level / 5 + distance * 0.7
	SpearObject.maxDmg = level / 5 + distance + 5
	return doTargetMagic(cid, target, SpearObject:ordered())
end
