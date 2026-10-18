"""MQTT 5 wire vectors and hostile-input tests with a simulated Q-SYS host.

Run against the packaged plugin. No Designer/Core or MQTT conformance certification implied.
"""
import json
import sys
from pathlib import Path
from test_mqtt import runtime, design, PLUGIN

HELPERS = r'''
function Var(n)
  local out=""
  repeat
    local b=n%128;n=math.floor(n/128)
    out=out..string.char(b+(n>0 and 128 or 0))
  until n==0
  return out
end
function Frame(header,body) return string.char(header)..Var(#body)..body end
function Text(s) return IdBytes(#s)..s end
function Connack(properties,rc) properties=properties or "";return Frame(32,"\000"..string.char(rc or 0)..Var(#properties)..properties) end
function Online5(properties,options)
  options=options or {};options.ProtocolVersion="5.0"
  local c,s=NewClient(options);s:Open();s:Feed(Connack(properties));assert(c.State=="Connected")
  return c,s
end
function Ack5(kind,id,rc,props)
  props=props or "";return Frame(kind,IdBytes(id)..string.char(rc or 0)..Var(#props)..props)
end
'''
CASES = {
"version selection, default and invalid option": r'''
local c=assert(Mqtt.New({Host="x",ClientId="id"}));assert(not c.IsV5)
assert(not Mqtt.New({Host="x",ClientId="id",ProtocolVersion="5"}))
local c,s=NewClient({ProtocolVersion="5.0",KeepAlive=0});s:Open()
local wire=s.Writes[1]
assert(wire:sub(3,12)=="\000\004MQTT\005\002\000\000")
''',
"CONNECT advertises bounded clean session and no aliases": r'''
local c,s=NewClient({ProtocolVersion="5.0",KeepAlive=0});s:Open()
local wire=s.Writes[1];assert(wire:byte(13)==13)
assert(wire:find("\017\000\000\000\000",14,true))
assert(wire:find("\039\000\001\000\000",14,true))
assert(wire:find("\034\000\000",14,true))
s:Feed(Connack());assert(c.State=="Connected")
''',
"short and reason-bearing PUBACK success and rejection": r'''
for _,code in ipairs({0,16,135,151}) do
  local c,s=Online5();local result,detail
  local _,id=c:Publish("x","y",1,false,function(_,ok,why) result=ok;detail=why end)
  s:Feed(code==0 and Frame(64,IdBytes(id)) or Frame(64,IdBytes(id)..string.char(code)))
  assert(result==(code<128) and c.PendingCount==0 and c.State=="Connected")
  if code>=128 then assert(detail=="broker-rejected-"..code) end
end
''',
"SUBACK and UNSUBACK failures are operation results": r'''
local c,s=Online5();local success
local _,id=c:Subscribe("a/#",1,function(_,ok) success=ok end)
s:Feed(Frame(144,IdBytes(id).."\000\135"))
assert(success==false and not c.Subscriptions["a/#"] and c.State=="Connected")
_,id=c:Subscribe("a",1);s:Feed(Frame(144,IdBytes(id).."\000\001"))
_,id=c:Unsubscribe("a",function(_,ok) success=ok end)
s:Feed(Frame(176,IdBytes(id).."\000\135"));assert(success==false and c.State=="Connected")
_,id=c:Unsubscribe("absent",function(_,ok,why) assert(ok and why=="no-subscription-existed") end)
s:Feed(Frame(176,IdBytes(id).."\000\017"));assert(c.PendingCount==0)
''',
"Receive Maximum counts only pending QoS1 publishes": r'''
local c,s=Online5("\033\000\001")
local _,id=c:Publish("x","one",1)
local ok,why=c:Publish("x","two",1);assert(not ok and why=="broker-receive-limit")
assert(c:Subscribe("a/#",1));assert(c:Publish("x","zero",0))
s:Feed(Frame(64,IdBytes(id)));assert(c:Publish("x","now",1))
s:Feed(Frame(50,Text("a/b")..IdBytes(44).."\000payload"))
assert(c.Messages[1].Payload=="payload" and s.Writes[#s.Writes]==Frame(64,IdBytes(44)))
''',
"broker QoS retain wildcard and packet limits": r'''
local c,s=Online5("\036\000\037\000\040\000\039\000\000\000\030")
local ok,why=c:Publish("x","a",1);assert(not ok and why=="broker-qos-unavailable")
ok,why=c:Publish("x","a",0,true);assert(not ok and why=="broker-retain-unavailable")
ok,why=c:Subscribe("a/#",1);assert(not ok and why=="broker-wildcards-unavailable")
assert(c:Subscribe("a",1))
ok,why=c:Publish("x",string.rep("a",30),0);assert(not ok and why=="packet-too-large")
assert(c:Publish("x","small",0))
''',
"server keepalive replaces configured keepalive including zero": r'''
local c,s=Online5("\019\000\002",{KeepAlive=30});Advance(2)
assert(s.Writes[#s.Writes]=="\192\000")
s:Feed("\208\000");assert(not c.PingAt)
local c,s=Online5("\019\000\000",{KeepAlive=1});Advance(5);assert(#s.Writes==1)
''',
"binary payload and MQTT5 properties survive delivery": r'''
local c,s=Online5()
local props="\003"..Text("application/octet-stream").."\008"..Text("reply/here").."\009"..Text("id\000x").."\038"..Text("key")..Text("value")
s:Feed(Frame(49,Text("a")..Var(#props)..props.."bin\000\255"))
local m=c.Messages[1];assert(m.Payload=="bin\000\255" and m.Retain)
assert(m.Properties.content_type=="application/octet-stream")
assert(m.Properties.response_topic=="reply/here" and m.Properties.correlation_data=="id\000x")
assert(m.UserProperties.key=="value")
''',
"fragmented multi-byte CONNACK and duplicate user properties": r'''
local c,s=NewClient({ProtocolVersion="5.0"});s:Open()
local p="\038"..Text("a")..Text(string.rep("x",140)).."\038"..Text("a")..Text("b")
local frame=Connack(p);s:Feed(frame:sub(1,7));s:Feed(frame:sub(8));assert(c.State=="Connected")
''',
"broker refusal and DISCONNECT never report connected success": r'''
local c,s=NewClient({ProtocolVersion="5.0"});s:Open();s:Feed(Connack("",135));assert(c.State=="Reconnecting")
for _,body in ipairs({"","\000","\139\000"}) do
  local c,s=Online5();s:Feed(Frame(224,body));assert(c.State=="Reconnecting")
end
''',
"nonzero broker session expiry declined as capability limit": r'''
local c,s=NewClient({ProtocolVersion="5.0"});s:Open();s:Feed(Connack("\017\000\000\000\030"))
assert(c.State=="Reconnecting" and s.Writes[2]:byte()==224)
assert(s.Writes[2]:find("\017\000\000\000\000",1,true))
''',
"reconnect resets broker limits and restores accepted subscriptions": r'''
local c,s=Online5("\033\000\001")
local _,id=c:Subscribe("a/#",1);s:Feed(Frame(144,IdBytes(id).."\000\001"))
s.Closed(s);Advance(1);local n=Sockets[#Sockets];n:Open();n:Feed(Connack())
assert(c.State=="Connected" and c.ServerReceiveMaximum==65535 and n.Writes[2]:byte()==130)
''',
"reconnect reports newly unsupported wildcard without reconnect loop": r'''
local c,s=Online5();local _,id=c:Subscribe("a/#",1);s:Feed(Frame(144,IdBytes(id).."\000\001"))
c.OnSubscription=function(_,filter,ok,why) assert(filter=="a/#" and not ok and why=="broker-wildcards-unavailable") end
s.Closed(s);Advance(1);local n=Sockets[#Sockets];n:Open();n:Feed(Connack("\040\000"))
assert(c.State=="Connected" and not c.Subscriptions["a/#"])
''',
"malformed properties cannot consume payload or bypass framing": r'''
local bad={
 Frame(48,Text("a").."\001\003\000\001xpayload"), -- text property outside property length
 Frame(48,Text("a").."\003\003\000\010abc"), -- truncated string
 Frame(48,Text("a").."\128\000payload"), -- overlong variable integer
 Frame(48,Text("a").."\002\127\000"), -- unknown property
 Frame(48,Text("a").."\004\001\000\001\000payload"), -- duplicate singleton
 Frame(48,Text("a").."\004\003\000\001\000payload"), -- null UTF8
 Frame(48,Text("a").."\001\001payload"), -- integer outside boundary
 Frame(48,Text("a").."\003\023\000\001payload"), -- illegal PUBLISH property
 Frame(48,Text("a").."\003\035\000\001payload"), -- unsolicited alias
 Frame(48,Text("a").."\002\011\001payload"), -- unrequested subscription ID
 "\208\001\000", -- PINGRESP payload
 Frame(224,"\000\005\017\000\000\000\000"), -- server expiry on disconnect
}
for _,frame in ipairs(bad) do
 local c,s=Online5();s:Feed(frame);assert(c.State=="Reconnecting" and #c.Messages==0)
 assert(s.Writes[#s.Writes]:byte()==224)
end
''',
"invalid CONNACK limits properties and reason codes": r'''
for _,p in ipairs({"\033\000\000","\039\000\000\000\000","\036\002","\037\002","\033\000\001\033\000\002","\018"..Text("other-id"),"\021"..Text("auth")}) do
 local c,s=NewClient({ProtocolVersion="5.0"});s:Open();s:Feed(Connack(p));assert(c.State=="Reconnecting")
end
local c,s=NewClient({ProtocolVersion="5.0"});s:Open();s:Feed(Connack("",3));assert(c.State=="Reconnecting")
''',
"invalid ack reasons and cardinality rejected": r'''
for _,tail in ipairs({"\000","\000\001\001","\000\003"}) do
 local c,s=Online5();local _,id=c:Subscribe("a",1);s:Feed(Frame(144,IdBytes(id)..tail));assert(c.State=="Reconnecting")
end
local c,s=Online5();local _,id=c:Publish("a","b",1);s:Feed(Frame(64,IdBytes(id).."\001"));assert(c.State=="Reconnecting")
''',
"oversized inbound packet sends MQTT5 Packet Too Large": r'''
local c,s=Online5(nil,{MaxPacketBytes=1024});s:Feed(Frame(48,Text("a").."\000"..string.rep("x",1024)))
assert(c.State=="Reconnecting" and s.Writes[#s.Writes]=="\224\002\149\000")
''',
"shared subscriptions and QoS2 remain explicitly unsupported": r'''
local c,s=Online5();local ok,why=c:Subscribe("$share/group/a",1)
assert(not ok and why=="shared-subscriptions-unsupported")
assert(not c:Publish("a","b",2));assert(not c:Subscribe("a",2))
''',
}

def main():
    passed=[]
    for name,source in CASES.items():
        try:
            lua=runtime();lua.execute(HELPERS.encode());lua.execute(source.encode())
        except Exception:
            print("FAILED:",name,file=sys.stderr);raise
        passed.append(name)
    for selection in (b"5.0", b"3.1.1", None):
        lua,g,props=design(1)
        assert props[b"MQTT Version"].Value==b"3.1.1"
        if selection is None:
            props[b"MQTT Version"]=None
        else:
            props[b"MQTT Version"].Value=selection
        g.Properties=props
        lua.execute(b'''
Controls={}
for _,d in ipairs(GetControls(Properties)) do
 Controls[d.Name]={String=type(d.DefaultValue)=="string" and d.DefaultValue or "",
 Value=type(d.DefaultValue)=="number" and d.DefaultValue or 0,Boolean=d.DefaultValue==true,
 Trigger=function() end}
end
SecretStorage={["text.1"]={String=""}}
''')
        lua.execute(PLUGIN)
        lua.execute(b'''
Controls.IPAddress.String="127.0.0.1"
Controls.ClientId.String="plugin-version-test"
Controls.Enable.Boolean=true;Controls.Enable.EventHandler()
Sockets[1]:Open()
''')
        assert g.MqttClient.Options.ProtocolVersion==(selection or b"3.1.1")
        g.Sockets[1].Feed(g.Sockets[1],b"\x20\x03\x00\x00\x00" if selection==b"5.0" else b"\x20\x02\x00\x00")
        assert g.Controls.Connected.Boolean
        if selection==b"5.0":
            lua.execute(b'''
Controls.PublishTopic1.String="test/out"
Controls.PublishPayload1.String="hello"
Controls.PublishQos1.String="1"
Controls.Publish1.EventHandler()
Sockets[1]:Feed(string.char(64,3)..IdBytes(MqttClient.NextId)..string.char(16))
assert(Controls.PublishResult1.String=="ACK: no subscribers")
''')
    passed.append("plugin MQTT Version selection and missing-property compatibility")
    if len(sys.argv)>1:
        Path(sys.argv[1]).write_text(json.dumps({"scope":"MQTT5 fake-host wire tests; no Q-SYS runtime", "checks":passed},indent=2)+"\n")
    print(f"PASS: {len(passed)} MQTT 5 test groups")


if __name__=="__main__":
    main()
