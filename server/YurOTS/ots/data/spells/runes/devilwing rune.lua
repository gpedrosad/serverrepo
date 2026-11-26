-- The shard is physical, like Icicle. The hit and missile use cold-fire artwork.
local DEVILWING_PROJECTILE = 22
local shard = MagicDamageObject(ATTACK_PHYSICAL, DEVILWING_PROJECTILE, NM_ME_ICE_SHATTER,
	NM_ME_ICE_HIT, LIGHT_BLUE, true, false, 0, 0)

function onCast(cid, position, level, maglv, var)
	local power = level * 1.5 + maglv * 2.2
	shard.minDmg = power * 0.52
	shard.maxDmg = power * 0.94
	return doTargetMagic(cid, position, shard:ordered())
end
