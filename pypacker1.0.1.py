"""
Python 脚本打包工具 - PyPacker Lite
支持拖入py文件自动打包为可执行程序
使用 PySide6 构建简约界面
"""

import sys
import os
import subprocess
import shutil
import threading
from pathlib import Path

# PySide6 导入
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                               QCheckBox, QProgressBar, QTextEdit, QFileDialog,
                               QMessageBox, QGroupBox, QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QFont, QPixmap, QTextCursor, QCursor


class BuildThread(QThread):
    """打包线程，在后台执行打包操作"""
    
    log_signal = Signal(str)
    finished_signal = Signal(bool)
    
    def __init__(self, script_path, output_folder, onefile=True, noconsole=False, icon_path=None):
        super().__init__()
        self.script_path = script_path
        self.output_folder = output_folder
        self.onefile = onefile
        self.noconsole = noconsole
        self.icon_path = icon_path
    
    def run(self):
        """执行打包命令"""
        script_dir = os.path.dirname(os.path.abspath(self.script_path))
        
        # 构建命令
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--distpath', self.output_folder,
            '--noconfirm',
        ]
        
        # 添加选项
        if self.onefile:
            cmd.append('-F')
        else:
            cmd.append('-D')
        
        if self.noconsole:
            cmd.append('-w')
        
        # 添加图标
        if self.icon_path and os.path.exists(self.icon_path):
            cmd.extend(['--icon', self.icon_path])
        
        # 添加脚本路径
        cmd.append(self.script_path)
        
        self.log_signal.emit(f"执行命令: {' '.join(cmd)}")
        self.log_signal.emit("-" * 50)
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=script_dir
            )
            
            # 实时读取输出
            for line in process.stdout:
                self.log_signal.emit(line.rstrip())
            
            process.wait()
            
            if process.returncode == 0:
                self.log_signal.emit("-" * 50)
                self.log_signal.emit("打包成功!")
                self.finished_signal.emit(True)
            else:
                self.log_signal.emit("-" * 50)
                self.log_signal.emit("打包失败")
                self.finished_signal.emit(False)
                
        except Exception as e:
            self.log_signal.emit(f"执行异常: {str(e)}")
            self.finished_signal.emit(False)


class PyPackerWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python Packer")
        self.setFixedSize(480, 520)
        
        # 检查依赖
        self.pyinstaller_available = self._check_pyinstaller()
        self.current_script = None
        self.build_thread = None
        
        # 设置主界面
        self.setup_ui()
        
        # 处理命令行参数
        self._handle_args()
    
    def _check_pyinstaller(self):
        """检查pyinstaller是否可用"""
        try:
            import PyInstaller
            return True
        except ImportError:
            pass
        
        return shutil.which('pyinstaller') is not None
    
    def setup_ui(self):
        """设置界面"""
        # 主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("Python Packer")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 状态提示
        if not self.pyinstaller_available:
            status_tip = QLabel("PyInstaller 未安装")
            status_tip.setAlignment(Qt.AlignCenter)
            status_tip.setStyleSheet("color: #999; font-size: 11px;")
            main_layout.addWidget(status_tip)
        
        # ========== 拖放区域 ==========
        self.setAcceptDrops(True)
        
        self.drop_label = QLabel()
        self.drop_label.setFixedSize(400, 60)
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setText("拖入 .py 文件 或 点击选择")
        self.drop_label.setStyleSheet("""
            QLabel {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #fff;
                color: #666;
                font-size: 12px;
            }
        """)
        
        # 只在拖放区域响应点击事件
        self.drop_label.mousePressEvent = self.on_drop_label_click
        
        main_layout.addWidget(self.drop_label, alignment=Qt.AlignHCenter)
        
        # 文件路径输入框
        path_layout = QHBoxLayout()
        path_layout.setSpacing(8)
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("文件路径...")
        self.path_edit.setReadOnly(True)
        self.path_edit.setStyleSheet("""
            QLineEdit {
                padding: 6px 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 11px;
            }
        """)
        
        browse_btn = QPushButton("浏览")
        browse_btn.setFixedWidth(60)
        browse_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f5f5f5;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #e5e5e5;
            }
        """)
        browse_btn.clicked.connect(self.browse_file)
        
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(browse_btn)
        main_layout.addLayout(path_layout)
        
        # ========== 选项区域 ==========
        options_group = QGroupBox("选项")
        options_group.setStyleSheet("""
            QGroupBox {
                font-size: 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(6)
        
        self.onefile_check = QCheckBox("单文件模式 (-F)")
        self.onefile_check.setChecked(True)
        self.onefile_check.setStyleSheet("font-size: 12px;")
        
        self.noconsole_check = QCheckBox("无控制台 (-w)")
        self.noconsole_check.setStyleSheet("font-size: 12px;")
        
        options_layout.addWidget(self.onefile_check)
        options_layout.addWidget(self.noconsole_check)
        
        # 图标选择
        icon_layout = QHBoxLayout()
        icon_layout.setSpacing(6)
        
        icon_layout.addWidget(QLabel("图标:"))
        
        self.icon_edit = QLineEdit()
        self.icon_edit.setPlaceholderText("可选")
        self.icon_edit.setReadOnly(True)
        self.icon_edit.setStyleSheet("font-size: 11px;")
        
        icon_btn = QPushButton("...")
        icon_btn.setFixedWidth(30)
        icon_btn.setStyleSheet("""
            QPushButton {
                padding: 4px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #f5f5f5;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #e5e5e5;
            }
        """)
        icon_btn.clicked.connect(self.browse_icon)
        
        icon_layout.addWidget(self.icon_edit)
        icon_layout.addWidget(icon_btn)
        icon_layout.addStretch()
        
        options_layout.addLayout(icon_layout)
        
        main_layout.addWidget(options_group)
        
        # ========== 打包按钮 ==========
        self.pack_btn = QPushButton("开始打包")
        self.pack_btn.setFixedHeight(40)
        self.pack_btn.setEnabled(False)
        self.pack_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #999;
                border-radius: 4px;
                background-color: #f5f5f5;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e5e5e5;
            }
            QPushButton:disabled {
                color: #aaa;
            }
        """)
        self.pack_btn.clicked.connect(self.start_pack)
        main_layout.addWidget(self.pack_btn)
        
        # 安装按钮（如果未安装pyinstaller）
        if not self.pyinstaller_available:
            self.install_btn = QPushButton("安装 PyInstaller")
            self.install_btn.setFixedHeight(35)
            self.install_btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #999;
                    border-radius: 4px;
                    background-color: #f5f5f5;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #e5e5e5;
                }
            """)
            self.install_btn.clicked.connect(self.install_pyinstaller)
            main_layout.addWidget(self.install_btn)
        
        # ========== 日志区域 ==========
        log_group = QGroupBox("日志")
        log_group.setStyleSheet("""
            QGroupBox {
                font-size: 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(140)
        self.log_text.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, monospace;
                font-size: 10px;
                background-color: #fafafa;
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 4px;
            }
        """)
        
        log_layout.addWidget(self.log_text)
        main_layout.addWidget(log_group)
        
        # ========== 进度条 ==========
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #eee;
            }
            QProgressBar::chunk {
                background-color: #999;
            }
        """)
        main_layout.addWidget(self.progress)
    
    def _handle_args(self):
        """处理命令行参数"""
        if len(sys.argv) > 1:
            script_path = sys.argv[1]
            script_path = script_path.strip('"').strip("'")
            
            if script_path.endswith('.py') and os.path.exists(script_path):
                self.path_edit.setText(script_path)
                self.current_script = script_path
                self.pack_btn.setEnabled(True)
                self.start_pack()
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_label.setStyleSheet("""
                QLabel {
                    border: 1px solid #666;
                    border-radius: 4px;
                    background-color: #f0f0f0;
                    color: #333;
                    font-size: 12px;
                }
            """)
    
    def dragLeaveEvent(self, event):
        """拖出事件"""
        self.drop_label.setStyleSheet("""
            QLabel {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #fff;
                color: #666;
                font-size: 12px;
            }
        """)
    
    def dropEvent(self, event: QDropEvent):
        """放下事件"""
        self.drop_label.setStyleSheet("""
            QLabel {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #fff;
                color: #666;
                font-size: 12px;
            }
        """)
        
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.endswith('.py'):
                    self.on_file_dropped(file_path)
                    break
    
    def mousePressEvent(self, event):
        """点击事件"""
        # 不在这里处理，让子组件自行处理
        pass
    
    def on_drop_label_click(self, event):
        """拖放区域点击事件"""
        if event.button() == Qt.LeftButton:
            self.browse_file()
    
    def on_file_dropped(self, file_path):
        """文件选择事件"""
        if os.path.exists(file_path) or file_path.endswith('.py'):
            self.path_edit.setText(file_path)
            self.current_script = file_path
            self.pack_btn.setEnabled(True)
            self.log(f"已选择: {file_path}")
    
    def browse_file(self):
        """浏览选择文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择Python脚本",
            "",
            "Python脚本 (*.py);;所有文件 (*.*)"
        )
        
        if file_path:
            self.on_file_dropped(file_path)
    
    def browse_icon(self):
        """浏览选择图标"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图标",
            "",
            "图标文件 (*.ico);;所有文件 (*.*)"
        )
        
        if file_path:
            self.icon_edit.setText(file_path)
    
    def install_pyinstaller(self):
        """安装pyinstaller"""
        self.log("正在安装 PyInstaller...")
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.install_btn.setEnabled(False)
        
        def install_task():
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', 'pyinstaller'],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    self.pyinstaller_available = True
                    self.pack_btn.setEnabled(True)
                    self.log("安装成功!")
                    self.install_btn.hide()
                    QMessageBox.information(self, "完成", "PyInstaller 安装成功")
                else:
                    self.log(f"安装失败")
                    QMessageBox.critical(self, "错误", "安装失败")
                    self.install_btn.setEnabled(True)
            except Exception as e:
                self.log(f"安装异常: {str(e)}")
                QMessageBox.critical(self, "错误", str(e))
                self.install_btn.setEnabled(True)
            finally:
                self.progress.setRange(0, 100)
                self.progress.setVisible(False)
        
        threading.Thread(target=install_task, daemon=True).start()
    
    def start_pack(self):
        """开始打包"""
        if not self.current_script:
            QMessageBox.warning(self, "提示", "请先选择脚本")
            return
        
        if not self.pyinstaller_available:
            QMessageBox.warning(self, "提示", "请先安装 PyInstaller")
            return
        
        script_path = self.current_script
        
        if not os.path.exists(script_path):
            QMessageBox.critical(self, "错误", "文件不存在")
            return
        
        self.log_text.clear()
        script_dir = os.path.dirname(os.path.abspath(script_path))
        output_folder = os.path.join(script_dir, "输出")
        
        self.pack_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        
        self.build_thread = BuildThread(
            script_path=script_path,
            output_folder=output_folder,
            onefile=self.onefile_check.isChecked(),
            noconsole=self.noconsole_check.isChecked(),
            icon_path=self.icon_edit.text() or None
        )
        
        self.build_thread.log_signal.connect(self.log)
        self.build_thread.finished_signal.connect(self.on_pack_finished)
        
        self.build_thread.start()
    
    def on_pack_finished(self, success):
        """打包完成"""
        self.progress.setRange(0, 100)
        self.progress.setVisible(False)
        self.pack_btn.setEnabled(True)
        
        if success:
            output_path = os.path.join(
                os.path.dirname(os.path.abspath(self.current_script)),
                "输出"
            )
            
            if QMessageBox.question(
                self, "完成", "打包完成，是否打开输出目录？",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self.open_folder(output_path)
    
    def open_folder(self, path):
        """打开文件夹"""
        try:
            if sys.platform == 'win32':
                os.startfile(path)
            else:
                subprocess.run(['xdg-open', path])
        except Exception as e:
            self.log(f"无法打开: {str(e)}")
    
    def log(self, message):
        """添加日志"""
        self.log_text.append(message)
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("Python Packer")
    
    window = PyPackerWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
