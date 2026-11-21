attackType = ATTACK_ENERGY
needDirection = false
areaEffect = NM_ME_NONE
animationEffect = NM_ANI_ENERGY

hitEffect = NM_ME_ENERGY_DAMAGE
damageEffect = NM_ME_ENERGY_DAMAGE
animationColor = LIGHT_BLUE
offensive = true
drawblood = false
minDmg = 30
maxDmg = 30

EnergyWallObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)
SubEnergyWallObject1 = MagicDamageObject(attackType, NM_ANI_NONE, NM_ME_NONE, damageEffect, animationColor, offensive, drawblood, minDmg, maxDmg)
SubEnergyWallObject2 = MagicDamageObject(attackType, NM_ANI_NONE, NM_ME_NONE, damageEffect, animationColor, offensive, drawblood, 25, 25)

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
	area = makeWallArea(getCreaturePos(cid), centerpos)

	return doAreaGroundMagic(cid, centerpos, needDirection, areaEffect, area, EnergyWallObject:ordered(),
		0, 1, SubEnergyWallObject1:ordered(),
		5000, 1, SubEnergyWallObject2:ordered(),
		2, 105000, 1495, 1)
end
