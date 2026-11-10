-- Tide Priest: la marea se lleva tu maná. Bola de agua a distancia que vacía maná (no vida) con salpicadura azul.
attackType = ATTACK_MANADRAIN
animationEffect = NM_ANI_SNOWBALL

hitEffect = NM_ME_NONE
damageEffect = NM_ME_LOOSE_ENERGY
animationColor = DARK_BLUE
offensive = true
drawblood = false

ManaTideObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
ManaTideObject.minDmg = 40
ManaTideObject.maxDmg = 90

return doTargetMagic(cid, centerpos, ManaTideObject:ordered())
end
