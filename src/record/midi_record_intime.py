#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIDI实时钢琴键盘监听程序
功能：接收MIDI设备输入，实时显示当前正在弹的琴键
"""

import mido
from mido import Message
import time
from datetime import datetime
import threading
import queue


class MidiPianoRecorder:
    """MIDI钢琴记录器"""
    
    # MIDI音符号到音符名称的映射（C4 = 中央C = MIDI 60）
    NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    def __init__(self):
        self.active_notes = {}  # 当前正在按下的音符 {note_number: velocity}
        self.port = None
        self.recorded_events = []  # 记录所有MIDI事件
        self.start_time = None  # 录制开始时间

        self.message_queue = queue.Queue(maxsize=100)
        
    def put_message(self, message):
        self.message_queue.put(message)
        
    def get_message(self):
        return self.message_queue.get()

    def get_note_name(self, note_number):
        """将MIDI音符号转换为音符名称（如C4, D#5等）"""
        octave = (note_number // 12) - 1
        note = self.NOTE_NAMES[note_number % 12]
        return f"{note}{octave}"
    
    def list_midi_devices(self):
        """列出所有可用的MIDI输入设备"""
        print("=" * 60)
        print("可用的MIDI输入设备：")
        print("=" * 60)
        input_names = mido.get_input_names()
        
        if not input_names:
            print("未找到任何MIDI输入设备！")
            print("请确保：")
            print("1. MIDI设备已正确连接到电脑")
            print("2. 设备驱动已正确安装")
            return None
        
        for i, name in enumerate(input_names):
            print(f"{i}: {name}")
        print("=" * 60)
        return input_names
    
    def select_device(self, device_index=None):
        """选择MIDI输入设备"""
        input_names = self.list_midi_devices()
        
        if not input_names:
            return False
        
        # 如果没有指定设备索引，使用第一个设备
        if device_index is None:
            if len(input_names) == 1:
                device_index = 0
                print(f"\n自动选择设备: {input_names[0]}")
            else:
                try:
                    device_index = int(input(f"\n请选择设备编号 (0-{len(input_names)-1}): "))
                except ValueError:
                    print("无效输入，使用第一个设备")
                    device_index = 0
        
        if 0 <= device_index < len(input_names):
            try:
                self.port = mido.open_input(input_names[device_index])
                print(f"\n✓ 已连接到: {input_names[device_index]}")
                return True
            except Exception as e:
                print(f"✗ 连接设备失败: {e}")
                return False
        else:
            print(f"✗ 无效的设备编号: {device_index}")
            return False
    
    def process_message(self, msg):
        """处理单个MIDI消息"""
        current_time = time.time()
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # 记录事件（用于后续保存为MIDI文件）
        if self.start_time is not None:
            relative_time = current_time - self.start_time
            self.recorded_events.append({
                'time': relative_time,
                'message': msg.copy()
            })
        
        if msg.type == 'note_on' and msg.velocity > 0:
            # 音符按下
            self.active_notes[msg.note] = msg.velocity
            note_name = self.get_note_name(msg.note)
            print(f"[{timestamp}] 🎹 按下: {note_name} (MIDI:{msg.note}) 力度:{msg.velocity}")
            self.put_message(msg)
            self.display_active_notes()
            
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            # 音符释放
            if msg.note in self.active_notes:
                del self.active_notes[msg.note]
                note_name = self.get_note_name(msg.note)
                print(f"[{timestamp}] 🎵 释放: {note_name} (MIDI:{msg.note})")
                self.put_message(msg)
                self.display_active_notes()
        
        elif msg.type == 'control_change':
            # 控制变化（如踏板、调制轮等）
            print(f"[{timestamp}] 🎛️  控制: CC{msg.control} = {msg.value}")
            self.put_message(msg)
        elif msg.type == 'pitchwheel':
            # 弯音轮
            print(f"[{timestamp}] 🎚️  弯音: {msg.pitch}")
            self.put_message(msg)
    
    def display_active_notes(self):
        """显示当前所有正在按下的音符"""
        if self.active_notes:
            notes_info = []
            for note, velocity in sorted(self.active_notes.items()):
                note_name = self.get_note_name(note)
                notes_info.append(f"{note_name}(v:{velocity})")
            print(f"   ► 当前按下的琴键: {', '.join(notes_info)}")
        else:
            print(f"   ► 当前按下的琴键: 无")
        print()
    
    def save_to_midi(self, filename=None):
        """将录制的演奏保存为MIDI文件"""
        if not self.recorded_events:
            print("⚠ 没有录制数据，无法保存")
            return False
        
        # 如果没有指定文件名，使用时间戳生成
        if filename is None:
            filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.midi"
        
        # 确保文件名以.midi结尾
        if not filename.endswith('.midi'):
            filename += '.midi'
        
        try:
            # 创建MIDI文件
            mid = mido.MidiFile()
            track = mido.MidiTrack()
            mid.tracks.append(track)
            
            # 添加音轨名称
            track.append(mido.MetaMessage('track_name', name='Piano Recording', time=0))
            
            # 设置速度 (120 BPM)
            track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(120), time=0))
            
            # 转换录制的事件为MIDI消息
            last_time = 0
            for event in self.recorded_events:
                # 计算delta时间（以ticks为单位）
                # mido使用ticks，我们需要将秒转换为ticks
                # 默认：480 ticks per beat，120 BPM = 2 beats/sec = 960 ticks/sec
                delta_seconds = event['time'] - last_time
                delta_ticks = int(delta_seconds * 960)  # 960 ticks/second at 120 BPM
                
                # 复制消息并设置时间
                msg = event['message'].copy()
                msg.time = delta_ticks
                track.append(msg)
                
                last_time = event['time']
            
            # 添加结束标记
            track.append(mido.MetaMessage('end_of_track', time=0))
            
            # 保存文件
            mid.save(filename)
            print(f"\n✓ 录制已保存到: {filename}")
            print(f"  - 总事件数: {len(self.recorded_events)}")
            print(f"  - 录制时长: {self.recorded_events[-1]['time']:.2f} 秒")
            return True
            
        except Exception as e:
            print(f"\n✗ 保存MIDI文件失败: {e}")
            return False
    
    def start_recording(self):
        """开始监听MIDI输入"""
        if not self.port:
            print("✗ 错误: 未连接到MIDI设备")
            return
        
        print("\n" + "=" * 60)
        print("开始监听MIDI输入...")
        print("🔴 正在录制，所有演奏将被保存")
        print("按 Ctrl+C 停止录制")
        print("=" * 60)
        print()
        
        # 记录开始时间
        self.start_time = time.time()
        
        try:
            for msg in self.port:
                self.process_message(msg)
        except KeyboardInterrupt:
            print("\n\n" + "=" * 60)
            print("停止录制")
            print("=" * 60)
            
            # 询问是否保存
            if self.recorded_events:
                print(f"\n录制了 {len(self.recorded_events)} 个MIDI事件")
                
                try:
                    save_choice = input("是否保存为MIDI文件？(Y/n): ").strip().lower()
                    
                    if save_choice == '' or save_choice == 'y' or save_choice == 'yes':
                        # 询问文件名
                        custom_filename = input("请输入文件名（直接回车使用默认名称）: ").strip()
                        
                        if custom_filename:
                            self.save_to_midi(custom_filename)
                        else:
                            self.save_to_midi()
                    else:
                        print("\n录制未保存")
                except Exception as e:
                    print(f"\n输入错误，自动保存: {e}")
                    self.save_to_midi()
            else:
                print("\n没有录制到任何数据")
        finally:
            if self.port:
                self.port.close()
                print("\nMIDI端口已关闭")


def main():
    """主函数"""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║          MIDI实时钢琴键盘监听程序                          ║
    ║          Real-time MIDI Piano Key Monitor                ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    recorder = MidiPianoRecorder()
    
    # 选择并连接MIDI设备
    if recorder.select_device():
        # 开始监听
        recorder.start_recording()
    else:
        print("\n程序退出")


if __name__ == "__main__":
    main()

