-- Challenge (exeta res): nearby monsters target the caster for 6 seconds.
-- Knight (voc 4). Exhaust via doTargetMagic; taunt via doChallenge C++ binding.

attackType = ATTACK_NONE
animationEffect = NM_ANI_NONE

hitEffect = NM_ME_NONE
damageEffect = NM_ME_SOUND_BLUE
animationColor = LIGHT_BLUE
offensive = false
drawblood = false

ChallengeObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
	local ret = doTargetMagic(cid, centerpos, ChallengeObject:ordered())
	if ret then
		doChallenge(cid)
	end
	return ret
end
