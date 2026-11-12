-- Root Colossus: las raices golpean alrededor (radio 2), sin inmovilizacion.
local area = {
    {0, 0, 0, 0, 0, 0, 0},
    {0, 0, 1, 1, 1, 0, 0},
    {0, 1, 1, 1, 1, 1, 0},
    {0, 1, 1, 0, 1, 1, 0},
    {0, 1, 1, 1, 1, 1, 0},
    {0, 0, 1, 1, 1, 0, 0},
    {0, 0, 0, 0, 0, 0, 0},
}
local damage = MagicDamageObject(ATTACK_PHYSICAL, NM_ANI_NONE, NM_ME_HIT_AREA,
    NM_ME_HIT_AREA, GREY, true, false, 100, 180)

function onCast(cid, creaturePos, level, maglv, var)
    local center = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
    return doAreaMagic(cid, center, false, NM_ME_HIT_AREA, area, damage:ordered())
end
