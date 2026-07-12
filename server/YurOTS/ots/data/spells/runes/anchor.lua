-- Anchor Rune (2296)
-- Momentary root: target cannot move for 1 second.
-- Not paralyze (no ATTACK_PARALYZE condition / icon).

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
	return doAnchorRoot(cid, centerpos)
end
