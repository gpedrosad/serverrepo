-- Tide Priest: rayo de fuego de San Telmo a distancia contra un solo objetivo (daño de energía).
attackType = ATTACK_ENERGY
animationEffect = NM_ANI_ENERGY

hitEffect = NM_ME_NONE
damageEffect = NM_ME_ENERGY_DAMAGE
animationColor = LIGHT_BLUE
offensive = true
drawblood = false

ElmoFireObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
ElmoFireObject.minDmg = 40
ElmoFireObject.maxDmg = 95

return doTargetMagic(cid, centerpos, ElmoFireObject:ordered())
end
