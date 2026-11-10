-- Ice Monk: fragmento de hielo a distancia contra un solo objetivo (proyectil FROSTBALL del pack "ice").
-- El motor 7.6 no tiene daño de hielo: es daño físico con número celeste.
attackType = ATTACK_PHYSICAL
animationEffect = NM_ANI_FROSTBALL

hitEffect = NM_ME_NONE
damageEffect = NM_ME_ICE_SHATTER
animationColor = LIGHT_BLUE
offensive = true
drawblood = false

IceShardObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
IceShardObject.minDmg = 45
IceShardObject.maxDmg = 95

return doTargetMagic(cid, centerpos, IceShardObject:ordered())
end
