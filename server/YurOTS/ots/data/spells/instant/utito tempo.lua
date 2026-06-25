attackType = ATTACK_NONE
animationEffect = NM_ANI_NONE

hitEffect = NM_ME_NONE
damageEffect = NM_ME_SOUND_BLUE
animationColor = YELLOW
offensive = false
drawblood = false

SkillBuffObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
    centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
    ret = doTargetMagic(cid, centerpos, SkillBuffObject:ordered())
    if(ret) then
        skillBuff(cid, 10, 30)
    end
    return ret
end
