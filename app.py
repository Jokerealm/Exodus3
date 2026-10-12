from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QRect,QRegularExpression,QSize
from PySide6.QtGui import QPainter,QPixmap,QColor,QFont,QIntValidator,QRegularExpressionValidator,QIcon,QPen
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QFrame,QLabel,QLineEdit,QPushButton,QCheckBox,QComboBox,QVBoxLayout,QHBoxLayout,QGridLayout,QGroupBox,QTabWidget,QPlainTextEdit,QTreeWidget,QTreeWidgetItem,QFileDialog,QMessageBox,QDialog,QListWidget,QDialogButtonBox,QGraphicsDropShadowEffect,QScrollArea,QSizePolicy)
from skin_catalog import SKIN_NAMES, FREE_SKINS
from sc2_cipher import decode_integer
from bank_model import (BankDocument,discover_banks,RESOURCE_NAMES,CURRENCY_NAMES,EQUIPMENT,MAX_MEDAL,encode_integer,field_name,original_name,HANDLE_RE)

ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
STYLE='''
QWidget {color:#e2e4fb;font-family:"Microsoft YaHei UI";font-size:13px;}
QMainWindow {background:#04040d;}
QFrame#header,QFrame#toolbar {background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #04040d,stop:0.55 #101527,stop:1 #04040d);border-bottom:1px solid #343647;}
QFrame#card {background:rgba(6,6,18,245);border:1px solid #666778;border-radius:10px;}
QLabel {background:transparent;border:none;}
QLabel#muted {color:#9194b0;font-size:12px;}
QLabel#gold {color:#f7ef76;font-weight:600;}
QLabel#section {color:#edeab1;font-weight:600;font-size:14px;}
QLabel#status {color:#a3b2d1;}
QLineEdit,QComboBox {background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #080822,stop:1 #171545);border:1px solid #4e43af;border-radius:3px;padding:3px 8px;selection-background-color:#4d68ad;font-family:Consolas,"Microsoft YaHei UI";}
QLineEdit:focus,QComboBox:focus {border:1px solid #9285f3;}
QLineEdit:disabled {color:#61637a;border-color:#27293a;background:#10101c;}
QLineEdit[role="medal"] {font-size:26px;font-weight:700;color:#fffbb6;padding:8px;}
QPushButton {background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #0c0c25,stop:0.55 #18164b,stop:1 #080822);border:1px solid #5146c3;border-radius:5px;padding:5px 12px;font-weight:600;}
QPushButton:hover {border-color:#a194ff;background:#262258;}
QPushButton:pressed {background:#080822;}
QPushButton:disabled {color:#585b78;border-color:#2d2c49;}
QPushButton#primary {border:1px solid #7d70e1;color:#ffffff;background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #43378d,stop:1 #211754);}
QPushButton#drop {color:#a0a4c7;border:1px dashed #626484;background:rgba(22,23,41,140);padding:8px;font-size:12px;}
QCheckBox {spacing:9px;padding:3px;}
QCheckBox::indicator {width:14px;height:14px;border:1px solid #716fb0;border-radius:2px;background:#111027;}
QCheckBox::indicator:checked {background:#4c79c7;border-color:#89b3f1;image:none;}
QCheckBox::indicator:checked:hover {background:#6895e0;}
QGroupBox {border:1px solid #353547;border-radius:4px;margin-top:14px;padding:13px 12px 10px;}
QGroupBox::title {subcontrol-origin:margin;left:9px;padding:0 6px;color:#edeab1;font-weight:600;}
QTabWidget::pane {border:none;background:transparent;}
QTabBar::tab {background:#0d0d20;border:1px solid #303047;color:#969bbd;padding:8px 20px;margin-bottom:10px;}
QTabBar::tab:selected {color:#eeecff;border-color:#6860b7;background:#1a1736;}
QTabBar::tab:first {border-top-left-radius:4px;}
QTabBar::tab:last {border-top-right-radius:4px;}
QTreeWidget,QPlainTextEdit,QListWidget {background:#0b0b1c;border:1px solid #35354e;border-radius:4px;color:#d4d8f4;alternate-background-color:#111127;}
QHeaderView::section {background:#17172e;color:#bcbed9;border:0px;border-right:1px solid #32324a;padding:8px;}
QTreeWidget::item:selected,QListWidget::item:selected {background:#2c315c;}
QScrollArea {border:none;background:transparent;}
QScrollBar:vertical {width:9px;background:#0e1022;border:none;}
QScrollBar::handle:vertical {background:#48466d;min-height:24px;border-radius:4px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0px;}
QDialog,QMessageBox {background:#0c0c20;}
QToolTip {background:#1f1c3c;border:1px solid #6b5a9f;color:#ededff;padding:6px;}
'''

class Backdrop(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.background=QPixmap(str(ROOT/'assets'/'background.jpg'))
    def paintEvent(self,event):
        painter=QPainter(self)
        if not self.background.isNull():
            image=self.background.scaled(self.size(),Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation)
            x=(self.width()-image.width())//2;y=(self.height()-image.height())//2
            painter.drawPixmap(x,y,image)
        painter.fillRect(self.rect(),QColor(2,4,14,48))

class Logo(QWidget):
    def __init__(self):super().__init__();self.setFixedSize(38,38)
    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor('#718bbb'),1));painter.setBrush(QColor('#a2c3d8'))
        from PySide6.QtGui import QPolygonF
        from PySide6.QtCore import QPointF
        for points in [[(19,2),(24,16),(19,19),(14,16)],[(36,19),(22,24),(19,19),(22,14)],[(19,36),(14,22),(19,19),(24,22)],[(2,19),(16,14),(19,19),(16,24)]]:
            painter.drawPolygon(QPolygonF([QPointF(x,y) for x,y in points]))

def label(text,name=None):
    w=QLabel(text)
    if name:w.setObjectName(name)
    return w

def line():
    w=QFrame();w.setFrameShape(QFrame.HLine);w.setStyleSheet('background:#373749;max-height:1px;border:none;');return w

def button(text,callback,name=None):
    w=QPushButton(text);w.clicked.connect(callback)
    if name:w.setObjectName(name)
    return w

def integer_edit(maximum=2_147_483_647,minimum=0):
    w=QLineEdit();w.setValidator(QIntValidator(minimum,maximum,w));w.setAlignment(Qt.AlignRight);w.setMinimumWidth(115)
    return w

def parse_integer(widget,name,maximum=2_147_483_647,minimum=0):
    text=widget.text().strip()
    if not text or not text.lstrip('-').isdigit():raise ValueError(f'{name}必须填写整数')
    value=int(text)
    if not minimum<=value<=maximum:raise ValueError(f'{name}必须在{minimum:,}–{maximum:,}之间')
    return value

class EditorWindow(QMainWindow):
    def __init__(self,state_dir=None):
        super().__init__();self.document=None;self.loading=False;self.extra_edits={};self.preview_document=None
        self.setWindowIcon(QIcon(str(ROOT/'assets'/'icon.ico')));self.setWindowTitle('Exodus 3 存档修改器 v1.2 · Bank Editor');self.resize(1320,920);self.setMinimumSize(1040,790)
        self.setAcceptDrops(True)
        self.state_dir=Path(state_dir) if state_dir else (Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).parent)/'data'
        self.draft_path=self.state_dir/'draft.json'
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self.refresh_preview)
        self.build_ui();self.refresh_enabled()
        self.setStyleSheet(STYLE + '\nQCheckBox::indicator:checked {image:url(\"' + str(ROOT/'assets'/'check.svg').replace('\\','/') + '\");}')
        QTimer.singleShot(0,self.show_existing_draft)

    def build_ui(self):
        body=QWidget();layout=QVBoxLayout(body);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0);self.setCentralWidget(body)
        header=QFrame();header.setObjectName('header');header.setFixedHeight(68)
        row=QHBoxLayout(header);row.setContentsMargins(22,12,22,12);row.addWidget(Logo())
        title=label('<span style="color:#f5f07b">B</span>ank Editor');title.setFont(QFont('Consolas',20,QFont.Bold));row.addWidget(title)
        sub=label('EXODUS 3  /  本地存档修改器','muted');row.addWidget(sub);row.addStretch()
        row.addWidget(label('<span style="color:#f5f07b">P</span>layer id:'))
        self.player=QLineEdit();self.player.setPlaceholderText('从存档自动识别');self.player.setFixedWidth(193);self.player.textChanged.connect(self.schedule)
        row.addWidget(self.player);row.addWidget(button('账号 / 存档',self.accounts));row.addWidget(button('使用帮助',self.help))
        layout.addWidget(header)
        toolbar=QFrame();toolbar.setObjectName('toolbar');toolbar.setFixedHeight(48)
        bar=QHBoxLayout(toolbar);bar.setContentsMargins(24,4,24,4)
        bar.addWidget(label('离线模式','muted'));bar.addStretch();bar.addWidget(label('<span style="color:#f5f07b">S</span>elect map:'))
        map_combo=QComboBox();map_combo.addItem('Exodus 3 · 火卫一矿业');map_combo.setFixedWidth(245);bar.addWidget(map_combo)
        self.autosave=QCheckBox('自动暂存草稿');self.autosave.setChecked(True);self.autosave.toggled.connect(self.schedule);bar.addWidget(self.autosave)
        bar.addWidget(button('恢复草稿',self.restore_draft));bar.addWidget(button('清除草稿',self.clear_draft));layout.addWidget(toolbar)
        backdrop=Backdrop();area_layout=QVBoxLayout(backdrop);area_layout.setContentsMargins(24,8,24,4);area_layout.setSpacing(8)
        outer=QScrollArea();outer.setWidgetResizable(True);outer.setStyleSheet('QScrollArea {background:transparent;} QScrollArea>QWidget>QWidget {background:transparent;}')
        container=QWidget();container_layout=QVBoxLayout(container);container_layout.setContentsMargins(0,0,0,0)
        container_layout.addStretch(1)
        card=QFrame();card.setObjectName('card');card.setMaximumWidth(990);card.setMinimumWidth(915)
        shadow=QGraphicsDropShadowEffect();shadow.setBlurRadius(35);shadow.setOffset(0,9);shadow.setColor(QColor(0,0,0,180));card.setGraphicsEffect(shadow)
        cl=QVBoxLayout(card);cl.setContentsMargins(20,17,20,17);cl.setSpacing(10)
        heading=QHBoxLayout();heading.addWidget(label('EXODUS 3','gold'));heading.addWidget(label('存档控制台','muted'));heading.addStretch()
        self.loaded_badge=label('等待导入','muted');heading.addWidget(self.loaded_badge);cl.addLayout(heading)
        meta=QHBoxLayout();grid=QGridLayout();grid.setHorizontalSpacing(12);grid.setVerticalSpacing(8)
        grid.addWidget(label('Bank name:','gold'),0,0)
        self.bank_name=QLineEdit('EX3Data');self.bank_name.setReadOnly(True);self.bank_name.setFixedWidth(175);grid.addWidget(self.bank_name,0,1)
        grid.addWidget(label('Author id:','gold'),1,0)
        self.author=QLineEdit();self.author.setPlaceholderText('从存档目录自动识别');self.author.setFixedWidth(175);self.author.textChanged.connect(self.schedule);grid.addWidget(self.author,1,1)
        meta.addLayout(grid);meta.addSpacing(15)
        self.file_label=label('请导入现有的 EX3Data.SC2Bank\n或将文件拖到窗口中','muted');self.file_label.setWordWrap(True);meta.addWidget(self.file_label,1)
        drop=button('拖入存档\n或点击选择文件',self.choose_file,'drop');drop.setFixedSize(168,69);meta.addWidget(drop);cl.addLayout(meta);cl.addWidget(line())
        self.tabs=QTabWidget();self.tabs.currentChanged.connect(self.tab_changed)
        self.basic=QWidget();self.create_basic(self.basic);self.tabs.addTab(self.basic,'常规编辑')
        self.skin_tab=QWidget();self.create_skin_tab(self.skin_tab);self.tabs.addTab(self.skin_tab,'皮肤 / 外观')
        self.advanced=QWidget();self.create_advanced(self.advanced);self.tabs.addTab(self.advanced,'更多字段')
        self.preview_tab=QWidget();self.create_preview(self.preview_tab);self.tabs.addTab(self.preview_tab,'修改预览')
        cl.addWidget(self.tabs)
        self.usage_tip=label('提示：修改存档是对作者工作的不敬，仅供体验，请在24小时内放弃修改。','usage_tip');self.usage_tip.setWordWrap(True);self.usage_tip.setStyleSheet('color:#d9bd81;font-size:12px;');cl.addWidget(self.usage_tip)
        cl.addWidget(line())
        footer=QHBoxLayout();self.summary=label('导入后即可编辑','status');self.summary.setWordWrap(True);footer.addWidget(self.summary,1)
        self.reset_button=button('重置修改',self.reset);footer.addWidget(self.reset_button)
        self.copy_button=button('复制 XML',self.copy_xml);footer.addWidget(self.copy_button)
        self.overwrite_button=button('备份并修改',self.overwrite);footer.addWidget(self.overwrite_button)
        self.export_button=button('导出存档…',self.export,'primary');footer.addWidget(self.export_button);cl.addLayout(footer)
        container_layout.addWidget(card,0,Qt.AlignHCenter);container_layout.addStretch(1);outer.setWidget(container);area_layout.addWidget(outer,1)
        self.status=label('全程本地处理  ·  导出时自动备份  ·  其他字段完整保留','muted');self.status.setAlignment(Qt.AlignCenter);area_layout.addWidget(self.status)
        layout.addWidget(backdrop,1)

    def create_basic(self,parent):
        columns=QHBoxLayout(parent);columns.setContentsMargins(0,0,0,0);columns.setSpacing(25)
        left=QWidget();ll=QVBoxLayout(left);ll.setContentsMargins(0,0,0,0);ll.setSpacing(8)
        note=label('载入存档后修改需要的数值。\n未改动的资源、装备及其他数据会保留。','muted');note.setWordWrap(True);ll.addWidget(note)
        currencies=QGroupBox('货币 / 样本');cg=QGridLayout(currencies);cg.setVerticalSpacing(7);self.currency_edits={}
        order=[3,0,1,2,4,5,6]
        for position,index in enumerate(order):
            row=position//2;col=(position%2)*2
            cg.addWidget(label(('公司勋章' if index==3 else CURRENCY_NAMES[index])+':','gold' if index==3 else None),row,col)
            entry=integer_edit(MAX_MEDAL if index==3 else 2_147_483_647)
            entry.setMinimumWidth(85);entry.setMaximumWidth(125);entry.setText('0');entry.textChanged.connect(self.schedule);cg.addWidget(entry,row,col+1)
            if index==3:self.medal=entry
            else:self.currency_edits[index]=entry
        cg.addWidget(button('复制勋章编码',self.copy_medal),3,2,1,2)
        self.medal_status=label('勋章及其他货币随存档一起载入','muted');self.medal_status.setWordWrap(True);cg.addWidget(self.medal_status,4,0,1,4)
        self.repair=QCheckBox('重新生成勋章校验');self.repair.toggled.connect(self.schedule);cg.addWidget(self.repair,5,0,1,4)
        ll.addWidget(currencies)
        options=QGroupBox('装备选项');ol=QVBoxLayout(options);ol.setSpacing(1)
        self.upgrade=QCheckBox('一键满级（20级，威望保持不变）')
        self.upgrade.setToolTip('将已有装备设为20级，保留威望、改造点数、属性和解锁状态')
        self.upgrade.toggled.connect(self.schedule);ol.addWidget(self.upgrade)
        ll.addWidget(options);ll.addStretch();columns.addWidget(left,5)
        resources=QGroupBox('Resources · 资源');rg=QGridLayout(resources);rg.setHorizontalSpacing(13);rg.setVerticalSpacing(5);self.resource_edits=[]
        for i,(ch,en) in enumerate(RESOURCE_NAMES):
            text=label(f'<span style="color:#efeeb0">{ch}</span>  {en}:');rg.addWidget(text,i,0)
            edit=integer_edit(90_000_000);edit.setText('0');edit.textChanged.connect(self.schedule);rg.addWidget(edit,i,1);self.resource_edits.append(edit)
        actions=QHBoxLayout();actions.addWidget(button('全部设为…',self.set_all_resources));actions.addWidget(label('0 – 90,000,000','muted'));rg.addLayout(actions,12,0,1,2)
        rg.setRowStretch(13,1);columns.addWidget(resources,4)

    def create_skin_tab(self,parent):
        self.skin_error=None;self.skin_items={};self.skin_loaded=False
        l=QVBoxLayout(parent);l.setContentsMargins(0,0,0,0);l.setSpacing(10)
        self.skin_info=label('人物皮肤：42款。标准和“普通”默认免费，其余可以写入存档解锁名单。','muted');self.skin_info.setWordWrap(True);l.addWidget(self.skin_info)
        controls=QHBoxLayout();controls.addWidget(label('穿戴皮肤:','gold'))
        self.skin_current=QComboBox();self.skin_current.setMinimumWidth(240);self.skin_current.setToolTip('选择人物皮肤时，会同时勾选它的解锁记录');self.skin_current.currentIndexChanged.connect(self.skin_selected);controls.addWidget(self.skin_current,1)
        self.skin_silent=QCheckBox('无陆战队员语音');self.skin_silent.toggled.connect(self.schedule);controls.addWidget(self.skin_silent)
        controls.addWidget(button('解锁全部人物皮肤',self.unlock_all_skins));l.addLayout(controls)
        self.skin_search=QLineEdit();self.skin_search.setPlaceholderText('搜索皮肤名称…');self.skin_search.textChanged.connect(self.filter_skins);l.addWidget(self.skin_search)
        self.skin_tree=QTreeWidget();self.skin_tree.setHeaderLabels(['人物皮肤','索引','解锁记录']);self.skin_tree.setColumnWidth(0,475);self.skin_tree.setColumnWidth(1,70);self.skin_tree.setAlternatingRowColors(True);self.skin_tree.setMinimumHeight(300);self.skin_tree.itemChanged.connect(self.skin_item_changed);l.addWidget(self.skin_tree,1)
        self.skin_details=label('导入后显示当前外观设置','muted');self.skin_details.setWordWrap(True);l.addWidget(self.skin_details)
        note=label('此处显示存档解锁记录，地图购买名单权限不会列出。枪皮、头顶及脚下光环还会检查地图名单，人物皮肤勾选不会自动解锁它们。','muted');note.setWordWrap(True);l.addWidget(note)

    def populate_skins(self,doc):
        self.skin_tree.clear();self.skin_items={};self.skin_current.clear();self.skin_error=None;self.skin_loaded=False
        try:
            owned=set(doc.skin_unlocks());equipped=doc.skin_equipped();silent=doc.skin_silent()
            for index,name in SKIN_NAMES.items():self.skin_current.addItem(name,index)
            if equipped not in SKIN_NAMES:self.skin_current.addItem('原存档未知皮肤 #'+str(equipped),equipped)
            self.skin_current.setCurrentIndex(self.skin_current.findData(equipped));self.skin_silent.setChecked(silent)
            groups={0:QTreeWidgetItem(['陆战队员','','']),1:QTreeWidgetItem(['武装佣兵','',''])}
            for group in groups.values():self.skin_tree.addTopLevelItem(group);group.setExpanded(True)
            for index,name in SKIN_NAMES.items():
                item=QTreeWidgetItem([name,str(index),'默认免费' if index in FREE_SKINS else ('已在存档中解锁' if index in owned else '未写入解锁记录')])
                item.setFlags(item.flags()|Qt.ItemIsUserCheckable);item.setData(0,Qt.UserRole,index)
                item.setCheckState(0,Qt.Checked if index in owned or index in FREE_SKINS else Qt.Unchecked)
                if index in FREE_SKINS:item.setFlags(item.flags()&~Qt.ItemIsUserCheckable);item.setToolTip(0,'地图默认免费，无需添加存档解锁记录')
                groups[0 if index<28 else 1].addChild(item);self.skin_items[index]=item
            details=[]
            for key,name,mapping in [('HH','头顶光环',{0:'关闭',1:'标准',2:'迷你'}),('HF','脚下光环',{0:'关闭',1:'开启'}),('GG','枪皮',{0:'无',1:'狙击枪',2:'机枪',3:'已废弃',4:'转轮机枪',5:'幽魂步枪',6:'焚烧枪',7:'战神武器',8:'矿工钻头',9:'火箭筒',10:'融合轨道炮',11:'M4A1',12:'DSR55'})]:
                value=doc.value('CUSTOM',key)
                if value and value[0]=='string' and value[1]:
                    index=decode_integer(value[1]);details.append(name+'：'+mapping.get(index,str(index)))
                else:details.append(name+'：未单独保存')
            self.skin_details.setText('  ·  '.join(details))
            self.skin_info.setText(f'人物皮肤共42款 · 当前穿戴：{SKIN_NAMES.get(equipped,"未知")} · 存档解锁记录：{len(owned)}项')
            self.skin_loaded=True;self.skin_tab.setEnabled(True);self.filter_skins()
        except Exception as exc:
            self.skin_error=str(exc);self.skin_info.setText('皮肤字段无法识别，导出时会保留原内容：'+str(exc));self.skin_tab.setEnabled(False)

    def refresh_skin_state(self):
        if not self.document or not self.skin_loaded or self.skin_error:return
        owned=set(self.document.skin_unlocks());selected=self.selected_skins();current=self.skin_current.currentData()
        was_loading=self.loading;self.loading=True
        for index,item in self.skin_items.items():
            if index in FREE_SKINS:text='默认免费'
            elif index in selected:text='已在存档中解锁' if index in owned else '待解锁'
            else:text='将移除存档记录' if index in owned else '未写入解锁记录'
            item.setText(2,text)
        name=SKIN_NAMES.get(current,'未知 #'+str(current))
        self.skin_info.setText(f'人物皮肤共42款 · 穿戴：{name} · 将保存的解锁记录：{len(selected-FREE_SKINS)}项（另有2款免费）')
        self.loading=was_loading

    def selected_skins(self):return {index for index,item in self.skin_items.items() if item.checkState(0)==Qt.Checked}

    def skin_selected(self,*args):
        if self.loading or not self.skin_loaded:return
        index=self.skin_current.currentData()
        if index in self.skin_items and index not in FREE_SKINS:self.skin_items[index].setCheckState(0,Qt.Checked)
        self.schedule()

    def skin_item_changed(self,item,column):
        if self.loading:return
        index=item.data(0,Qt.UserRole)
        if index in self.skin_items and index not in FREE_SKINS:
            self.loading=True;item.setText(2,'将写入解锁记录' if item.checkState(0)==Qt.Checked else '未写入解锁记录');self.loading=False
            self.schedule()

    def unlock_all_skins(self):
        if not self.document or not self.skin_loaded:return
        self.loading=True
        for index,item in self.skin_items.items():
            item.setCheckState(0,Qt.Checked)
            if index not in FREE_SKINS:item.setText(2,'将写入解锁记录')
        self.loading=False;self.refresh_preview();self.status.setText('全部人物皮肤已勾选，导出后写入存档')

    def filter_skins(self,*args):
        text=self.skin_search.text().lower()
        for i in range(self.skin_tree.topLevelItemCount()):
            group=self.skin_tree.topLevelItem(i);visible=False
            for j in range(group.childCount()):
                item=group.child(j);show=not text or text in (item.text(0)+' '+item.text(1)).lower();item.setHidden(not show);visible=visible or show
            group.setHidden(not visible)

    def create_advanced(self,parent):
        l=QVBoxLayout(parent);l.setContentsMargins(0,0,0,0)
        info=label('公司区块的其他整数可同步生成配套编码；下方可查看存档中的所有字段。','muted');info.setWordWrap(True);l.addWidget(info)
        editrow=QHBoxLayout();self.company_field=QComboBox();self.company_field.setMinimumWidth(240);self.company_field.currentIndexChanged.connect(self.company_selected);editrow.addWidget(self.company_field,1)
        self.company_value=integer_edit(2_147_483_647,-2_147_483_648);editrow.addWidget(self.company_value)
        self.apply_company=button('应用此字段',self.apply_company_field);editrow.addWidget(self.apply_company);l.addLayout(editrow)
        self.search=QLineEdit();self.search.setPlaceholderText('搜索区块、键名或值…');self.search.textChanged.connect(self.filter_tree);l.addWidget(self.search)
        self.tree=QTreeWidget();self.tree.setHeaderLabels(['区块 / 键名','类型','值']);self.tree.setAlternatingRowColors(True);self.tree.setColumnWidth(0,350);self.tree.setColumnWidth(1,65);self.tree.setMinimumHeight(380);l.addWidget(self.tree,1)

    def create_preview(self,parent):
        l=QVBoxLayout(parent);l.setContentsMargins(0,0,0,0)
        self.preview_label=label('只展示本次修改；原始存档不会在这里被写入。','muted');l.addWidget(self.preview_label)
        self.change_tree=QTreeWidget();self.change_tree.setHeaderLabels(['修改字段','原值','新值']);self.change_tree.setColumnWidth(0,400);self.change_tree.setColumnWidth(1,235);self.change_tree.setMinimumHeight(130);l.addWidget(self.change_tree)
        self.xml_preview=QPlainTextEdit();self.xml_preview.setReadOnly(True);self.xml_preview.setFont(QFont('Consolas',11));self.xml_preview.setMinimumHeight(280);l.addWidget(self.xml_preview,2)

    def schedule(self,*args):
        if not self.loading:self.timer.start(400)

    def refresh_enabled(self):
        enabled=self.document is not None
        for w in [self.basic,self.skin_tab,self.advanced,self.reset_button,self.copy_button,self.export_button,self.overwrite_button]:w.setEnabled(enabled)
        self.player.setReadOnly(enabled and bool(self.document.handle))

    def choose_file(self):
        path,_=QFileDialog.getOpenFileName(self,'选择 Exodus 3 存档',str(Path.home()/'Documents'/'StarCraft II'),'SC2 存档 (*.SC2Bank *.sc2bank *.xml *.txt);;所有文件 (*)')
        if path:self.load_path(path)

    def load_path(self,path,quiet=False):
        try:
            doc=BankDocument.load(path)
            self.load_document(doc)
            self.status.setText('已载入：'+doc.path.name+'  ·  玩家 '+doc.handle);self.status.setToolTip(str(doc.path))
            return True
        except Exception as exc:
            if not quiet:self.error(str(exc))
            return False

    def load_document(self,doc):
        self.loading=True;self.document=doc;self.extra_edits={};self.timer.stop()
        self.player.setText(doc.handle);self.author.setText(doc.author);self.bank_name.setText(doc.bank_name)
        self.loaded_badge.setText(f'已载入 · {len(doc.sections)} 个区块')
        self.file_label.setText(doc.path.name if doc.path else '已载入存档')
        self.file_label.setToolTip(str(doc.path or ''))
        n=doc.medal();self.medal.setText(str(n if n is not None else 0))
        self.medal.setEnabled(n is not None);self.repair.setEnabled(n is not None);self.repair.setChecked(False)
        state=doc.medal_matches();self.medal_status.setText('原存档勋章校验一致' if state else ('原存档校验不匹配，可勾选重新生成' if state is False else '此存档没有公司勋章字段'))
        self.medal_status.setStyleSheet('color:#91caa8;' if state else 'color:#d9bd81;')
        for i,edit in enumerate(self.resource_edits):
            edit.setEnabled(i<len(doc.resources));edit.setText(str(doc.resources[i]) if i<len(doc.resources) else '');edit.setToolTip('随存档保留' if i<len(doc.resources) else '此版本没有该资源字段')
        for i,edit in self.currency_edits.items():edit.setEnabled(i<len(doc.currencies));edit.setText(str(doc.currencies[i]) if i<len(doc.currencies) else '')
        self.upgrade.setChecked(False);self.upgrade.setEnabled(len(doc.resources)==12)
        self.company_field.clear()
        for section,name,value in doc.paired_fields():
            if section=='EECompany' and name!='Medal':self.company_field.addItem(name,(name,value))
        self.apply_company.setEnabled(self.company_field.count()>0)
        self.company_selected();self.populate_tree(doc);self.populate_skins(doc);self.loading=False;self.refresh_enabled();self.skin_tab.setEnabled(self.skin_error is None);self.refresh_preview()

    def build_document(self):
        if self.document is None:raise ValueError('请先导入存档')
        doc=self.document.clone()
        handle=self.player.text().strip()
        if self.document.handle and handle!=self.document.handle:raise ValueError('玩家ID必须与原存档一致')
        doc.handle=handle;doc.author=self.author.text().strip();doc.require_handle()
        resources=list(doc.resources)
        for i,w in enumerate(self.resource_edits):
            if i<len(resources):resources[i]=parse_integer(w,RESOURCE_NAMES[i][0],90_000_000)
        doc.set_resources(resources)
        currencies=list(doc.currencies)
        for i,w in self.currency_edits.items():
            if i<len(currencies):currencies[i]=parse_integer(w,CURRENCY_NAMES[i])
        doc.set_currencies(currencies)
        if doc.medal() is not None:
            n=parse_integer(self.medal,'勋章',MAX_MEDAL)
            if n!=self.document.medal() or self.repair.isChecked():doc.set_medal(n)
        for name,value in self.extra_edits.items():doc.paired('EECompany',name,value)
        if self.upgrade.isChecked():doc.max_equipment_levels()
        if self.skin_loaded and self.skin_error is None:
            doc.set_skin_unlocks(self.selected_skins())
            selected=self.skin_current.currentData()
            if selected!=self.document.skin_equipped():doc.set_skin_equipped(selected)
            doc.set_skin_silent(self.skin_silent.isChecked())
        doc.to_bytes()
        return doc

    def refresh_preview(self):
        if self.document is None:return
        try:
            self.preview_document=self.build_document();count=len(self.preview_document.changes);self.refresh_skin_state()
            self.summary.setText(f'待导出 · {count} 个字段已修改' if count else '未修改 · 其他字段保留')
            self.summary.setStyleSheet('color:#eee7ac;' if count else 'color:#a3b2d1;')
            for w in [self.export_button,self.copy_button,self.overwrite_button]:w.setEnabled(True)
            if self.tabs.currentWidget()==self.preview_tab:self.populate_preview()
            if self.autosave.isChecked():self.save_draft()
        except Exception as exc:
            self.preview_document=None;self.summary.setText(str(exc));self.summary.setStyleSheet('color:#e39b99;')
            for w in [self.export_button,self.copy_button,self.overwrite_button]:w.setEnabled(False)

    def populate_preview(self):
        if not self.preview_document:return
        self.change_tree.clear()
        for (section,key),change in self.preview_document.changes.items():
            sec=original_name(self.preview_document.handle,section) or section
            name=original_name(self.preview_document.handle,key) or key
            before=change['before'][1] if change['before'] else '（新增）';after=change['after'][1]
            item=QTreeWidgetItem([sec+' / '+name,before,after]);item.setToolTip(1,before);item.setToolTip(2,after);self.change_tree.addTopLevelItem(item)
        self.xml_preview.setPlainText(self.preview_document.to_bytes().decode('utf-8-sig'))
        self.preview_label.setText(f'共 {len(self.preview_document.changes)} 个字段改变 · 导出时会备份原内容')

    def populate_tree(self,doc):
        self.tree.clear()
        for section in doc.sections:
            short=original_name(doc.handle,section) or section
            parent=QTreeWidgetItem([short,'','']);parent.setToolTip(0,section);self.tree.addTopLevelItem(parent)
            for (sec,key),node in doc.keys.items():
                if sec!=section:continue
                value=doc.value(sec,key);shortkey=original_name(doc.handle,key) or key
                kind,text=value if value else ('复杂节点',node.toxml())
                item=QTreeWidgetItem([shortkey,kind,text]);item.setToolTip(0,key);item.setToolTip(2,text);parent.addChild(item)
        self.filter_tree()

    def filter_tree(self,*args):
        q=self.search.text().lower()
        for i in range(self.tree.topLevelItemCount()):
            parent=self.tree.topLevelItem(i);has=False
            for j in range(parent.childCount()):
                child=parent.child(j);show=not q or q in ' '.join([parent.text(0)]+[child.text(k) for k in range(3)]).lower()
                child.setHidden(not show);has=has or show
            parent.setHidden(not has);parent.setExpanded(bool(q and has))

    def tab_changed(self,index):
        if getattr(self,'preview_tab',None) is not None and self.tabs.currentWidget()==self.preview_tab:self.refresh_preview();self.populate_preview()

    def company_selected(self,*args):
        data=self.company_field.currentData()
        if data:self.company_value.setText(str(self.extra_edits.get(data[0],data[1])))

    def apply_company_field(self):
        data=self.company_field.currentData()
        if not data:return
        try:
            value=parse_integer(self.company_value,data[0],2_147_483_647,-2_147_483_648)
            if value==data[1]:self.extra_edits.pop(data[0],None)
            else:self.extra_edits[data[0]]=value
            self.refresh_preview();self.status.setText(data[0]+' 已加入本次修改')
        except Exception as exc:self.error(str(exc))

    def set_all_resources(self):
        if not self.document:return
        dialog=QDialog(self);dialog.setWindowTitle('批量设置资源');l=QVBoxLayout(dialog)
        l.addWidget(label('填写所有现有资源的数量：'))
        entry=integer_edit(90_000_000);entry.setText('1000000');l.addWidget(entry)
        controls=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);controls.accepted.connect(dialog.accept);controls.rejected.connect(dialog.reject);l.addWidget(controls)
        if dialog.exec()==QDialog.Accepted:
            try:
                n=parse_integer(entry,'资源',90_000_000)
                for w in self.resource_edits:
                    if w.isEnabled():w.setText(str(n))
                self.refresh_preview()
            except Exception as exc:self.error(str(exc))

    def accounts(self):
        files=discover_banks()
        if not files:self.choose_file();return
        dialog=QDialog(self);dialog.setWindowTitle('选择本机账号存档');dialog.resize(850,280);l=QVBoxLayout(dialog)
        l.addWidget(label('以下列表只读取本机 StarCraft II 账号目录：','muted'));lst=QListWidget();l.addWidget(lst)
        for path in files:
            try:
                d=BankDocument.load(path);lst.addItem(f'{d.handle}  |  勋章 {d.medal() if d.medal() is not None else "—"}  |  作者 {d.author}')
                lst.item(lst.count()-1).setToolTip(str(path))
            except Exception:lst.addItem(str(path))
        lst.setCurrentRow(0)
        controls=QDialogButtonBox(QDialogButtonBox.Open|QDialogButtonBox.Cancel);controls.accepted.connect(dialog.accept);controls.rejected.connect(dialog.reject);l.addWidget(controls);lst.itemDoubleClicked.connect(lambda *_:dialog.accept())
        if dialog.exec()==QDialog.Accepted and lst.currentRow()>=0:self.load_path(files[lst.currentRow()])

    def save_draft(self):
        if not self.document or not self.document.path:return
        state={'path':str(self.document.path),'source_sha256':self.document.original_hash,'handle':self.player.text(),'author':self.author.text(),'medal':self.medal.text(),'repair':self.repair.isChecked(),
               'resources':[w.text() for w in self.resource_edits],'currencies':{str(i):w.text() for i,w in self.currency_edits.items()},
               'upgrade':self.upgrade.isChecked(),'extra_edits':self.extra_edits,
               'skins':sorted(self.selected_skins()) if self.skin_loaded else None,'skin_equipped':self.skin_current.currentData() if self.skin_loaded else None,'skin_silent':self.skin_silent.isChecked()}
        try:
            self.state_dir.mkdir(parents=True,exist_ok=True)
            temp=self.draft_path.with_suffix('.tmp');temp.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(temp,self.draft_path)
        except OSError:self.status.setText('草稿暂存失败；仍可导出存档')

    def show_existing_draft(self):
        if self.draft_path.exists() and self.document is None:self.status.setText('发现上次草稿，可点击右上方“恢复草稿”继续编辑')

    def restore_draft(self):
        if not self.draft_path.exists():self.status.setText('没有已保存的草稿');return
        try:
            state=json.loads(self.draft_path.read_text(encoding='utf-8'));doc=BankDocument.load(state['path'])
            if doc.original_hash!=state['source_sha256']:raise ValueError('原始存档已改变，不能直接恢复旧草稿；请重新载入文件')
            self.loading=True;self.load_document(doc);self.loading=True
            self.player.setText(state.get('handle',doc.handle));self.author.setText(state.get('author',doc.author));self.medal.setText(state['medal']);self.repair.setChecked(state['repair'])
            for w,value in zip(self.resource_edits,state['resources']):w.setText(value)
            for i,w in self.currency_edits.items():w.setText(state['currencies'].get(str(i),w.text()))
            self.upgrade.setChecked(state.get('upgrade',False));self.extra_edits={k:int(v) for k,v in state['extra_edits'].items()}
            if self.skin_loaded and state.get('skins') is not None:
                selected=set(state['skins'])
                for index,item in self.skin_items.items():item.setCheckState(0,Qt.Checked if index in selected or index in FREE_SKINS else Qt.Unchecked)
                position=self.skin_current.findData(state.get('skin_equipped'))
                if position>=0:self.skin_current.setCurrentIndex(position)
                self.skin_silent.setChecked(state.get('skin_silent',False))
            self.loading=False;self.refresh_preview();self.company_selected();self.status.setText('已恢复草稿；游戏存档尚未写入')
        except Exception as exc:self.loading=False;self.error(str(exc))

    def clear_draft(self):
        if self.draft_path.exists():self.draft_path.unlink()
        self.autosave.setChecked(False);self.status.setText('已清除编辑器草稿，原始存档未改变')

    def reset(self):
        if self.document:self.load_document(self.document);self.status.setText('本次修改已重置为导入时的内容')

    def copy_xml(self):
        try:
            doc=self.build_document();QApplication.clipboard().setText(doc.to_bytes().decode('utf-8-sig'));self.status.setText('完整存档 XML 已复制到剪贴板')
        except Exception as exc:self.error(str(exc))

    def copy_medal(self):
        if not self.document:return
        try:
            doc=self.build_document();n=parse_integer(self.medal,'勋章',MAX_MEDAL)
            QApplication.clipboard().setText(encode_integer(n,doc.handle,'Medal'));self.status.setText('Medal-en 编码已复制；导出仍需同时保存整数和配套字段')
        except Exception as exc:self.error(str(exc))

    def export(self):
        if not self.document:return
        default=self.document.path.with_name(self.document.path.stem+'_modified.SC2Bank')
        target,_=QFileDialog.getSaveFileName(self,'导出修改后的存档',str(default),'SC2 存档 (*.SC2Bank)')
        if target:self.save_target(target)

    def overwrite(self):
        if not self.document or not self.document.path:return
        answer=QMessageBox.question(self,'备份并修改','先关闭正在运行的地图。\n将备份原文件，再把本次修改写入：\n'+str(self.document.path),QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
        if answer==QMessageBox.Yes:self.save_target(self.document.path)

    def save_target(self,target):
        try:
            doc=self.build_document();backup=doc.save(target)
            self.status.setText('已保存：'+Path(target).name+'  ·  原内容已备份');self.status.setToolTip(str(target)+'\n备份：'+str(backup));self.saved_data=doc.to_bytes()
            QMessageBox.information(self,'保存完成','存档已保存。\n\n'+str(target)+'\n\n原内容已备份到：\n'+str(backup)+'\n\n若另存为副本，游戏读取时文件名需要为 EX3Data.SC2Bank。')
            if self.document.path and Path(target).resolve()==self.document.path.resolve():self.load_path(target,quiet=True)
        except Exception as exc:self.error(str(exc))

    def error(self,message):QMessageBox.warning(self,'无法完成操作',message)

    def help(self):
        QMessageBox.information(self,'使用帮助','1. 点击“账号 / 存档”或拖入 EX3Data.SC2Bank。\n2. 修改勋章、12种资源、货币、装备或人物皮肤。\n3. 在“修改预览”核对，再导出副本或备份并修改。\n\n自动暂存只保存编辑器草稿，不会自动写入游戏存档。\n每次保存都会备份原内容，并保留其他字段。\n\n勋章与汇总校验已按提取的地图源码生成；新数值仍需在游戏中验证。\n“更多字段”可修改公司区块其他整数，并查看全部字段。\n\n背景参考：DarthVan / StarCraft2-Bank-Restorer。')

    def closeEvent(self,event):
        if self.document:
            if self.autosave.isChecked():self.save_draft()
            elif self.preview_document and self.preview_document.changes and getattr(self,'saved_data',None)!=self.preview_document.to_bytes():
                if QMessageBox.question(self,'关闭修改器','本次修改尚未导出，仍要关闭吗？',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:
                    event.ignore();return
        event.accept()

    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls() and len(event.mimeData().urls())==1 and event.mimeData().urls()[0].isLocalFile():event.acceptProposedAction()
    def dropEvent(self,event):
        paths=[u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if len(paths)==1:self.load_path(paths[0]);event.acceptProposedAction()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('bank',nargs='?');parser.add_argument('--render');parser.add_argument('--smoke',action='store_true');args=parser.parse_args()
    app=QApplication(sys.argv);app.setApplicationName('Exodus3BankEditor');app.setStyle('Fusion')
    window=EditorWindow(state_dir=Path(args.render).parent/'ui-test-data' if args.render else None)
    if args.bank:window.load_path(args.bank,quiet=bool(args.render or args.smoke))
    if args.render or args.smoke:
        window.setAttribute(Qt.WA_DontShowOnScreen,True);window.show();app.processEvents()
        if args.render:
            window.grab().save(args.render);print('RENDERED '+args.render,flush=True)
        if args.smoke:print('GUI_SMOKE_OK',flush=True)
        window.close();return 0
    window.show();return app.exec()

if __name__=='__main__':
    try:sys.exit(main())
    except Exception:
        import traceback
        log=(Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).parent)/'error.log'
        try:log.write_text(traceback.format_exc(),encoding='utf-8')
        except OSError:pass
        raise
