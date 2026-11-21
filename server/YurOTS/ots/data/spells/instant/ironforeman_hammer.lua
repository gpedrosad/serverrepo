-- Golpe del martillo: impacto fisico inmediato alrededor del capataz (radio 1).
local area = {
    {1, 1, 1},
    {1, 0, 1},
    {1, 1, 1},
}
local damage = MagicDamageObject(ATTACK_PHYSICAL, NM_ANI_NONE, NM_ME_EXPLOSION_DAMAGE,
    NM_ME_EXPLOSION_DAMAGE, ORANGE, true, false, 50, 90)

function onCast(cid, creaturePos, level, maglv, var)
    local center = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
    return doAreaMagic(cid, center, false, NM_ME_EXPLOSION_AREA, area, damage:ordered())
end
