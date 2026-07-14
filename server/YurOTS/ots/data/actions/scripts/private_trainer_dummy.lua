-- Private trainer dummy (20155): put on a free house tile, then Use.
-- Same pattern as construction kits — no use-with.

function onUse(cid, item, frompos, item2, topos)
	if frompos.x == 65535 then
		doPlayerSendCancel(cid, "Put the private trainer dummy on a house tile first.")
		return 1
	end

	return doPlacePrivateTrainer(cid, item.uid, frompos)
end
