-- Brutal Strike (exori ico), Knight: golpe fuerte con el arma al blanco marcado, pegado al knight.
--
-- Nov 2026, con la idea de las versiones nuevas (8.x en adelante) y la fórmula de TFS 1.x:
--   mínimo = nivel / 5 + (skill + ataque del arma) * 0.5
--   máximo = nivel / 5 + (skill + ataque del arma) * 1.5
-- Necesita espada, hacha o maza en la mano y el blanco en una de las 8 casillas de alrededor. Si no, no se
-- lanza (no gasta maná). Doc: docs/gameplay/SPELLS_NOV2026.md.

attackType = ATTACK_PHYSICAL
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_DRAW_BLOOD
damageEffect = NM_ME_EXPLOSION_DAMAGE
animationColor = RED
offensive = true
drawblood = true

SKILLS = {club = 1, sword = 2, axe = 3}

StrikeObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	local weapon = getPlayerWeapon(cid)
	local skillId = SKILLS[weapon.type]
	if skillId == nil then
		return false
	end
	local target = getAttackedCreaturePos(cid)
	if target.x == nil or target.z ~= creaturePos.z then
		return false
	end
	local dx = math.abs(target.x - creaturePos.x)
	local dy = math.abs(target.y - creaturePos.y)
	if (dx == 0 and dy == 0) or dx > 1 or dy > 1 then
		return false
	end
	local skill = getPlayerSkill(cid, skillId)
	if skill < 0 then
		return false
	end
	StrikeObject.minDmg = level / 5 + (skill + weapon.attack) * 0.5
	StrikeObject.maxDmg = level / 5 + (skill + weapon.attack) * 1.5
	return doTargetMagic(cid, target, StrikeObject:ordered())
end
