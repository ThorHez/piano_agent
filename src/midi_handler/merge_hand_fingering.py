#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import argparse
import glob
from datetime import datetime
from notes_to_fingering import find_arm_positions_optimized, detect_hand_from_filename, parse_notes_from_file

def note_to_midi_number(note_name):
    """
    将音符名称转换为MIDI编号
    
    Args:
        note_name: 音符名称，如 'C4', 'F#5', 'Bb3'
    
    Returns:
        int: MIDI编号（C4=60, B2=47）
    """
    # 音名到半音偏移的映射
    note_offsets = {
        'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11
    }
    
    # 提取音符名和八度数
    if len(note_name) >= 2:
        if '#' in note_name:
            # 升号：如 'C#4'
            note_base = note_name[0]
            octave = int(note_name[-1])
            offset = note_offsets.get(note_base, 0) + 1  # 升号加1
        elif 'b' in note_name:
            # 降号：如 'Bb3'
            note_base = note_name[0]
            octave = int(note_name[-1])
            offset = note_offsets.get(note_base, 0) - 1  # 降号减1
        else:
            # 无升降号：如 'C4', 'F5'
            note_base = note_name[0]
            octave = int(note_name[-1])
            offset = note_offsets.get(note_base, 0)
    else:
        return 60  # 默认C4
    
    # 计算MIDI编号：C4=60
    midi_number = (octave + 1) * 12 + offset
    
    return midi_number

def transpose_note_up_octave(note_name):
    """
    将音符升高一个八度（+8度）
    
    Args:
        note_name: 音符名称，如 'C4', 'F#5', 'Bb3'
    
    Returns:
        str: 升高一个八度后的音符
    """
    # 提取音符名和八度数
    if len(note_name) >= 2:
        if '#' in note_name or 'b' in note_name:
            # 有升降号：如 'C#4', 'Bb3'
            note_base = note_name[:-1]  # 去掉最后的数字
            octave = int(note_name[-1])
        else:
            # 无升降号：如 'C4', 'F5'
            note_base = note_name[:-1]
            octave = int(note_name[-1])
    else:
        # 异常情况
        return note_name
    
    # 升高一个八度
    new_octave = octave + 1
    
    # 确保不超过钢琴范围（C8）
    if new_octave > 8:
        new_octave = 8
    
    return note_base + str(new_octave)

def transpose_note_to_range(note_name, target_low_midi=48, target_high_midi=59):
    """
    将音符升8度（或8度的倍数），直到升到目标范围内
    
    Args:
        note_name: 音符名称，如 'A0', 'B2', 'C1'
        target_low_midi: 目标范围下限（默认48=C3）
        target_high_midi: 目标范围上限（默认59=B3）
    
    Returns:
        tuple: (转换后的音符, 升高的八度数)
    
    示例：
        A0 (MIDI 21) → A3 (MIDI 57), 升高3个八度
        B2 (MIDI 47) → B3 (MIDI 59), 升高1个八度
        C3 (MIDI 48) → C3 (MIDI 48), 不变
    """
    # 计算当前音符的MIDI编号
    current_midi = note_to_midi_number(note_name)
    
    # 如果已在目标范围内，不转换
    if target_low_midi <= current_midi <= target_high_midi:
        return note_name, 0
    
    # 提取音符名和八度数
    if len(note_name) >= 2:
        if '#' in note_name or 'b' in note_name:
            note_base = note_name[:-1]
            octave = int(note_name[-1])
        else:
            note_base = note_name[:-1]
            octave = int(note_name[-1])
    else:
        return note_name, 0
    
    # 计算需要升高多少个八度
    octaves_up = 0
    while current_midi < target_low_midi:
        current_midi += 12  # 升一个八度
        octave += 1
        octaves_up += 1
        
        # 安全限制：最多升4个八度
        if octaves_up >= 4:
            break
    
    # 如果升高后超过目标范围上限，调整到上限
    if current_midi > target_high_midi:
        # 回退到目标范围内
        while current_midi > target_high_midi and octave > 0:
            current_midi -= 12
            octave -= 1
            octaves_up -= 1
    
    # 确保八度在合理范围内
    if octave < 0:
        octave = 0
    elif octave > 8:
        octave = 8
    
    return note_base + str(octave), octaves_up

def process_midi_to_fingering(midi_file, hand_type, output_dir, transpose_octave=False, 
                              filter_low_notes=False, low_note_threshold='B2',
                              transpose_low_to_range=False):
    """
    将MIDI文件转换为指法数据
    
    Args:
        midi_file: MIDI文件路径
        hand_type: 'left' 或 'right'
        output_dir: 输出目录
        transpose_octave: 是否升高一个八度（默认False）
        filter_low_notes: 是否过滤低音（默认False）
        low_note_threshold: 低音过滤阈值（默认'B2'，过滤<=B2的音符）
        transpose_low_to_range: 是否将低音升到C3~B3范围（默认False）
    
    Returns:
        tuple: (指法结果列表, 总移动距离, 移动次数, 原始音符数, 过滤掉的音符数)
    """
    # 使用midi_to_musical_notation.py解析MIDI文件
    from midi_to_musical_notation import midi_to_notes
    
    # 解析MIDI文件
    notes, control_events, timing_info = midi_to_notes(midi_file)
    
    # 计算过滤阈值的MIDI编号
    threshold_midi = note_to_midi_number(low_note_threshold) if filter_low_notes else 0
    
    # 提取音符名称和时间信息
    notes_list = []
    note_timing = []
    
    transposed_count = 0
    filtered_count = 0
    transposed_to_range_count = 0
    original_count = len(notes)
    
    for note in notes:
        note_name = note['note_name']
        original_name = note_name
        
        # ⭐ 如果启用了低音过滤，检查音符是否需要过滤
        if filter_low_notes:
            note_midi = note_to_midi_number(note_name)
            if note_midi <= threshold_midi:
                # 音符 <= 阈值，过滤掉
                filtered_count += 1
                continue  # 跳过此音符
        
        # ⭐ 如果启用了低音升到目标范围（B2及以下升到C3~B3）
        if transpose_low_to_range:
            note_midi = note_to_midi_number(note_name)
            if note_midi <= 47:  # B2及以下
                # 将音符升到C3~B3范围（MIDI 48~59）
                note_name, octaves_up = transpose_note_to_range(note_name, 48, 59)
                if octaves_up > 0:
                    transposed_to_range_count += 1
        
        # ⭐ 如果启用了升八度，转换音符
        if transpose_octave:
            note_name = transpose_note_up_octave(note_name)
            if note_name != original_name:
                transposed_count += 1
        
        notes_list.append(note_name)
        note_timing.append({
            'start_time': note['start_time_sec'],
            'duration': note['duration_sec'],
            'velocity': note['velocity']
        })
    
    # 显示转换统计
    if transpose_octave and transposed_count > 0:
        print(f"   ⭐ 音符升八度: {transposed_count}/{len(notes)} 个音符已升高8度")
    
    # 显示低音升到目标范围的统计
    if transpose_low_to_range and transposed_to_range_count > 0:
        print(f"   ⬆️  低音升高: {transposed_to_range_count}/{original_count} 个音符已升到C3~B3范围")
    
    # 显示过滤统计
    if filter_low_notes and filtered_count > 0:
        print(f"   🗑️  低音过滤: {filtered_count}/{original_count} 个音符已删除（<= {low_note_threshold}）")
    
    # 计算指法
    result, total_move, move_count = find_arm_positions_optimized(
        notes_list, 
        move_penalty=5.0, 
        note_timing=note_timing, 
        hand_type=hand_type
    )
    
    return result, total_move, move_count, notes_list, original_count, filtered_count

def save_separate_hand_fingerings(left_midi_file, right_midi_file, output_dir, song_name, 
                                  transpose_right_octave=False, filter_left_low_notes=False,
                                  transpose_left_low_to_range=False):
    """
    分别保存左右手指法数据（不合并）
    
    Args:
        left_midi_file: 左手MIDI文件路径
        right_midi_file: 右手MIDI文件路径
        output_dir: 输出目录
        song_name: 曲目名称
        transpose_right_octave: 是否将右手音符升高一个八度（默认False）
        filter_left_low_notes: 是否过滤左手B2及以下的低音（默认False）
        transpose_left_low_to_range: 是否将左手B2及以下的音符升到C3~B3范围（默认False）
    """
    print(f"正在处理曲目: {song_name}")
    print("=" * 60)
    
    if transpose_right_octave:
        print("⭐ 右手音符升八度: 已启用（所有右手音符将升高8度）")
    
    if filter_left_low_notes:
        print("⭐ 左手低音过滤: 已启用（将删除B2及以下的音符）")
    
    if transpose_left_low_to_range:
        print("⭐ 左手低音升高: 已启用（将B2及以下的音符升到C3~B3范围）")
    
    # 处理左手MIDI文件
    print("\n处理左手MIDI文件...")
    left_result, left_move, left_count, left_notes, left_original_count, left_filtered_count = process_midi_to_fingering(
        left_midi_file, 'left', output_dir, transpose_octave=False, 
        filter_low_notes=filter_left_low_notes, low_note_threshold='B2',
        transpose_low_to_range=transpose_left_low_to_range
    )
    
    if filter_left_low_notes and left_filtered_count > 0:
        print(f"左手: {len(left_result)}个音符（原始{left_original_count}个，已过滤{left_filtered_count}个）, 移动距离: {left_move:.2f}, 移动次数: {left_count}")
    else:
        print(f"左手: {len(left_result)}个音符, 移动距离: {left_move:.2f}, 移动次数: {left_count}")
    
    # 处理右手MIDI文件
    print("\n处理右手MIDI文件...")
    right_result, right_move, right_count, right_notes, right_original_count, right_filtered_count = process_midi_to_fingering(
        right_midi_file, 'right', output_dir, transpose_octave=transpose_right_octave,
        filter_low_notes=False  # 右手不过滤低音
    )
    
    if transpose_right_octave:
        print(f"右手: {len(right_result)}个音符（已升八度）, 移动距离: {right_move:.2f}, 移动次数: {right_count}")
    else:
        print(f"右手: {len(right_result)}个音符, 移动距离: {right_move:.2f}, 移动次数: {right_count}")
    
    # 统计小拇指键类型使用情况
    left_pinky_normal = sum(1 for r in left_result if r['finger'] == 5 and r.get('pinky_key_type', 'normal') == 'normal')
    left_pinky_extended = sum(1 for r in left_result if r['finger'] == 5 and r.get('pinky_key_type', 'normal') == 'extended')
    right_pinky_normal = sum(1 for r in right_result if r['finger'] == 5 and r.get('pinky_key_type', 'normal') == 'normal')
    right_pinky_extended = sum(1 for r in right_result if r['finger'] == 5 and r.get('pinky_key_type', 'normal') == 'extended')
    
    # ==================== 保存左手指法文件 ====================
    left_output_file = os.path.join(output_dir, f"{song_name}_left_hand_fingering.txt")
    
    with open(left_output_file, 'w', encoding='utf-8') as f:
        f.write(f"{song_name} - 左手指法分析结果\n")
        f.write("=" * 120 + "\n")
        f.write(f"左手音符数: {len(left_result)}\n")
        if filter_left_low_notes and left_filtered_count > 0:
            f.write(f"原始音符数: {left_original_count}\n")
            f.write(f"🗑️  已过滤低音: {left_filtered_count}个（<= B2）\n")
        if transpose_left_low_to_range:
            f.write(f"⬆️  低音升高: B2及以下的音符已升到C3~B3范围\n")
        f.write(f"左手移动距离: {left_move:.2f}\n")
        f.write(f"左手移动次数: {left_count}\n")
        f.write(f"平均每次移动距离: {left_move/max(1, left_count):.2f}\n")
        f.write(f"小拇指基础键: {left_pinky_normal}次\n")
        f.write(f"小拇指扩展键: {left_pinky_extended}次\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # 保存左手指法结果
        f.write("左手指法分配（按时间顺序）:\n")
        f.write("-" * 160 + "\n")
        f.write("序号\t音符\t白键索引\t机械臂位置\t手指\t小拇指键\t开始时间\t持续时间\t结束时间\t强度\n")
        for i, result in enumerate(left_result):
            # 添加小拇指键类型显示
            pinky_str = ""
            if result['finger'] == 5:
                pinky_type = result.get('pinky_key_type', 'normal')
                pinky_str = "扩展" if pinky_type == 'extended' else "基础"
            else:
                pinky_str = "-"
            
            f.write(f"{i+1}\t{result['note']}\t{result['white_key_index']}\t{result['arm_position']}\t{result['finger']}\t{pinky_str}\t{result['start_time']:.2f}s\t{result['duration']:.2f}s\t{result['end_time']:.2f}s\t{result['velocity']}\n")
    
    # 保存左手JSON格式
    left_json_file = os.path.join(output_dir, f"{song_name}_left_hand_fingering.json")
    with open(left_json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'song_name': song_name,
            'hand': 'left',
            'notes_count': len(left_result),
            'original_notes_count': left_original_count if filter_left_low_notes else len(left_result),
            'filtered_count': left_filtered_count if filter_left_low_notes else 0,
            'filtered_threshold': 'B2' if filter_left_low_notes else None,
            'transposed_low_to_range': transpose_left_low_to_range,  # ⭐ 记录是否升低音到范围
            'target_range': 'C3~B3' if transpose_left_low_to_range else None,
            'move_distance': left_move,
            'move_count': left_count,
            'average_move_distance': left_move/max(1, left_count),
            'pinky_normal_count': left_pinky_normal,
            'pinky_extended_count': left_pinky_extended,
            'generated_time': datetime.now().isoformat(),
            'fingering_data': left_result
        }, f, indent=2, ensure_ascii=False)
    
    # ==================== 保存右手指法文件 ====================
    right_output_file = os.path.join(output_dir, f"{song_name}_right_hand_fingering.txt")
    
    with open(right_output_file, 'w', encoding='utf-8') as f:
        f.write(f"{song_name} - 右手指法分析结果\n")
        f.write("=" * 120 + "\n")
        f.write(f"右手音符数: {len(right_result)}\n")
        f.write(f"右手移动距离: {right_move:.2f}\n")
        f.write(f"右手移动次数: {right_count}\n")
        f.write(f"平均每次移动距离: {right_move/max(1, right_count):.2f}\n")
        f.write(f"小拇指基础键: {right_pinky_normal}次\n")
        f.write(f"小拇指扩展键: {right_pinky_extended}次\n")
        if transpose_right_octave:
            f.write(f"⭐ 音符转换: 已升高一个八度（+8度）\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # 保存右手指法结果
        f.write("右手指法分配（按时间顺序）:\n")
        f.write("-" * 160 + "\n")
        f.write("序号\t音符\t白键索引\t机械臂位置\t手指\t小拇指键\t开始时间\t持续时间\t结束时间\t强度\n")
        for i, result in enumerate(right_result):
            # 添加小拇指键类型显示
            pinky_str = ""
            if result['finger'] == 5:
                pinky_type = result.get('pinky_key_type', 'normal')
                pinky_str = "扩展" if pinky_type == 'extended' else "基础"
            else:
                pinky_str = "-"
            
            f.write(f"{i+1}\t{result['note']}\t{result['white_key_index']}\t{result['arm_position']}\t{result['finger']}\t{pinky_str}\t{result['start_time']:.2f}s\t{result['duration']:.2f}s\t{result['end_time']:.2f}s\t{result['velocity']}\n")
    
    # 保存右手JSON格式
    right_json_file = os.path.join(output_dir, f"{song_name}_right_hand_fingering.json")
    with open(right_json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'song_name': song_name,
            'hand': 'right',
            'notes_count': len(right_result),
            'move_distance': right_move,
            'move_count': right_count,
            'average_move_distance': right_move/max(1, right_count),
            'pinky_normal_count': right_pinky_normal,
            'pinky_extended_count': right_pinky_extended,
            'transposed_octave': transpose_right_octave,  # ⭐ 记录是否升八度
            'generated_time': datetime.now().isoformat(),
            'fingering_data': right_result
        }, f, indent=2, ensure_ascii=False)
    
    # ==================== 保存统计摘要文件 ====================
    summary_file = os.path.join(output_dir, f"{song_name}_summary.txt")
    
    total_notes = len(left_result) + len(right_result)
    total_move = left_move + right_move
    total_count = left_count + right_count
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"{song_name} - 指法统计摘要\n")
        f.write("=" * 60 + "\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        if transpose_right_octave:
            f.write(f"⭐ 右手音符转换: 已升高一个八度（+8度）\n")
        if filter_left_low_notes and left_filtered_count > 0:
            f.write(f"🗑️  左手低音过滤: 已删除{left_filtered_count}个音符（<= B2）\n")
        if transpose_left_low_to_range:
            f.write(f"⬆️  左手低音升高: B2及以下的音符已升到C3~B3范围\n")
        f.write("\n")
        
        f.write("左右手音符统计:\n")
        f.write(f"  总音符数: {total_notes}\n")
        f.write(f"  左手音符数: {len(left_result)}\n")
        if filter_left_low_notes and left_filtered_count > 0:
            f.write(f"  左手原始音符数: {left_original_count}\n")
            f.write(f"  左手过滤音符数: {left_filtered_count}\n")
        f.write(f"  右手音符数: {len(right_result)}\n\n")
        
        f.write("左右手移动统计:\n")
        f.write(f"  总移动距离: {total_move:.2f}\n")
        f.write(f"  左手移动距离: {left_move:.2f}\n")
        f.write(f"  右手移动距离: {right_move:.2f}\n")
        f.write(f"  总移动次数: {total_count}\n")
        f.write(f"  左手移动次数: {left_count}\n")
        f.write(f"  右手移动次数: {right_count}\n")
        f.write(f"  平均每次移动距离: {total_move/max(1, total_count):.2f}\n\n")
        
        f.write("小拇指键使用统计:\n")
        f.write(f"  左手:\n")
        f.write(f"    - 基础键: {left_pinky_normal}次\n")
        f.write(f"    - 扩展键: {left_pinky_extended}次\n")
        f.write(f"  右手:\n")
        f.write(f"    - 基础键: {right_pinky_normal}次\n")
        f.write(f"    - 扩展键: {right_pinky_extended}次\n\n")
        
        f.write("生成的文件:\n")
        f.write(f"  - 左手指法: {song_name}_left_hand_fingering.txt / .json\n")
        f.write(f"  - 右手指法: {song_name}_right_hand_fingering.txt / .json\n")
        f.write(f"  - 统计摘要: {song_name}_summary.txt\n")
    
    print(f"\n✅ 处理完成!")
    print(f"\n总体统计:")
    print(f"  总音符数: {total_notes}")
    print(f"  总移动距离: {total_move:.2f}")
    print(f"  总移动次数: {total_count}")
    print(f"\n左手统计:")
    print(f"  音符数: {len(left_result)}")
    if filter_left_low_notes and left_filtered_count > 0:
        print(f"  原始音符数: {left_original_count}")
        print(f"  过滤掉的音符: {left_filtered_count}个（<= B2）")
    if transpose_left_low_to_range:
        print(f"  ⬆️  低音升高: B2及以下已升到C3~B3范围")
    print(f"  移动距离: {left_move:.2f}")
    print(f"  移动次数: {left_count}")
    print(f"  小拇指基础键: {left_pinky_normal}次")
    print(f"  小拇指扩展键: {left_pinky_extended}次")
    print(f"\n右手统计:")
    print(f"  音符数: {len(right_result)}")
    print(f"  移动距离: {right_move:.2f}")
    print(f"  移动次数: {right_count}")
    print(f"  小拇指基础键: {right_pinky_normal}次")
    print(f"  小拇指扩展键: {right_pinky_extended}次")
    print(f"\n结果已分别保存到:")
    print(f"  📄 左手指法:")
    print(f"     - {left_output_file}")
    print(f"     - {left_json_file}")
    print(f"  📄 右手指法:")
    print(f"     - {right_output_file}")
    print(f"     - {right_json_file}")
    print(f"  📄 统计摘要:")
    print(f"     - {summary_file}")
    
    return left_result, right_result, total_move, total_count

def find_midi_files(song_name, base_dir="/Users/hezhili/PycharmProjects/piano_agent_service/data/midi"):
    """
    查找指定曲目的左右手MIDI文件
    
    Args:
        song_name: 曲目名称
        base_dir: 基础目录
    
    Returns:
        tuple: (左手MIDI文件路径, 右手MIDI文件路径)
    """
    # 搜索可能的文件路径
    left_patterns = [
        f"{base_dir}/{song_name}/{song_name}_left.mid",
        f"{base_dir}/{song_name}/left.mid",
        f"{base_dir}/{song_name}/*left*.mid"
    ]
    
    right_patterns = [
        f"{base_dir}/{song_name}/{song_name}_right.mid", 
        f"{base_dir}/{song_name}/right.mid",
        f"{base_dir}/{song_name}/*right*.mid"
    ]
    
    left_file = None
    right_file = None
    
    # 查找左手文件
    for pattern in left_patterns:
        files = glob.glob(pattern)
        if files:
            left_file = files[0]
            print(f"找到左手文件: {left_file}")
            break
    
    # 查找右手文件
    for pattern in right_patterns:
        files = glob.glob(pattern)
        if files:
            right_file = files[0]
            print(f"找到右手文件: {right_file}")
            break
    
    return left_file, right_file

def main():
    parser = argparse.ArgumentParser(description='合并左右手MIDI文件的指法数据')
    parser.add_argument('song_name', help='曲目名称')
    parser.add_argument('--output_dir', default='midi_output', help='输出目录')
    parser.add_argument('--transpose-right-octave', action='store_true', 
                        help='将右手所有音符升高一个八度（+8度）')
    parser.add_argument('--filter-left-low-notes', action='store_true',
                        help='过滤左手B2及以下的低音（删除<= B2的音符）')
    parser.add_argument('--transpose-left-low-to-range', action='store_true',
                        help='将左手B2及以下的音符升高到C3~B3范围（升8度或8度的倍数）')
    
    args = parser.parse_args()
    
    # 检查互斥选项
    if args.filter_left_low_notes and args.transpose_left_low_to_range:
        print("❌ 错误: --filter-left-low-notes 和 --transpose-left-low-to-range 不能同时使用")
        print("   请选择一个：")
        print("   - --filter-left-low-notes: 删除B2及以下的音符")
        print("   - --transpose-left-low-to-range: 将B2及以下的音符升到C3~B3范围")
        return
    
    song_name = args.song_name
    output_dir = os.path.join(args.output_dir, song_name)
    os.makedirs(output_dir, exist_ok=True)
    
    # 查找MIDI文件
    left_midi_file, right_midi_file = find_midi_files(song_name)
    
    if not left_midi_file:
        print(f"❌ 错误: 找不到左手MIDI文件")
        print("请确保文件存在于以下位置之一:")
        print(f"  - sheet_to_midi/out_midi/{song_name}/{song_name}_left.mid")
        print(f"  - sheet_to_midi/out_midi/{song_name}/left.mid")
        print(f"  - sheet_to_midi/out_midi/{song_name}/*left*.mid")
        return
    
    if not right_midi_file:
        print(f"❌ 错误: 找不到右手MIDI文件")
        print("请确保文件存在于以下位置之一:")
        print(f"  - sheet_to_midi/out_midi/{song_name}/{song_name}_right.mid")
        print(f"  - sheet_to_midi/out_midi/{song_name}/right.mid")
        print(f"  - sheet_to_midi/out_midi/{song_name}/*right*.mid")
        return
    
    # 分别保存左右手指法数据
    try:
        left_result, right_result, total_move, total_count = save_separate_hand_fingerings(
            left_midi_file, right_midi_file, output_dir, song_name,
            transpose_right_octave=args.transpose_right_octave,
            filter_left_low_notes=args.filter_left_low_notes,
            transpose_left_low_to_range=args.transpose_left_low_to_range
        )
        
        # 构建成功消息
        msg_parts = []
        if args.transpose_right_octave:
            msg_parts.append("右手已升八度")
        if args.filter_left_low_notes:
            msg_parts.append("左手已过滤低音")
        if args.transpose_left_low_to_range:
            msg_parts.append("左手低音已升到C3~B3")
        
        if msg_parts:
            print(f"\n✅ 成功完成 {song_name} 的左右手指法分离保存（{', '.join(msg_parts)}）!")
        else:
            print(f"\n✅ 成功完成 {song_name} 的左右手指法分离保存!")
        
    except Exception as e:
        print(f"❌ 处理过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
