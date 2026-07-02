import json, subprocess, sys, re
from pathlib import Path
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGraphicsScene, QGraphicsView, QGraphicsRectItem, QGraphicsPathItem,
    QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem,
    QSplitter, QMenu, QInputDialog, QFileDialog, QDialog, QFormLayout, QTextEdit, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox
)
from PyQt6.QtCore import Qt, QPointF, QRectF, QLineF, QEvent
from PyQt6.QtGui import QColor, QBrush, QPen, QFont, QPainter, QPainterPath, QCursor

from ...core.config import SETTINGS
from ...core.style import THEME, STYLESHEET
from ...core.workers import WorkflowWorker
from ..widgets import LogView

NODE_W, NODE_H = 160, 70

class FlowNode(QGraphicsRectItem):
    TYPES = {
        "trigger":  {"color":"#0e3a50","border":"#1a7fa0","emoji":"🔵","label":"Trigger"},
        "ai":       {"color":"#1e1040","border":"#6e56cf","emoji":"🤖","label":"AI Task"},
        "git":      {"color":"#0e2a1e","border":"#3ecf8e","emoji":"📁","label":"Git"},
        "terminal": {"color":"#2a1e0a","border":"#f7b731","emoji":"💻","label":"Terminal"},
        "python":   {"color":"#102a10","border":"#31f755","emoji":"🐍","label":"Python"},
        "condition":{"color":"#2a0e0e","border":"#f04452","emoji":"🔀","label":"Condition"},
        "notify":   {"color":"#0e0e2a","border":"#9d7ff5","emoji":"🔔","label":"Notify"},
    }

    def __init__(self, node_type, x=0, y=0, config=None):
        super().__init__(0, 0, NODE_W, NODE_H)
        self.node_type = node_type
        self.config = config or {}
        self._edges_out: list = []
        self._edges_in:  list = []
        info = self.TYPES.get(node_type, self.TYPES["terminal"])
        self.setBrush(QBrush(QColor(info["color"])))
        pen = QPen(QColor(info["border"]), 1.5)
        self.setPen(pen)
        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setPos(x, y)
        self.setZValue(1)
        # Title
        title = QGraphicsTextItem(f"{info['emoji']} {info['label']}", self)
        title.setDefaultTextColor(QColor(THEME["text"]))
        title.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        title.setPos(8, 6)
        # Config summary
        self._cfg_item = QGraphicsTextItem("(click to configure)", self)
        self._cfg_item.setDefaultTextColor(QColor(THEME["text2"]))
        self._cfg_item.setFont(QFont("Consolas", 8))
        self._cfg_item.setPos(8, 32)
        self._cfg_item.setTextWidth(NODE_W - 16)
        # Ports
        r = 8
        self._in_port  = QGraphicsEllipseItem(-r//2, NODE_H//2-r//2, r, r, self)
        self._in_port.setBrush(QBrush(QColor(THEME["success"]))); self._in_port.setPen(QPen(Qt.PenStyle.NoPen))
        self._out_port = QGraphicsEllipseItem(NODE_W-r//2, NODE_H//2-r//2, r, r, self)
        self._out_port.setBrush(QBrush(QColor(THEME["accent2"]))); self._out_port.setPen(QPen(Qt.PenStyle.NoPen))
        self.update_config_display()

    def update_config_display(self):
        if self.config:
            vals = list(self.config.values())
            s = str(vals[0])[:30] + ("…" if len(str(vals[0])) > 30 else "")
            self._cfg_item.setPlainText(s)
        else:
            self._cfg_item.setPlainText("(click to configure)")

    def in_port_scene_pos(self):
        return self.scenePos() + QPointF(0, NODE_H / 2)

    def out_port_scene_pos(self):
        return self.scenePos() + QPointF(NODE_W, NODE_H / 2)

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            for e in self._edges_out + self._edges_in:
                if hasattr(e, "update_path"): e.update_path()
        return super().itemChange(change, value)

    def set_highlight(self, active: bool, paused: bool = False):
        pen = self.pen()
        if paused:
            pen.setWidth(3); pen.setColor(QColor("#f1c40f")) # Yellow for paused debugging
        elif active:
            pen.setWidth(3); pen.setColor(QColor(THEME["accent2"]))
        else:
            info = self.TYPES.get(self.node_type, self.TYPES["terminal"])
            pen.setWidth(1); pen.setColor(QColor(info["border"]))
        self.setPen(pen)

    def to_dict(self):
        return {"type":self.node_type, "x":self.pos().x(), "y":self.pos().y(), "config":self.config}

class FlowEdge(QGraphicsPathItem):
    def __init__(self, src: FlowNode, dst: FlowNode):
        super().__init__()
        self.src = src; self.dst = dst
        src._edges_out.append(self); dst._edges_in.append(self)
        pen = QPen(QColor(THEME["accent"]), 2)
        pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen); self.setZValue(0)
        self.update_path()

    def update_path(self):
        s = self.src.out_port_scene_pos()
        d = self.dst.in_port_scene_pos()
        path = QPainterPath(s)
        mx = (s.x() + d.x()) / 2
        path.cubicTo(QPointF(mx, s.y()), QPointF(mx, d.y()), d)
        self.setPath(path)

    def remove(self):
        if self in self.src._edges_out: self.src._edges_out.remove(self)
        if self in self.dst._edges_in:  self.dst._edges_in.remove(self)
        sc = self.scene()
        if sc: sc.removeItem(self)

class NodeCanvas(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self._nodes: List[FlowNode] = []
        self._pending_src: Optional[FlowNode] = None
        self._temp_edge: Optional[QGraphicsLineItem] = None

    def add_node(self, node_type, x=50, y=50):
        node = FlowNode(node_type, x, y)
        self.addItem(node)
        self._nodes.append(node)
        return node

    def connect_nodes(self, src: FlowNode, dst: FlowNode):
        edge = FlowEdge(src, dst)
        self.addItem(edge)

    def mouseDoubleClickEvent(self, event):
        items = self.items(event.scenePos())
        for item in items:
            if isinstance(item, FlowNode):
                self._configure_node(item); return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        pos = event.scenePos()
        items = self.items(pos)
        for item in items:
            if isinstance(item, QGraphicsEllipseItem) and isinstance(item.parentItem(), FlowNode):
                node = item.parentItem()
                if item == node._out_port:
                    self._pending_src = node
                    self._temp_edge = QGraphicsLineItem(QLineF(node.out_port_scene_pos(), pos))
                    pen = QPen(QColor(THEME["accent2"]), 2, Qt.PenStyle.DashLine)
                    self._temp_edge.setPen(pen)
                    self.addItem(self._temp_edge)
                    return
        clicked_node = None
        for item in items:
            if isinstance(item, FlowNode):
                clicked_node = item; break
        if event.button() == Qt.MouseButton.RightButton and clicked_node:
            self._show_node_context_menu(clicked_node, event.screenPos())
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._temp_edge:
            line = self._temp_edge.line()
            line.setP2(event.scenePos())
            self._temp_edge.setLine(line)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._temp_edge:
            pos = event.scenePos()
            items = self.items(pos)
            dst_node = None
            for item in items:
                if isinstance(item, QGraphicsEllipseItem) and isinstance(item.parentItem(), FlowNode):
                    node = item.parentItem()
                    if item == node._in_port and node != self._pending_src:
                        dst_node = node; break
                elif isinstance(item, FlowNode):
                    if item != self._pending_src:
                        dst_node = item; break
            if dst_node:
                exists = any(e.src == self._pending_src and e.dst == dst_node for e in self._pending_src._edges_out)
                if not exists:
                    self.connect_nodes(self._pending_src, dst_node)
            self.removeItem(self._temp_edge)
            self._temp_edge = None
            self._pending_src = None
            return
        super().mouseReleaseEvent(event)

    def _show_node_context_menu(self, node: FlowNode, screen_pos):
        menu = QMenu()
        menu.setStyleSheet(STYLESHEET)
        act_cfg = menu.addAction("⚙ Configure")
        act_del = menu.addAction("🗑 Delete")
        action = menu.exec(screen_pos.toPoint())
        if action == act_cfg: self._configure_node(node)
        elif action == act_del:
            for e in node._edges_out[:] + node._edges_in[:]: e.remove()
            self._nodes.remove(node); self.removeItem(node)

    def _configure_node(self, node: FlowNode):
        dialog = NodeConfigDialog(node)
        if dialog.exec():
            node.config = dialog.get_config()
            node.update_config_display()

    def delete_selected(self):
        for item in self.selectedItems():
            if isinstance(item, FlowNode):
                for e in item._edges_out[:]+item._edges_in[:]: e.remove()
                self._nodes.remove(item); self.removeItem(item)
            elif isinstance(item, FlowEdge):
                item.remove()

    def to_dict(self):
        idx = {n:i for i,n in enumerate(self._nodes)}
        edges = []
        for n in self._nodes:
            for e in n._edges_out:
                edges.append({"from":idx[e.src],"to":idx[e.dst]})
        return {"nodes":[n.to_dict() for n in self._nodes], "edges":edges}

    def from_dict(self, data):
        self.clear(); self._nodes = []
        for nd in data.get("nodes",[]):
            self.add_node(nd["type"], nd.get("x",50), nd.get("y",50))
            self._nodes[-1].config = nd.get("config",{})
            self._nodes[-1].update_config_display()
        for ed in data.get("edges",[]):
            src = self._nodes[ed["from"]]; dst = self._nodes[ed["to"]]
            self.connect_nodes(src, dst)

class NodeConfigDialog(QDialog):
    def __init__(self, node: FlowNode, parent=None):
        super().__init__(parent)
        self.node = node
        self.setWindowTitle(f"Configure {node.node_type.capitalize()} Node")
        self.setMinimumWidth(400)
        self.setStyleSheet(STYLESHEET)
        
        self.fields = {}
        self._build_ui()
        
    def _build_ui(self):
        lay = QVBoxLayout(self)
        form = QFormLayout()
        
        # Define fields and types for each node
        schemas = {
            "trigger":  [("type", "combo", ["manual", "interval", "file"]), ("interval_sec", "line", "30"), ("watch_path", "line", "")],
            "ai":       [("model", "line", ""), ("prompt", "text", "")],
            "git":      [("cmd", "line", "git pull"), ("repo", "line", ".")],
            "terminal": [("cmd", "text", ""), ("cwd", "line", "."), ("timeout", "line", "60")],
            "python":   [("script", "text", "print('Hello World')")],
            "condition":[("pattern", "line", ""), ("on_true", "combo", ["continue", "stop"]), ("on_false", "combo", ["stop", "continue"])],
            "notify":   [("message", "line", ""), ("level", "combo", ["info", "success", "warn", "error"])],
        }
        
        schema = schemas.get(self.node.node_type, [])
        for key, ftype, default in schema:
            cur_val = self.node.config.get(key, default)
            if ftype == "line":
                w = QLineEdit(str(cur_val))
            elif ftype == "text":
                w = QTextEdit()
                w.setPlainText(str(cur_val))
                w.setMinimumHeight(100)
            elif ftype == "combo":
                w = QComboBox()
                w.addItems(default)
                if cur_val in default: w.setCurrentText(cur_val)
                elif cur_val: w.addItem(str(cur_val)); w.setCurrentText(str(cur_val))
            
            self.fields[key] = (w, ftype)
            form.addRow(f"{key}:", w)
            
            # Special button for AI prompts
            if self.node.node_type == "ai" and key == "prompt":
                btn_load = QPushButton("Load Template")
                btn_load.clicked.connect(lambda _, w=w: self._load_prompt_template(w))
                form.addRow("", btn_load)
                
        lay.addLayout(form)
        
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_ok = QPushButton("Save"); btn_ok.clicked.connect(self.accept); btn_ok.setObjectName("primary")
        btn_cancel = QPushButton("Cancel"); btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel); btn_box.addWidget(btn_ok)
        lay.addLayout(btn_box)

    def _load_prompt_template(self, text_edit):
        try:
            import json
            from pathlib import Path
            prompts_file = Path.home() / ".nexus_prompts.json"
            if prompts_file.exists():
                prompts = json.loads(prompts_file.read_text())
                names = [p["name"] for p in prompts]
                if not names: return
                val, ok = QInputDialog.getItem(self, "Select Prompt", "Template:", names, 0, False)
                if ok and val:
                    tpl = next(p for p in prompts if p["name"] == val)
                    text_edit.setPlainText(tpl.get("template", ""))
        except Exception as e:
            pass
            
    def get_config(self):
        cfg = {}
        for k, (w, ftype) in self.fields.items():
            if ftype == "line": cfg[k] = w.text()
            elif ftype == "text": cfg[k] = w.toPlainText()
            elif ftype == "combo": cfg[k] = w.currentText()
        return cfg

class WorkflowPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def activate(self): pass
    def deactivate(self): pass

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(16,16,16,16); root.setSpacing(10)
        hdr = QHBoxLayout()
        t = QLabel("Automation Flows")
        t.setStyleSheet(f"font-size:18px;font-weight:bold;color:{THEME['text']};")
        hdr.addWidget(t); hdr.addStretch()
        root.addLayout(hdr)

        desc = QLabel("Visual node-based automation. Right-click nodes to connect them. Double-click to configure.")
        desc.setStyleSheet(f"color:{THEME['text2']};font-size:12px;")
        root.addWidget(desc)

        tb = QHBoxLayout()
        node_types = [("🔵 Trigger","trigger"),("🤖 AI","ai"),("🐍 Python","python"),("📁 Git","git"),
                      ("💻 Terminal","terminal"),("🔀 Condition","condition"),("🔔 Notify","notify")]
        for label, nt in node_types:
            b = QPushButton(label); b.setMaximumHeight(28)
            b.setStyleSheet("font-size:11px;padding:2px 8px;")
            b.clicked.connect(lambda _, t=nt: self._add_node(t))
            tb.addWidget(b)
        tb.addStretch()
        
        self.debug_mode_chk = QCheckBox("⏸ Debug Mode")
        self.debug_mode_chk.setStyleSheet(f"color:{THEME['text']}; font-size:11px; margin-right: 8px;")
        tb.addWidget(self.debug_mode_chk)
        
        self.btn_step = QPushButton("⏭ Step Next")
        self.btn_step.setEnabled(False)
        self.btn_step.clicked.connect(self._step_flow)
        tb.addWidget(self.btn_step)

        btn_del = QPushButton("🗑 Delete"); btn_del.setObjectName("danger")
        btn_del.clicked.connect(lambda: self.canvas.delete_selected())
        btn_clear = QPushButton("Clear All"); btn_clear.clicked.connect(self._clear_all)
        btn_save  = QPushButton("💾 Save"); btn_save.clicked.connect(self._save_flow)
        btn_load  = QPushButton("📂 Load"); btn_load.clicked.connect(self._load_flow)
        self.btn_run = QPushButton("▶ Run Flow"); self.btn_run.setObjectName("success")
        self.btn_run.clicked.connect(self._run_flow)
        for b in [btn_del, btn_clear, btn_save, btn_load, self.btn_run]:
            tb.addWidget(b)
        root.addLayout(tb)

        tpl_row = QHBoxLayout()
        tpl_row.addWidget(QLabel("Templates:"))
        templates = [("Auto-Commit","auto_commit"),("AI Code Review","ai_review"),("Git+Notify","git_notify")]
        for name, tpl in templates:
            b = QPushButton(name); b.setMaximumHeight(24)
            b.setStyleSheet(f"font-size:10px;padding:1px 6px;color:{THEME['accent2']};")
            b.clicked.connect(lambda _, t=tpl: self._load_template(t))
            tpl_row.addWidget(b)
        tpl_row.addStretch()
        root.addLayout(tpl_row)

        split = QSplitter(Qt.Orientation.Vertical)
        self.canvas = NodeCanvas()
        self.canvas.setSceneRect(-50,-50,2000,1000)
        self.view = QGraphicsView(self.canvas)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.view.setMinimumHeight(300)
        split.addWidget(self.view)

        # Bottom Splitter: Logs (left) & Context Variables (right)
        split_bottom = QSplitter(Qt.Orientation.Horizontal)
        self.log = LogView()
        split_bottom.addWidget(self.log)
        
        self.context_table = QTableWidget(0, 2)
        self.context_table.setHorizontalHeaderLabels(["Variable Name", "Value"])
        self.context_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.context_table.setStyleSheet(f"background: {THEME['bg2']}; color: {THEME['text']}; border: 1px solid {THEME['border']}; border-radius: 4px;")
        self.context_table.itemChanged.connect(self._on_context_cell_changed)
        split_bottom.addWidget(self.context_table)
        split_bottom.setSizes([450, 250])
        
        split_bottom.setMaximumHeight(180)
        split.addWidget(split_bottom); split.setSizes([400, 180])
        root.addWidget(split, 1)

    def _add_node(self, node_type):
        cx = self.view.viewport().width()//2
        cy = self.view.viewport().height()//2
        sp = self.view.mapToScene(cx, cy)
        self.canvas.add_node(node_type, sp.x()-NODE_W//2, sp.y()-NODE_H//2)

    def _clear_all(self):
        self.canvas.clear(); self.canvas._nodes = []

    def _save_flow(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Flow", str(Path.home()), "JSON (*.json)")
        if path:
            Path(path).write_text(json.dumps(self.canvas.to_dict(), indent=2))

    def _load_flow(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Flow", str(Path.home()), "JSON (*.json)")
        if path:
            data = json.loads(Path(path).read_text())
            self.canvas.from_dict(data)

    def _run_flow(self):
        data = self.canvas.to_dict()
        if not data["nodes"]: return
        self.context_table.setRowCount(0)
        self.btn_run.setEnabled(False)
        
        step_mode = self.debug_mode_chk.isChecked()
        self._worker = WorkflowWorker(data, host=SETTINGS.get("ollama_host"), step_mode=step_mode)
        self._worker.step_info.connect(self.log.append_line)
        self._worker.highlight.connect(self._highlight_node)
        self._worker.paused.connect(self._on_flow_paused)
        self._worker.context_updated.connect(self._on_context_updated)
        
        def on_finished():
            self.log.append_line("Workflow complete", "success")
            self.btn_run.setEnabled(True)
            self.btn_step.setEnabled(False)
            self._clear_all_paused_highlights()
            
        self._worker.finished.connect(on_finished)
        self._worker.start()

    def _highlight_node(self, idx, active):
        if 0 <= idx < len(self.canvas._nodes):
            self.canvas._nodes[idx].set_highlight(active)

    def _on_flow_paused(self, node_idx):
        self.log.append_line(f"Paused. Click 'Step Next' to run this node.", "warn")
        if 0 <= node_idx < len(self.canvas._nodes):
            self.canvas._nodes[node_idx].set_highlight(False, paused=True)
        self.btn_step.setEnabled(True)

    def _step_flow(self):
        self.btn_step.setEnabled(False)
        self._clear_all_paused_highlights()
        if self._worker:
            self._worker.step()

    def _clear_all_paused_highlights(self):
        for node in self.canvas._nodes:
            # Revert yellow border to default
            node.set_highlight(False, paused=False)

    def _on_context_updated(self, context_dict):
        self.context_table.blockSignals(True)
        self.context_table.setRowCount(0)
        for k, v in context_dict.items():
            row = self.context_table.rowCount()
            self.context_table.insertRow(row)
            
            key_item = QTableWidgetItem(str(k))
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable) # Read-only key
            self.context_table.setItem(row, 0, key_item)
            
            val_item = QTableWidgetItem(str(v))
            self.context_table.setItem(row, 1, val_item)
        self.context_table.blockSignals(False)

    def _on_context_cell_changed(self, item):
        if not hasattr(self, "_worker") or not self._worker or not self._worker.isRunning():
            return
        row = item.row()
        key_item = self.context_table.item(row, 0)
        val_item = self.context_table.item(row, 1)
        if key_item and val_item:
            key = key_item.text()
            val = val_item.text()
            self._worker.engine.context[key] = val
            self.log.append_line(f"Runtime variable '{key}' modified to: '{val}'", "info")

    def _load_template(self, tpl):
        templates = {
            "auto_commit": {"nodes":[
                {"type":"trigger","x":50,"y":200,"config":{"type":"manual"}},
                {"type":"git","x":280,"y":200,"config":{"cmd":"git add -A","repo":"."}},
                {"type":"git","x":510,"y":200,"config":{"cmd":"git commit -m 'auto: update'","repo":"."}},
                {"type":"git","x":740,"y":200,"config":{"cmd":"git push","repo":"."}},
                {"type":"notify","x":970,"y":200,"config":{"message":"Push complete!","level":"success"}},
            ],"edges":[{"from":0,"to":1},{"from":1,"to":2},{"from":2,"to":3},{"from":3,"to":4}]},
            "ai_review": {"nodes":[
                {"type":"trigger","x":50,"y":200,"config":{"type":"manual"}},
                {"type":"terminal","x":280,"y":200,"config":{"cmd":"git diff HEAD~1","cwd":"."}},
                {"type":"ai","x":510,"y":200,"config":{"model":"","prompt":"Review this code diff and identify issues:"}},
                {"type":"notify","x":740,"y":200,"config":{"message":"Review complete","level":"info"}},
            ],"edges":[{"from":0,"to":1},{"from":1,"to":2},{"from":2,"to":3}]},
            "git_notify": {"nodes":[
                {"type":"trigger","x":50,"y":200,"config":{"type":"manual"}},
                {"type":"git","x":280,"y":200,"config":{"cmd":"git pull","repo":"."}},
                {"type":"notify","x":510,"y":200,"config":{"message":"Pull done!","level":"success"}},
            ],"edges":[{"from":0,"to":1},{"from":1,"to":2}]},
        }
        if tpl in templates:
            self.canvas.from_dict(templates[tpl])
