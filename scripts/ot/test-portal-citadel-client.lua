-- Solo fixture sintético en 7280. Nunca usa cuentas del servidor de juego.
-- La copia QA debe cargar settings/minimapa exclusivos: APP_NAME solo no aísla writeDir.
g_resources.makeDir('/settings/')
local portals={
  {'catedral',155,{x=148,y=335,z=7}}, {'isla',156,{x=147,y=462,z=7}},
  {'elvenbane',157,{x=39,y=346,z=7}}, {'valle',158,{x=312,y=360,z=7}},
  {'inferno',159,{x=540,y=440,z=7}}, {'crisol',164,{x=605,y=105,z=0}},
  {'wave',166,{x=606,y=223,z=7}}, {'reloj',168,{x=605,y=327,z=6}}
}
local finished=false
local function finish(ok,message)
  if finished then return end
  finished=true
  print((ok and 'CITADEL_QA_PASS: ' or 'CITADEL_QA_FAIL: ')..message)
  if g_game.isOnline() then g_game.safeLogout() end
  scheduleEvent(function()g_app.exit()end,1200)
end
local function protect(fn)
  local ok,err=pcall(fn)
  if not ok then finish(false,tostring(err)) end
end
local function later(fn,delay)
  scheduleEvent(function()if not finished then protect(fn) end end,delay or 600)
end
local function position()
  return g_game.getLocalPlayer():getPosition()
end
local function same(a,b)
  return a and math.abs(a.x-b.x)<=1 and math.abs(a.y-b.y)<=1 and a.z==b.z
end
local function go(x,y,z)
  g_game.talk(string.format('/goto %d %d %d',x,y,z))
end
local function tour(i)
  if i>#portals then
    go(161,46,7)
    later(function()
      print('CITADEL_QA: render final, writeDir='..g_resources.getWriteDir())
      if type(g_app.doScreenshot)=='function' then g_app.doScreenshot('portal-citadel-qa.png') end
      if type(g_app.doMapScreenshot)=='function' then g_app.doMapScreenshot('portal-citadel-map.png') end
      later(function()finish(true,'8 portales recorridos con destinos correctos; nuevos pisos y torres cargados')end,1500)
    end,1200)
    return
  end
  local p=portals[i]
  go(p[2],48,7)
  later(function()
    assert(same(position(),{x=p[2],y=48,z=7}),'no llegó al anillo de '..p[1])
    g_game.walk(North)
    later(function()
      assert(same(position(),p[3]),p[1]..': destino incorrecto')
      print('CITADEL_PORTAL_PASS: '..p[1])
      tour(i+1)
    end,800)
  end,800)
end
connect(g_game,{onGameStart=function()
  later(function()
    g_window.resize({width=1360,height=950})
    for _,cid in ipairs({3379,3368,3365,3363,3342,3253,3247,3246,3245,3244,3243}) do
      assert(g_things.getThingType(cid,ThingCategoryItem):getId()==cid,'asset ausente')
    end
    go(161,52,7)
    later(function()
      local steps=0
      local function walk()
        if steps==7 then
          assert(same(position(),{x=161,y=45,z=7}),'pasillo central bloqueado')
          print('CITADEL_WALK_PASS: acceso sur-norte libre')
          tour(1);return
        end
        steps=steps+1;g_game.walk(North);later(walk,350)
      end
      walk()
    end,700)
  end,1200)
end,onLoginError=function(message)finish(false,tostring(message))end})
g_game.setClientVersion(760)
g_game.setProtocolVersion(760)
g_game.setCustomOs(2)
g_game.loginWorld('111111','asantest','Citadel QA','192.168.1.17',7280,'Portal QA','','')
scheduleEvent(function()finish(false,'timeout')end,60000)
