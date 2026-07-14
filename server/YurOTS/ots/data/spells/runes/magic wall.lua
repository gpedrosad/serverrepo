-- doTargetGroundMagic
 -- cid: creature id.
 -- creaturePos: Target position.
 -- animationEffect: Projectile animation.
 -- offensive: Indicates if the spell is a healing/attack spell.
 --
 -- returns true if the spell was casted.

 animationEffect = NM_ANI_ENERGY
 offensive = true
 magicDamageListCount = 0
 -- 15s real: DECAY_INTERVAL es 5000ms; valores no multiplo de ese interval se redondean.
 durationTicks = 15000
 itemid = 1498
 transformCount = 1

 function onCast(cid, creaturePos, level, maglv, var)
 centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}

 return doTargetGroundMagic(cid, centerpos, animationEffect, offensive,
 magicDamageListCount, durationTicks, itemid, transformCount)
 end
