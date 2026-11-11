-- Whirlwind Throw (exori hur), Knight: lanza su arma de melee contra el blanco marcado, hasta 5 casillas.
--
-- Hecho de cero (nov 2026) con la idea de las versiones nuevas (8.x en adelante): daño físico que sube con
-- el nivel, el skill del arma y el ataque del arma (fórmula de TFS 1.x):
--   mínimo = nivel / 5 + (skill + ataque) / 3
--   máximo = nivel / 5 + skill + ataque
-- Sin arma de melee en la mano, sin blanco, en otro piso o fuera de rango no se lanza (no gasta maná).
-- El proyectil depende del arma. En 7.6 no existe el arma girando de las versiones nuevas: espada ->
-- cuchillo arrojadizo, hacha -> estrella arrojadiza, maza -> roca.
-- Usa getAttackedCreaturePos, getPlayerWeapon y getPlayerSkill (spells.cpp). Doc: docs/gameplay/SPELL_EXORI_HUR.md.

attackType = ATTACK_PHYSICAL
hitEffect = NM_ME_DRAW_BLOOD
damageEffect = NM_ME_HIT_AREA
animationColor = RED
offensive = true
drawblood = true

RANGE = 5
SKILL_CLUB, SKILL_SWORD, SKILL_AXE = 1, 2, 3
WEAPONS = {
	sword = {skill = SKILL_SWORD, missile = NM_ANI_THROWINGKNIFE},
	axe = {skill = SKILL_AXE, missile = NM_ANI_THROWINGSTAR},
	club = {skill = SKILL_CLUB, missile = NM_ANI_LARGEROCK},
}

function onCast(cid, creaturePos, level, maglv, var)
	local weapon = getPlayerWeapon(cid)
	local kind = WEAPONS[weapon.type]
	if kind == nil then
		return false
	end

	local target = getAttackedCreaturePos(cid)
	if target.x == nil or target.z ~= creaturePos.z then
		return false
	end
	local dx = math.abs(target.x - creaturePos.x)
	local dy = math.abs(target.y - creaturePos.y)
	if (dx == 0 and dy == 0) or dx > RANGE or dy > RANGE then
		return false
	end

	local skill = getPlayerSkill(cid, kind.skill)
	if skill < 0 then
		return false
	end
	local throw = MagicDamageObject(attackType, kind.missile, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)
	throw.minDmg = level / 5 + (skill + weapon.attack) / 3
	throw.maxDmg = level / 5 + skill + weapon.attack
	return doTargetMagic(cid, target, throw:ordered())
end
