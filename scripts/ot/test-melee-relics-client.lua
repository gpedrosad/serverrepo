-- Perfil QA offline, sin login ni updater; settings/minimapa con nombres exclusivos.
local function run()
  g_game.setClientVersion(760)
  g_game.setProtocolVersion(760)
  assert(g_things.isDatLoaded(), 'DAT no cargado')
  local panel=g_ui.createWidget('UIWidget',g_ui.getRootWidget())
  panel:setSize({width=440,height=180})
  panel:setPosition({x=80,y=80})
  panel:setBackgroundColor('#252831')
  for i,id in ipairs({3242,3238,3235}) do
    local item=Item.create(id)
    assert(item:getId()==id and not item:isStackable(), 'item invalido/apilable')
    local widget=g_ui.createWidget('UIItem',panel)
    widget:setSize({width=96,height=96})
    widget:setPosition({x=90+(i-1)*130,y=110})
    widget:setItemId(id)
  end
  for id=48,50 do
    local effect=Effect.create();effect:setId(id)
    assert(effect:getId()==id)
    assert(g_things.getThingType(id,ThingCategoryEffect):getId()==id)
  end
  print('MELEE_RELICS_CLIENT_PASS: 3 armas y 3 impactos cargados con motor Mac')
  scheduleEvent(function()
    g_app.doScreenshot('melee-relics-client-qa.png')
    scheduleEvent(function()panel:destroy();g_app.exit()end,1000)
  end,2500)
end
local ok,err=pcall(run)
if not ok then
  print('MELEE_RELICS_CLIENT_FAIL: '..tostring(err))
  scheduleEvent(function()g_app.exit()end,1000)
end
