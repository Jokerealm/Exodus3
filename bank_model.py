from __future__ import annotations
import hashlib
import math
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from xml.dom import minidom, Node
from sc2_cipher import decode_integer, decrypt, encrypt, encode_sequence
from skin_catalog import SKIN_NAMES, FREE_SKINS

HANDLE_RE=re.compile(r'\d+-S2-\d+-\d+')
MAX_MEDAL=2_706_911
RESOURCE_NAMES=[('钒','Vanadium'),('铬','Chromium'),('钛','Titanium'),('钨','Tungsten'),('金','Gold'),('铌','Niobium'),('锇','Osmium'),('铱','Iridium'),('钯','Palladium'),('钕','Neodymium'),('钷','Promethium'),('铽','Terbium'),('柚','Uranium'),('铪','Hafnium'),('钼','Molybdenum')]
CURRENCY_NAMES=['信用点','悬赏凭证','神器碎片','勋章显示副本','普通样本','稀有样本','超级样本']
EQUIPMENT={'W':('武器',26,9,'WS'),'PA':('动力装甲',18,9,'PAS'),'TO':('工具',7,6,None),'T':('炮塔',38,9,'TS'),'S':('建筑',36,9,'SS')}
REPLACEMENTS=[('1','on'),('2','tw'),('6','si'),('7','se'),('8','ei3'),('9','ni'),('0','ze'),('3','th'),('4','fo6'),('5','fi'),(' ','nu')]

def i32(value):return (int(value)+2**31)%2**32-2**31

def trunc_div(value,divisor):return (abs(value)//divisor)*(-1 if value<0 else 1)

def scramble(value):
    result=trunc_div(i32(value),3)
    for op,n in [('*',28),('*',17),('+',500),('*',5)]:result=i32(result*n if op=='*' else result+n)
    return trunc_div(result,3)

def transcribe(text):
    for old,new in REPLACEMENTS:text=text.replace(old,new)
    return text

def field_name(handle,name):return handle+name+transcribe(name)

def original_name(handle,encoded_name):
    if not encoded_name.startswith(handle):return None
    rest=encoded_name[len(handle):]
    for n in range(1,len(rest)+1):
        candidate=rest[:n]
        if candidate+transcribe(candidate)==rest:return candidate
    return None

def encode_integer(value,handle,name):
    text=str(scramble(value))+handle+name
    step=math.trunc(abs(math.sin(math.radians(len(text)*17)))*787)%97+11
    index=0;remaining=list(text);out=[]
    while remaining:
        index=(index+step)%len(remaining)+1
        out.append(remaining.pop(index-1))
    return field_name(handle,''.join(out))

def children(node,tag):return [n for n in node.childNodes if n.nodeType==Node.ELEMENT_NODE and n.tagName==tag]

class BankDocument:
    def __init__(self,data:bytes,path=None,handle=None):
        if len(data)>32*1024*1024:raise ValueError('存档文件超过32MB')
        if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise ValueError('不支持带外部实体声明的XML')
        self.original=data;self.path=Path(path) if path else None
        self.dom=minidom.parseString(data);self.root=self.dom.documentElement
        if self.root.tagName!='Bank':raise ValueError('这不是SC2Bank存档：缺少Bank根节点')
        self.sections={};self.keys={};self.changes={}
        for section in children(self.root,'Section'):
            name=section.getAttribute('name')
            if name in self.sections:raise ValueError('存档有重复的Section名称')
            self.sections[name]=section
            for key in children(section,'Key'):
                k=key.getAttribute('name')
                if (name,k) in self.keys:raise ValueError('存档有重复的Key名称')
                self.keys[name,k]=key
        if self.value('R','R') is None:raise ValueError('不是Exodus 3存档：未找到R/R资源区块')
        handles=set()
        for name in self.sections:
            m=HANDLE_RE.match(name)
            if m:handles.add(m.group())
        if len(handles)>1:raise ValueError('存档包含多个玩家ID，请使用对应账号的单独存档')
        detected=next(iter(handles),None)
        if detected and handle and detected!=handle:raise ValueError('指定玩家ID与存档中的玩家ID不一致')
        if not detected and self.path:
            candidates=[p.name for p in self.path.parents if HANDLE_RE.fullmatch(p.name)]
            detected=next((x for x in candidates if x!=self.path.parent.name),None)
        self.handle=detected or handle or ''
        self.author=self.path.parent.name if self.path and HANDLE_RE.fullmatch(self.path.parent.name) else ''
        self.bank_name=self.path.stem if self.path else 'EX3Data'
        self.original_hash=hashlib.sha256(data).hexdigest()
        self.resources=self.sequence('R','R')
        if len(self.resources)<9:raise ValueError('资源字段数量少于9，无法识别这个存档版本')
        self.currencies=self.sequence('C','C') if self.value('C','C') else []

    @classmethod
    def load(cls,path):
        p=Path(path)
        return cls(p.read_bytes(),p)

    def clone(self):
        other=BankDocument(self.dom.toxml(encoding='utf-8'),self.path,self.handle or None)
        other.original=self.original;other.original_hash=self.original_hash
        other.changes=dict(self.changes);other.author=self.author;other.bank_name=self.bank_name
        return other

    def value_node(self,section,key):
        item=self.keys.get((section,key))
        if item is None:return None
        values=children(item,'Value')
        return values[0] if len(values)==1 else None

    def value(self,section,key):
        value=self.value_node(section,key)
        if value is None or len(value.attributes)!=1:return None
        attr=value.attributes.item(0)
        return attr.name,attr.value

    def sequence(self,section,key):
        found=self.value(section,key)
        if found is None or found[0]!='string':raise ValueError(f'{section}/{key}不是可识别的加密整数串')
        try:return [decode_integer(token) for token in found[1].split()]
        except Exception as exc:raise ValueError(f'{section}/{key}解密失败：{exc}') from exc

    def set_value(self,section,key,type,value):
        value=str(value);before=self.value(section,key)
        if before==(type,value):return
        if section not in self.sections:
            sec=self.dom.createElement('Section');sec.setAttribute('name',section)
            self.root.appendChild(self.dom.createTextNode('\n    '));self.root.appendChild(sec)
            self.sections[section]=sec
        if (section,key) not in self.keys:
            node=self.dom.createElement('Key');node.setAttribute('name',key)
            self.sections[section].appendChild(self.dom.createTextNode('\n        '));self.sections[section].appendChild(node)
            self.keys[section,key]=node
        value_node=self.value_node(section,key)
        if value_node is None:
            value_node=self.dom.createElement('Value');self.keys[section,key].appendChild(value_node)
        while value_node.attributes.length:value_node.removeAttribute(value_node.attributes.item(0).name)
        value_node.setAttribute(type,value)
        identifier=(section,key)
        if identifier not in self.changes:self.changes[identifier]={'before':before,'after':(type,value)}
        else:self.changes[identifier]['after']=(type,value)
        if self.changes[identifier]['before']==(type,value):del self.changes[identifier]

    def require_handle(self):
        if not HANDLE_RE.fullmatch(self.handle):raise ValueError('请填写与游戏账号一致的玩家ID，如5-S2-1-3003153')

    def paired(self,section,name,value):
        self.require_handle();value=i32(value)
        self.set_value(field_name(self.handle,section),field_name(self.handle,name),'int',value)
        self.set_value(field_name(self.handle,section),field_name(self.handle,name+'-en'),'string',encode_integer(value,self.handle,name))

    def get_paired(self,section,name):
        found=self.value(field_name(self.handle,section),field_name(self.handle,name))
        return int(found[1]) if found and found[0]=='int' else None

    def medal(self):return self.get_paired('EECompany','Medal') if self.handle else None

    def medal_matches(self):
        n=self.medal()
        if n is None:return None
        found=self.value(field_name(self.handle,'EECompany'),field_name(self.handle,'Medal-en'))
        return bool(found and found[1]==encode_integer(n,self.handle,'Medal'))

    def set_medal(self,value):
        if not 0<=value<=MAX_MEDAL:raise ValueError(f'勋章必须在0–{MAX_MEDAL}之间')
        self.paired('EECompany','Medal',value)
        if len(self.currencies)>3:
            currencies=list(self.currencies);currencies[3]=value
            self.set_currencies(currencies)

    def set_resources(self,values):
        # The test map writes either 12 (solo) or 15 (multiplayer) values.
        # Explicitly enabling its minerals may extend a 12-value bank to 15.
        if len(values)!=len(self.resources) and (len(self.resources),len(values))!=(12,15):
            raise ValueError('仅支持保留原资源字段数量，或为12项存档补齐test版的3种矿物')
        if any(not 0<=x<=90_000_000 for x in values[:len(RESOURCE_NAMES)]):raise ValueError('资源数量必须在0–90,000,000之间')
        if values!=self.resources:
            old_tokens=self.value('R','R')[1].split()
            tokens=[old_tokens[i] if i<len(self.resources) and n==self.resources[i] else encrypt(n) for i,n in enumerate(values)]
            self.set_value('R','R','string',' '.join(tokens)+' ');self.resources=list(values)
            # Match the map's writer: checksum covers the serialized resources.
            self.paired('RS','RS',i32(sum(values)))

    def set_currencies(self,values):
        if len(values)!=len(self.currencies):raise ValueError('不能丢弃未知货币字段')
        if any(not 0<=x<=2_147_483_647 for x in values):raise ValueError('货币必须是非负32位整数')
        if values!=self.currencies:
            tokens=self.value('C','C')[1].split()
            tokens=[encrypt(n) if n!=old else tokens[i] for i,(n,old) in enumerate(zip(values,self.currencies))]
            self.set_value('C','C','string',' '.join(tokens)+' ');self.currencies=list(values)
            self.paired('CS','CS',i32(sum(values[:7])))

    def skin_unlocks(self):
        value=self.value('CUSTOM','SK')
        if value is None or value[1]=='':return []
        if value[0]!='string':raise ValueError('CUSTOM/SK不是皮肤解锁字符串')
        # Native multi-block writers may pad with zero bytes; the map's
        # ASCII table emits no characters for those bytes.
        text=decrypt(value[1]).rstrip(' \x00')
        if not text:return []
        if not re.fullmatch(r'\d+(?:,\d+)*',text):raise ValueError('无法识别皮肤解锁列表，请保留原值并检查存档版本')
        return list(dict.fromkeys(int(token) for token in text.split(',')))

    def skin_equipped(self):
        value=self.value('CUSTOM','MM')
        return decode_integer(value[1]) if value and value[0]=='string' and value[1] else 0

    def skin_silent(self):
        value=self.value('CUSTOM','SV')
        return bool(value and value[0]=='string' and value[1] and decode_integer(value[1])==1)

    def set_skin_unlocks(self,selected):
        selected=set(selected)
        if any(index not in SKIN_NAMES for index in selected):raise ValueError('皮肤索引超出当前地图范围')
        original=self.skin_unlocks()
        # Keep existing free/unknown/future entries and original order.
        requested=(selected-FREE_SKINS)|{i for i in original if i not in SKIN_NAMES or i in FREE_SKINS}
        ordered=[i for i in original if i in requested]
        ordered+=sorted(requested-set(ordered))
        if ordered==original:return
        text=','.join(str(i) for i in ordered)
        self.set_value('CUSTOM','SK','string',encrypt(text) if text else '')

    def set_skin_equipped(self,index):
        if index not in SKIN_NAMES:raise ValueError('当前地图仅支持皮肤索引0–41')
        if index not in FREE_SKINS and index not in self.skin_unlocks():
            owned=set(self.skin_unlocks())
            owned.add(index)
            self.set_skin_unlocks({i for i in owned if i in SKIN_NAMES})
        if index!=self.skin_equipped():self.set_value('CUSTOM','MM','string',encrypt(index))

    def set_skin_silent(self,enabled):
        if bool(enabled)!=self.skin_silent():self.set_value('CUSTOM','SV','string',encrypt(1 if enabled else 0))

    def equipment_values(self,section,index):
        found=self.value(section,str(index))
        return self.sequence(section,str(index)) if found else None

    def max_equipment_levels(self):
        self.require_handle()
        if len(self.resources)!=12:raise ValueError('装备满级仅支持当前12资源版本的存档')
        for section,(_,count,attributes,protected) in EQUIPMENT.items():
            for index in range(count):
                vector=self.equipment_values(section,index)
                if vector is None:continue
                if len(vector)<3+attributes:raise ValueError(f'{section}/{index}装备字段不完整')
                if vector[1]==20:continue
                # Level alone changes; prestige, points and attributes are retained.
                vector[1]=20
                self.set_value(section,str(index),'string',encode_sequence(vector))
                if protected:self.paired(protected,str(index),sum(vector[:3+attributes]))
        self.refresh_equipment_total()

    def refresh_equipment_total(self):
        total=0
        for section,(_,count,attributes,_) in EQUIPMENT.items():
            vectors=[self.equipment_values(section,i) or [0]*(3+attributes) for i in range(count)]
            total+=sum(sum(v[:3]) for v in vectors)
            if section=='TO':total+=sum(sum(v[3:9]) for v in vectors)
            else:
                # Preserve the original aggregate's diagonal array indexing.
                total+=count*sum(vectors[i][3+i-1] if len(vectors[i])>3+i-1 else 0 for i in range(1,10))
        self.paired('EC','ECA',i32(total))

    def paired_fields(self):
        fields=[]
        if not self.handle:return fields
        for (section,key),node in self.keys.items():
            value=self.value(section,key)
            if value and value[0]=='int':
                section_name=original_name(self.handle,section)
                property_name=original_name(self.handle,key)
                if section_name and property_name:
                    fields.append((section_name,property_name,int(value[1])))
        return sorted(fields,key=lambda v:(v[0],v[1]))

    def update_signature(self):
        signatures=children(self.root,'Signature')
        if not signatures or not self.changes:return
        self.require_handle()
        if not HANDLE_RE.fullmatch(self.author):raise ValueError('存档带签名，需要正确的地图作者ID；可从Banks子目录名识别')
        text=self.author+self.handle+self.bank_name
        order=lambda s:s.encode('utf-16-be')
        for name in sorted(self.sections,key=order):
            text+=name
            keys=sorted([k for sec,k in self.keys if sec==name],key=order)
            for key in keys:
                text+=key
                for child in sorted([x for x in self.keys[name,key].childNodes if x.nodeType==Node.ELEMENT_NODE],key=lambda x:order(x.tagName)):
                    if len(child.attributes)!=1:raise ValueError('无法计算带复杂节点的Bank签名')
                    attr=child.attributes.item(0);text+=child.tagName+attr.name
                    if attr.name!='text':text+=attr.value
        signatures[0].setAttribute('value',hashlib.sha1(text.encode('utf-8')).hexdigest().upper())

    def to_bytes(self):
        if not self.changes:return self.original
        self.update_signature()
        data=self.dom.toxml(encoding='utf-8')
        minidom.parseString(data)
        return data

    def save(self,target):
        target=Path(target)
        if self.path and target.resolve()==self.path.resolve() and self.path.exists():
            if hashlib.sha256(self.path.read_bytes()).hexdigest()!=self.original_hash:
                raise ValueError('原文件已被游戏或其他程序改变，请重新载入后再保存')
        data=self.to_bytes()
        target.parent.mkdir(parents=True,exist_ok=True)
        backup_data=target.read_bytes() if target.exists() else self.original
        backups=target.parent/'EX3-editor-backups';backups.mkdir(exist_ok=True)
        backup=backups/(target.stem+'_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.SC2Bank')
        backup.write_bytes(backup_data)
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent,prefix=target.name+'.',suffix='.tmp',delete=False) as f:
                temporary=Path(f.name);f.write(data);f.flush();os.fsync(f.fileno())
            os.replace(temporary,target)
        finally:
            if temporary and temporary.exists():temporary.unlink()
        return backup


def discover_banks():
    root=Path.home()/'Documents'/'StarCraft II'/'Accounts'
    if not root.exists():return []
    found=[]
    for p in root.glob('*/*/Banks/*/EX3Data.SC2Bank'):
        found.append(p)
    return sorted(found,key=lambda p:p.stat().st_mtime,reverse=True)
