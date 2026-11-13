-- Bog Raider: chorro de pantano que roba vida.
--doTargetMagic
-- attackType: Type of attack.
-- cid: creature id.
-- Targetpos: Target position.
-- animationEffect: Projectile animation.
-- damageEffect: Effect to show when spell damage a creature.
-- hitEffect: Effect to show when spell hits a creature.
-- animationColor: Color of the text that is shown above the player when hit.
-- offensive: Indicates if the spell is a healing/attack spell.
-- drawblood: Determines if the spell causes blood splash.
-- minDmg: Minimal damage.
-- maxDmg: Maximum damage.
-- returns true if the spell was casted.

attackType = ATTACK_LIFEDRAIN
animationEffect = NM_ANI_FLYPOISONFIELD

hitEffect = NM_ME_POISEN_RINGS
damageEffect = NM_ME_POISONCLOUD
animationColor = RED
offensive = true
drawblood = true

BogRaiderDrownObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}

BogRaiderDrownObject.minDmg = 50
BogRaiderDrownObject.maxDmg = 110

return doTargetMagic(cid, centerpos, BogRaiderDrownObject:ordered())
end
