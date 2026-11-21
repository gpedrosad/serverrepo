-- Shop-only PvP trap. Damage happens on step-in, never on placement.
function onCast(cid, creaturePos, level, maglv, var)
	return doFrostMine(cid, creaturePos)
end
