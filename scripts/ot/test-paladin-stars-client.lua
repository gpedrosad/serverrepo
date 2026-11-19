-- Prueba OFFLINE con perfil QA: nunca inicia sesión ni usa cuentas de jugadores.
-- Ejecutar tras loadModules() en una copia del cliente con APP_NAME exclusivo.
local function run()
  g_game.setClientVersion(760)
  g_game.setProtocolVersion(760)
  assert(g_things.isDatLoaded(), 'DAT no cargado')
  local root = g_ui.getRootWidget()
  local panel = g_ui.createWidget('UIWidget', root)
  panel:setSize({width=420, height=180})
  panel:setPosition({x=80,y=80})
  panel:setBackgroundColor('#303038')
  for i, id in ipairs({3396,3395,3393}) do
    local item = Item.create(id)
    assert(item:getId() == id and not item:isStackable(), 'item invalido/apilable')
    local widget = g_ui.createWidget('UIItem', panel)
    widget:setSize({width=96,height=96})
    widget:setPosition({x=90+(i-1)*130,y=110})
    widget:setItemId(id)
  end
  for id=45,47 do
    local effect = Effect.create()
    effect:setId(id)
    assert(effect:getId()==id)
    assert(g_things.getThingType(id,ThingCategoryEffect):getId()==id)
  end
  for id=19,21 do
    local missile = Missile.create()
    missile:setId(id)
    missile:setPath({x=100,y=100,z=7},{x=104,y=100,z=7})
    assert(missile:getId()==id)
    assert(g_things.getThingType(id,ThingCategoryMissile):getId()==id)
  end
  print('PALADIN_STARS_CLIENT_PASS: 3 items no apilables, 3 efectos y 3 proyectiles custom cargados por motor Mac')
  scheduleEvent(function() panel:destroy(); g_app.exit() end,3000)
end
local ok, err = pcall(run)
if not ok then
  print('PALADIN_STARS_CLIENT_FAIL: '..tostring(err))
  scheduleEvent(function() g_app.exit() end,1000)
end
