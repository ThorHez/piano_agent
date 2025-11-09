def note_to_white_key_index(note):
    """
    将音符转换为白键索引（1-52，对应A0到C8的52个白键）
    
    Args:
        note: 音符字符串 (如 'C4', 'F#5', 'Bb3')
    
    Returns:
        int: 白键索引 (1-52)
    """
    # 规范化音符字符串
    note = note.upper()
    if 'B#' in note:
        note = note.replace('B#', 'C')
    if 'E#' in note:
        note = note.replace('E#', 'F')
    if 'CB' in note:
        note = note.replace('CB', 'B')
    if 'FB' in note:
        note = note.replace('FB', 'E')
    
    # 处理降号转换为升号
    if 'DB' in note:
        note = note.replace('DB', 'C#')
    if 'EB' in note:
        note = note.replace('EB', 'D#')
    if 'GB' in note:
        note = note.replace('GB', 'F#')
    if 'AB' in note:
        note = note.replace('AB', 'G#')
    if 'BB' in note:
        note = note.replace('BB', 'A#')
    
    # 解析音符和八度
    import re
    match = re.match(r'([A-G])([#b]?)(\d+)', note)
    if not match:
        return -1
    
    note_name, accidental, octave = match.groups()
    octave = int(octave)
    
    # 白键映射：C=1, D=2, E=3, F=4, G=5, A=6, B=7
    white_key_map = {'C': 1, 'D': 2, 'E': 3, 'F': 4, 'G': 5, 'A': 6, 'B': 7}
    
    if note_name not in white_key_map:
        return -1
    
    # 计算白键索引：A0=1, B0=2, C1=3, D1=4, E1=5, F1=6, G1=7, A1=8, B1=9, C2=10, ...
    if octave == 0:
        if note_name == 'A':
            return 1
        elif note_name == 'B':
            return 2
        else:
            return -1  # A0和B0以外的八度0音符不支持
    else:
        # 从C1开始计算：C1=3, D1=4, E1=5, F1=6, G1=7, A1=8, B1=9, C2=10, ...
        if note_name == 'C':
            white_key_index = (octave - 1) * 7 + 3
        elif note_name == 'D':
            white_key_index = (octave - 1) * 7 + 4
        elif note_name == 'E':
            white_key_index = (octave - 1) * 7 + 5
        elif note_name == 'F':
            white_key_index = (octave - 1) * 7 + 6
        elif note_name == 'G':
            white_key_index = (octave - 1) * 7 + 7
        elif note_name == 'A':
            white_key_index = octave * 7 + 1
        elif note_name == 'B':
            white_key_index = octave * 7 + 2
        else:
            return -1
    
    # 确保在有效范围内
    if 1 <= white_key_index <= 52:
        return white_key_index
    else:
        return -1

def get_all_piano_notes():
    """
    获取钢琴所有88个键的音符列表
    
    Returns:
        list: 所有88个音符的列表，从A0到C8
    """
    notes = []
    
    # A0到B0
    notes.extend(['A0', 'A#0', 'B0'])
    
    # C1到B7 (7个八度)
    for octave in range(1, 8):
        notes.extend([
            f'C{octave}', f'C#{octave}', f'D{octave}', f'D#{octave}', f'E{octave}',
            f'F{octave}', f'F#{octave}', f'G{octave}', f'G#{octave}', f'A{octave}', f'A#{octave}', f'B{octave}'
        ])
    
    # C8 (最高音)
    notes.append('C8')
    
    return notes

def is_black_key(note: str) -> bool:
    """
    判断音符是否为黑键
    
    Args:
        note: 音符字符串
    
    Returns:
        bool: 是否为黑键
    """
    return '#' in note or 'b' in note

def get_black_key_finger(note: str, hand_type: str) -> int:
    """
    根据黑键规则获取手指编号（标准钢琴指法编号：1=大拇指, 2=食指, 3=中指, 4=无名指, 5=小拇指）
    
    Args:
        note: 音符字符串（如 'C#4', 'F#5'）
        hand_type: 'left' 或 'right'
    
    Returns:
        int: 手指编号，如果无规则则返回-1
    """
    import re
    
    # 解析音符
    note_upper = note.upper()
    match = re.match(r'([A-G])([#b])(\d+)', note_upper)
    if not match:
        return -1
    
    note_name, accidental, octave = match.groups()
    octave = int(octave)
    
    # 只处理升号黑键
    if accidental != '#':
        return -1
    
    if hand_type == 'left':
        # 左手黑键指法规则（A0~B3）
        if note_name == 'A' and octave == 0:
            return 4  # A0# 用无名指
        elif note_name == 'C' and 1 <= octave <= 3:
            return 3  # C1#, C2#, C3# 用中指
        elif note_name == 'G' and 1 <= octave <= 3:
            return 3  # G1#, G2#, G3# 用中指
        elif note_name == 'D' and 1 <= octave <= 3:
            return 2  # D1#, D2#, D3# 用食指
        elif note_name == 'A' and 1 <= octave <= 3:
            return 2  # A1#, A2#, A3# 用食指
        elif note_name == 'F' and 1 <= octave <= 3:
            return 4  # F1#, F2#, F3# 用无名指
        else:
            return -1  # 不在左手范围或无规则
    
    elif hand_type == 'right':
        # 右手黑键指法规则（C4~C8）
        if octave < 4:
            return -1  # 不在右手范围
        
        if note_name == 'C':
            return 2  # C# 用食指
        elif note_name == 'F':
            return 2  # F# 用食指
        elif note_name == 'D':
            return 3  # D# 用中指
        elif note_name == 'G':
            return 3  # G# 用中指
        elif note_name == 'A':
            return 4  # A# 用无名指
        else:
            return -1  # 无规则
    
    return -1

def get_black_key_region(note: str) -> int:
    """
    获取黑键所在区域（1区或2区）
    
    Args:
        note: 音符字符串
    
    Returns:
        int: 1表示1区(C#/D#), 2表示2区(F#/G#/A#), -1表示不是黑键
    """
    import re
    
    if not is_black_key(note):
        return -1
    
    note_upper = note.upper()
    match = re.match(r'([A-G])([#b])(\d+)', note_upper)
    if not match:
        return -1
    
    note_name = match.group(1)
    
    # 1区：C#, D#
    if note_name in ['C', 'D']:
        return 1
    # 2区：F#, G#, A#
    elif note_name in ['F', 'G', 'A']:
        return 2
    else:
        return -1


def find_arm_positions_optimized(notes_list, move_penalty: float = 5.0, distance_penalty: float = 50.0, note_timing: list = None, hand_type: str = 'both'):
    """
    计算机械臂位置和指法（优化版本，包含硬件限制）
    
    Args:
        notes_list: 音符列表
        move_penalty: 移动次数惩罚系数
        distance_penalty: 单次移动距离惩罚系数（使用平方惩罚，距离越大惩罚越严重）
        note_timing: 音符时间信息列表
        hand_type: 'left', 'right', 或 'both'
    
    Returns:
        tuple: (指法结果列表, 总移动距离, 移动次数)
    """
    # 定义硬件音域范围（基于白键索引）
    # 白键索引计算：A0=1, B0=2, C1=3, ..., B3=23, C4=24, ..., C8=52
    LEFT_HAND_RANGE = (1, 23)     # A0(1) 到 B3(23)
    RIGHT_HAND_RANGE = (24, 52)   # C4(24) 到 C8(52)
    
    # 将音符转换为白键索引
    white_key_indices = []
    valid_notes = []
    valid_timing = []
    filtered_notes = []  # 记录过滤的音符
    
    for i, note in enumerate(notes_list):
        white_key_idx = note_to_white_key_index(note)
        if white_key_idx != -1:
            # 检查音符是否在手部允许的音域范围内
            is_valid = False
            filter_reason = ""
            
            if hand_type == 'left':
                # 左手：A0到B3
                if LEFT_HAND_RANGE[0] <= white_key_idx <= LEFT_HAND_RANGE[1]:
                    is_valid = True
                else:
                    filter_reason = f"超出左手音域范围(A0-B3)"
                    
            elif hand_type == 'right':
                # 右手：C4到C8
                if RIGHT_HAND_RANGE[0] <= white_key_idx <= RIGHT_HAND_RANGE[1]:
                    is_valid = True
                else:
                    filter_reason = f"超出右手音域范围(C4-C8)"
                    
            else:
                # 双手模式：不限制
                is_valid = True
            
            if is_valid:
                white_key_indices.append(white_key_idx)
                valid_notes.append(note)
                if note_timing:
                    valid_timing.append(note_timing[i])
            else:
                filtered_notes.append({
                    'note': note,
                    'white_key_index': white_key_idx,
                    'reason': filter_reason,
                    'time': note_timing[i]['start_time'] if note_timing and i < len(note_timing) else 0
                })
    
    # 显示过滤信息
    if filtered_notes:
        print(f"\n⚠️  警告：{len(filtered_notes)} 个音符因硬件限制被过滤：")
        for item in filtered_notes[:10]:  # 只显示前10个
            print(f"   - {item['note']} (白键索引{item['white_key_index']}, {item['time']:.2f}s): {item['reason']}")
        if len(filtered_notes) > 10:
            print(f"   ... 还有 {len(filtered_notes) - 10} 个音符被过滤")
    
    N = len(white_key_indices)
    if N == 0:
        return [], 0, 0
    
    # 如果没有提供时间信息，创建默认值
    if not valid_timing:
        valid_timing = [{'start_time': i * 0.5, 'duration': 0.5, 'velocity': 64} for i in range(N)]
    
    # 机械臂位置范围：1-52（覆盖所有白键）
    # ⭐ 右手覆盖6个白键（有小拇指扩展键），左手覆盖5个白键（无扩展键）
    # 对于高音区B7(51)和C8(52)，需要扩展到52以支持右手小拇指弹奏
    max_arm_position = 52
    
    # 对于每个音符，计算机械臂可以覆盖的位置范围
    # ⭐ 右手覆盖6个白键（offset 0-5），左手覆盖5个白键（offset 0-4）
    # 右手：位置范围 [white_key_idx-5, white_key_idx]
    # 左手：位置范围 [white_key_idx-4, white_key_idx]
    arm_position_ranges = []
    for idx, white_key_idx in enumerate(white_key_indices):
        note = notes_list[idx]
        
        # ⭐ 根据手类型确定覆盖范围
        if hand_type == 'left':
            # 左手只覆盖5个键（无扩展键）
            min_pos = max(1, white_key_idx - 4)  # offset 0-4
            max_pos = min(max_arm_position, white_key_idx)
        else:
            # 右手覆盖6个键（有扩展键）
            min_pos = max(1, white_key_idx - 5)  # offset 0-5
            max_pos = min(max_arm_position, white_key_idx)
        
        # 硬约束：特定音符必须使用特定手指
        if hand_type == 'right':
            # 右手指法映射：offset=0→finger=1, offset≥4→finger=5
            # 右手C4(24)：必须用大拇指(1)，offset=0
            if white_key_idx == 24:  # C4
                # offset=0: 24-arm_pos=0 → arm_pos=24
                min_pos = 24
                max_pos = 24
            # 右手B7(51)和C8(52)：必须用小拇指(5)，offset≥4
            elif white_key_idx == 51:  # B7
                # offset≥4: 51-arm_pos≥4 → arm_pos≤47
                # 取最大可能的offset=4或5: arm_pos=47或46
                min_pos = 46
                max_pos = 47
            elif white_key_idx == 52:  # C8
                # offset≥4: 52-arm_pos≥4 → arm_pos≤48
                # 取最大可能的offset=4或5: arm_pos=48或47
                min_pos = 47
                max_pos = 48
        elif hand_type == 'left':
            # 左手指法映射：offset=0→finger=5（小拇指），offset=4→finger=1（大拇指）
            # ⭐ 左手只有5个键（offset 0-4），没有扩展键
            # 左手B3(23)：必须用大拇指(1)，offset=4
            if white_key_idx == 23:  # B3
                # offset=4: 23-arm_pos=4 → arm_pos=19
                min_pos = 19
                max_pos = 19
            # 左手A0(1)：必须用小拇指(5)，offset=0
            elif white_key_idx == 1:  # A0
                # offset=0: 1-arm_pos=0 → arm_pos=1
                min_pos = 1
                max_pos = 1
            # 左手B0(2)：可用小拇指(5)，offset=0
            elif white_key_idx == 2:  # B0
                # offset=0: 2-arm_pos=0 → arm_pos=2
                min_pos = 2
                max_pos = 2
        
        arm_position_ranges.append((min_pos, max_pos))
    
    # 动态规划：dp[i][pos] = 弹奏前i个音符且第i个音符机械臂位置为pos的最小成本
    dp = [[float('inf')] * (max_arm_position + 1) for _ in range(N)]
    prev_pos = [[-1] * (max_arm_position + 1) for _ in range(N)]
    move_count = [[0] * (max_arm_position + 1) for _ in range(N)]  # 记录移动次数
    
    # 初始化第一个音符
    min_pos, max_pos = arm_position_ranges[0]
    
    for pos in range(min_pos, max_pos + 1):
        dp[0][pos] = 0  # 第一个音符没有移动成本
        move_count[0][pos] = 0
    
    # 填充DP表
    for i in range(1, N):
        min_pos, max_pos = arm_position_ranges[i]
        prev_min_pos, prev_max_pos = arm_position_ranges[i-1]
        
        for current_pos in range(min_pos, max_pos + 1):
            min_cost = float('inf')
            best_prev_pos = -1
            best_move_count = 0
            
            # 寻找前一个音符的最佳机械臂位置
            for prev_pos_val in range(prev_min_pos, prev_max_pos + 1):
                if dp[i-1][prev_pos_val] == float('inf'):
                    continue
                
                # 计算移动距离
                distance = abs(current_pos - prev_pos_val)
                
                # ⭐⭐ 新增约束：如果需要移臂，前一个音符不能是短音符
                if distance > 0:  # 需要移臂
                    prev_note_duration = valid_timing[i-1]['duration']
                    # 十六分音符≈0.2s，三十二分音符≈0.1s
                    # 如果前一个音符duration ≤ 0.25s，给予极高惩罚
                    if prev_note_duration <= 0.25:
                        # 跳过这个路径，不允许在短音符后移臂
                        continue
                
                # 计算移动次数（如果位置改变则+1）
                moves = move_count[i-1][prev_pos_val] + (1 if current_pos != prev_pos_val else 0)
                
                # ⭐ 总成本 = 基础成本 + 单次距离惩罚（平方） + 移动次数惩罚
                # 使用平方惩罚确保大距离移动会受到严重惩罚
                single_move_penalty = distance_penalty * (distance ** 2) if distance > 0 else 0
                total_cost = dp[i-1][prev_pos_val] + distance + single_move_penalty + move_penalty * moves
                
                if total_cost < min_cost:
                    min_cost = total_cost
                    best_prev_pos = prev_pos_val
                    best_move_count = moves
            
            dp[i][current_pos] = min_cost
            prev_pos[i][current_pos] = best_prev_pos
            move_count[i][current_pos] = best_move_count
    
    # 找到最优解
    min_cost = float('inf')
    best_final_pos = -1
    best_final_moves = 0
    
    min_pos, max_pos = arm_position_ranges[N-1]
    
    for pos in range(min_pos, max_pos + 1):
        if dp[N-1][pos] < min_cost:
            min_cost = dp[N-1][pos]
            best_final_pos = pos
            best_final_moves = move_count[N-1][pos]
    
    # 回溯得到机械臂位置序列
    arm_positions = [0] * N
    arm_positions[N-1] = best_final_pos
    for i in range(N-2, -1, -1):
        arm_positions[i] = prev_pos[i+1][arm_positions[i+1]]
    
    # 计算手指分配（基于硬件限制和黑键规则）
    finger_assignments = []
    black_key_notes_check = []  # 用于验证黑键指法
    
    for i in range(N):
        note = valid_notes[i]
        white_key_idx = white_key_indices[i]
        arm_pos = arm_positions[i]
        
        # 检查是否为黑键
        use_extended_pinky = False  # 黑键是否使用扩展键
        
        if is_black_key(note):
            # 黑键：使用固定指法规则
            finger = get_black_key_finger(note, hand_type)
            if finger == -1:
                # 无规则，使用默认逻辑
                print(f"⚠️  警告：黑键 {note} 无固定指法规则，使用默认逻辑")
                finger_offset = white_key_idx - arm_pos
                
                # ⭐ 根据手类型区分小拇指扩展键位置
                if hand_type == 'right':
                    # 右手：扩展键在offset=1（上方）
                    if finger_offset == 0:
                        finger = 5
                        use_extended_pinky = False
                    elif finger_offset == 1:
                        finger = 5
                        use_extended_pinky = True
                    elif finger_offset == 2:
                        finger = 4
                    elif finger_offset == 3:
                        finger = 3
                    elif finger_offset == 4:
                        finger = 2
                    elif finger_offset == 5:
                        finger = 1
                    else:
                        finger = 5
                else:
                    # 左手：只有5个键，没有扩展键
                    if finger_offset == 0:
                        finger = 5  # 小拇指基础键
                        use_extended_pinky = False  # ❌ 左手没有扩展键
                    elif finger_offset == 1:
                        finger = 4  # 无名指
                        use_extended_pinky = False
                    elif finger_offset == 2:
                        finger = 3  # 中指
                        use_extended_pinky = False
                    elif finger_offset == 3:
                        finger = 2  # 食指
                        use_extended_pinky = False
                    elif finger_offset == 4:
                        finger = 1  # 大拇指
                        use_extended_pinky = False
                    else:
                        finger = 5
            else:
                # 记录黑键指法
                # ✅ 黑键小拇指也要检查是否使用扩展键（仅右手）
                if finger == 5:
                    finger_offset = white_key_idx - arm_pos
                    # ⭐ 注意：只有右手有扩展键（offset=5），左手没有扩展键
                    if hand_type == 'right' and finger_offset == 5:
                        use_extended_pinky = True
                
                black_key_notes_check.append({
                    'note': note,
                    'finger': finger,
                    'region': get_black_key_region(note),
                    'arm_pos': arm_pos,
                    'use_extended': use_extended_pinky
                })
        else:
            # 白键：使用偏移量计算逻辑（左右手不同）
            finger_offset = white_key_idx - arm_pos
            
            # 手指分配规则（标准钢琴指法编号）：
            # 关键：左手和右手在钢琴上的摆放方向相反！
            # - 右手：大拇指(1)在左侧（低音），小拇指(5)在右侧（高音）
            # - 左手：小拇指(5)在左侧（低音），大拇指(1)在右侧（高音）
            
            # 判断是否使用小拇指扩展键
            use_extended_pinky = False
            
            if hand_type == 'right':
                # 右手指法映射（大拇指在低位，小拇指在高位）
                if finger_offset == 0:
                    finger = 1  # 大拇指（arm_pos + 0）
                elif finger_offset == 1:
                    finger = 2  # 食指（arm_pos + 1）
                elif finger_offset == 2:
                    finger = 3  # 中指（arm_pos + 2）
                elif finger_offset == 3:
                    finger = 4  # 无名指（arm_pos + 3）
                elif finger_offset == 4:
                    finger = 5  # 小拇指基础键（arm_pos + 4）
                    use_extended_pinky = False
                elif finger_offset == 5:
                    finger = 5  # 小拇指扩展键（arm_pos + 5）
                    use_extended_pinky = True  # ✅ 使用扩展键
                else:
                    print(f"⚠️  警告：右手白键 {note} 手指偏移量 {finger_offset} 无效")
                    finger = 1  # 默认使用大拇指
            else:
                # 左手指法映射（小拇指在低位，大拇指在高位）
                # ⭐ 注意：左手只有5个键，没有小拇指扩展键
                if finger_offset == 0:
                    finger = 5  # 小拇指基础键（arm_pos + 0）
                    use_extended_pinky = False  # ❌ 左手没有扩展键
                elif finger_offset == 1:
                    finger = 4  # 无名指（arm_pos + 1）
                    use_extended_pinky = False
                elif finger_offset == 2:
                    finger = 3  # 中指（arm_pos + 2）
                    use_extended_pinky = False
                elif finger_offset == 3:
                    finger = 2  # 食指（arm_pos + 3）
                    use_extended_pinky = False
                elif finger_offset == 4:
                    finger = 1  # 大拇指（arm_pos + 4）
                    use_extended_pinky = False
                else:
                    # offset >= 5 超出左手覆盖范围（只有5个键）
                    print(f"⚠️  警告：左手白键 {note} 手指偏移量 {finger_offset} 超出范围（左手只有5个键）")
                    finger = 5  # 默认使用小拇指
        
        finger_assignments.append((finger, use_extended_pinky))
    
    # 显示黑键指法验证
    if black_key_notes_check:
        print(f"\n🎹 黑键指法验证（共{len(black_key_notes_check)}个）：")
        finger_names = {1: "大拇指", 2: "食指", 3: "中指", 4: "无名指", 5: "小拇指"}
        region_names = {1: "1区(C#/D#)", 2: "2区(F#/G#/A#)"}
        
        # 按区域分组显示
        region1_notes = [item for item in black_key_notes_check if item['region'] == 1]
        region2_notes = [item for item in black_key_notes_check if item['region'] == 2]
        
        if region1_notes:
            print(f"  1区(C#/D#)黑键: {len(region1_notes)}个")
            for item in region1_notes[:3]:
                print(f"    {item['note']}: 使用{finger_names[item['finger']]}({item['finger']})")
        
        if region2_notes:
            print(f"  2区(F#/G#/A#)黑键: {len(region2_notes)}个")
            for item in region2_notes[:3]:
                print(f"    {item['note']}: 使用{finger_names[item['finger']]}({item['finger']})")
    
    # 生成输出结果
    output = []
    for i in range(N):
        note = valid_notes[i]
        finger, use_extended = finger_assignments[i]  # 解包元组
        
        # 确定小拇指使用的键类型
        pinky_key_type = 'normal'
        if finger == 5 and use_extended:
            pinky_key_type = 'extended'  # 使用扩展键
        
        result_data = {
            "note": note,
            "white_key_index": white_key_indices[i],
            "arm_position": arm_positions[i],
            "finger": finger,
            "pinky_key_type": pinky_key_type,  # ✅ 新增：小拇指键类型
            "start_time": valid_timing[i]['start_time'],
            "duration": valid_timing[i]['duration'],
            "end_time": valid_timing[i]['start_time'] + valid_timing[i]['duration'],
            "velocity": valid_timing[i]['velocity'],
            "hand": hand_type,  # 手部类型信息
            "is_black_key": is_black_key(note),  # 是否为黑键
            "black_key_region": get_black_key_region(note) if is_black_key(note) else 0  # 黑键区域
        }
        output.append(result_data)
    
    return output, min_cost, best_final_moves

# 旧的函数已删除，使用新的 find_arm_positions_optimized 函数

# 旧的函数已删除，使用新的 find_arm_positions_optimized 函数

def get_hand_range_description(hand_type: str) -> str:
    """
    获取手部音域范围描述（基于硬件限制，标准钢琴指法编号）
    
    Args:
        hand_type: 'left', 'right', 或 'both'
    
    Returns:
        str: 音域范围描述
    """
    if hand_type == 'left':
        desc = "左手音域: A0-B3 (白键索引 1-23), ⭐ 覆盖5个键（无小拇指扩展键）\n"
        desc += "    左手指法: 小拇指(5)→无名指(4)→中指(3)→食指(2)→大拇指(1)\n"
        desc += "    左手黑键: A0#用无名指(4), C#/G#用中指(3), D#/A#用食指(2), F#用无名指(4)"
        return desc
    elif hand_type == 'right':
        desc = "右手音域: C4-C8 (白键索引 24-52), ⭐ 覆盖6个键（有小拇指扩展键）\n"
        desc += "    右手指法: 大拇指(1)→食指(2)→中指(3)→无名指(4)→小拇指基础(5)→小拇指扩展(5)\n"
        desc += "    右手黑键: C#/F#用食指(2), D#/G#用中指(3), A#用无名指(4)"
        return desc
    else:
        return "双手音域: A0-B3 (左手, 5键) + C4-C8 (右手, 6键)"

def detect_hand_from_filename(filename):
    """
    从文件名检测左右手类型
    
    Args:
        filename: 文件名
    
    Returns:
        str: 'left', 'right', 或 'both'
    """
    filename_lower = filename.lower()
    if filename_lower.endswith('right') or 'right' in filename_lower:
        return 'right'
    elif filename_lower.endswith('left') or 'left' in filename_lower:
        return 'left'
    else:
        return 'both'

def find_notes_file(song_name, base_dir="midi_output"):
    """在midi_output目录下搜索指定曲名的notes.txt文件"""
    import os
    import glob
    
    # 搜索可能的文件路径
    search_patterns = [
        f"{base_dir}/{song_name}/{song_name}_notes.txt",
        f"{base_dir}/{song_name}/notes.txt",
        f"{base_dir}/*/{song_name}_notes.txt",
        f"{base_dir}/*/{song_name}*notes.txt"
    ]
    
    for pattern in search_patterns:
        files = glob.glob(pattern)
        if files:
            return files[0]  # 返回第一个找到的文件
    
    return None

def parse_notes_from_file(file_path):
    """从文本文件中解析音符和时间信息"""
    import re
    notes = []
    note_timing = []
    
    # 定义支持的音符范围（钢琴所有88键：A0到C8）
    supported_notes = set(get_all_piano_notes())
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 按时间排序音符
        note_entries = []
        for line in lines:
            if line.strip().startswith("Note:"):
                # 提取音符名称、时间和强度
                match = re.search(r"Note:\s*([A-Ga-g][#b]?\d+)\s*\(", line)
                if match:
                    note_name = match.group(1).upper()
                    # 提取开始时间、持续时间和强度
                    start_match = re.search(r"Start:\s*([\d.]+)s", line)
                    duration_match = re.search(r"Duration:\s*([\d.]+)s", line)
                    velocity_match = re.search(r"Velocity:\s*(\d+)", line)
                    
                    if start_match:
                        start_time = float(start_match.group(1))
                        duration = 0.5  # 默认持续时间
                        velocity = 64   # 默认强度
                        
                        if duration_match:
                            duration = float(duration_match.group(1))
                        if velocity_match:
                            velocity = int(velocity_match.group(1))
                        
                        note_entries.append((start_time, note_name, duration, velocity))
        
        # 按时间排序
        note_entries.sort(key=lambda x: x[0])
        
        # 过滤支持的音符
        unsupported = set()
        for start_time, note_name, duration, velocity in note_entries:
            if note_name in supported_notes:
                notes.append(note_name)
                note_timing.append({
                    'start_time': start_time,
                    'duration': duration,
                    'velocity': velocity
                })
            else:
                unsupported.add(note_name)
        
        if unsupported:
            print(f"过滤掉不支持的音符: {sorted(unsupported)}")
            
    except FileNotFoundError:
        print(f"文件 {file_path} 未找到")
        return [], []
    except Exception as e:
        print(f"解析文件时出错: {e}")
        return [], []
    
    return notes, note_timing

# 示例使用
if __name__ == "__main__":
    import sys
    import os
    
    # 获取曲名输入
    if len(sys.argv) > 1:
        song_name = sys.argv[1]
    else:
        song_name = input("请输入曲名（例如：小星星）: ").strip()
    
    if not song_name:
        print("未输入曲名，使用默认曲名：小星星")
        song_name = "小星星"
    
    print(f"正在搜索曲目: {song_name}")
    
    # 搜索对应的notes.txt文件
    file_path = find_notes_file(song_name)
    
    if not file_path:
        print(f"未找到曲目 '{song_name}' 对应的notes.txt文件")
        print("搜索路径包括:")
        print("- midi_output/{曲名}/{曲名}_notes.txt")
        print("- midi_output/{曲名}/notes.txt")
        print("- midi_output/*/{曲名}_notes.txt")
        print("- midi_output/*/{曲名}*notes.txt")
        
        # 列出可用的曲目
        import glob
        available_songs = []
        for pattern in ["midi_output/*/", "midi_output/*/*notes.txt"]:
            files = glob.glob(pattern)
            for file in files:
                if os.path.isdir(file):
                    dir_name = os.path.basename(file.rstrip('/'))
                    if dir_name != "midi_output":
                        available_songs.append(dir_name)
                elif "notes.txt" in file:
                    dir_name = os.path.basename(os.path.dirname(file))
                    if dir_name not in available_songs:
                        available_songs.append(dir_name)
        
        if available_songs:
            print(f"\n可用的曲目: {', '.join(sorted(set(available_songs)))}")
        
        print("\n使用示例音符进行演示")
        # 示例曲谱：包含左右手音符，覆盖钢琴全音域
        notes1 = ['F4', 'F#4', 'G4', 'A4', 'B4', 'C5', 'D5', 'E5']
        notes2 = [
            # 左手低音区（A0-B3）
            'C3', 'E3', 'G3', 'A3', 'B3',
            # 右手高音区（C4-C8）
            'C4', 'E4', 'F4','G4','A4','B4','C5','D5','E5','F5',
            'F#5','G#5','A#5','C6','D#6','F#6','G#6','A#6',
            'E5','G5','B5','D6','F#6','A6','C7',
            'G5','F#5','E5','D5','C5','B4','A4','G4',
            'F#4','G#4','A#4','C5','D5','E5','F5','G5',
            # 更多左手音符
            'A2', 'C3', 'E3', 'A3', 'B3'
        ]
        notes = notes2
        song_name = "示例曲目"
    else:
        print(f"找到文件: {file_path}")
        notes, note_timing = parse_notes_from_file(file_path)
        
        if not notes:
            print("未能从文件中读取到有效音符，使用示例音符")
            # 示例曲谱：包含左右手音符，覆盖钢琴全音域
            notes1 = ['F4', 'F#4', 'G4', 'A4', 'B4', 'C5', 'D5', 'E5']
            notes2 = [
                # 左手低音区（A0-B3）
                'C3', 'E3', 'G3', 'A3', 'B3',
                # 右手高音区（C4-C8）
                'C4', 'E4', 'F4','G4','A4','B4','C5','D5','E5','F5',
                'F#5','G#5','A#5','C6','D#6','F#6','G#6','A#6',
                'E5','G5','B5','D6','F#6','A6','C7',
                'G5','F#5','E5','D5','C5','B4','A4','G4',
                'F#4','G#4','A#4','C5','D5','E5','F5','G5',
                # 更多左手音符
                'A2', 'C3', 'E3', 'A3', 'B3'
            ]
            notes = notes2
            # 为示例音符创建默认时间信息
            note_timing = [{'start_time': i * 0.5, 'duration': 0.5, 'velocity': 64} for i in range(len(notes))]
            song_name = "示例曲目"
    
    print(f"从文件读取到 {len(notes)} 个音符")
    print("前20个音符:", notes[:20])
    
    # 检测左右手类型
    hand_type = 'both'
    if file_path:
        hand_type = detect_hand_from_filename(file_path)
        print(f"检测到文件类型: {hand_type}")
        print(f"硬件限制: {get_hand_range_description(hand_type)}")
    
    # 使用新的机械臂优化算法
    # distance_penalty=50.0 提供严重的单次移动距离惩罚（平方惩罚）
    result, total_move, move_count = find_arm_positions_optimized(
        notes, 
        move_penalty=5.0, 
        distance_penalty=50.0,  # ⭐ 单次移动距离惩罚系数（越大惩罚越严重）
        note_timing=note_timing, 
        hand_type=hand_type
    )
    
    # 计算过滤统计
    filtered_count = len(notes) - len(result)
    filter_rate = (filtered_count / len(notes) * 100) if len(notes) > 0 else 0
    
    # 计算移臂统计信息
    max_single_move = 0
    total_arm_moves = 0
    arm_move_distances = []  # 记录所有移臂距离
    short_notes_before_move = 0  # 统计移臂前的短音符数量（应该为0）
    
    if len(result) > 1:
        for i in range(1, len(result)):
            single_move = abs(result[i]['arm_position'] - result[i-1]['arm_position'])
            if single_move > 0:
                total_arm_moves += 1
                arm_move_distances.append(single_move)
                # 检查移臂前的音符是否为短音符
                if result[i-1]['duration'] <= 0.25:
                    short_notes_before_move += 1
            max_single_move = max(max_single_move, single_move)
    
    print(f"\n{song_name}机械臂指法分析结果")
    print("=" * 60)
    print(f"总音符数: {len(notes)}")
    print(f"有效音符数: {len(result)}")
    print(f"过滤音符数: {filtered_count} ({filter_rate:.1f}%)")
    print(f"总移动距离: {total_move:.2f} 格")
    print(f"机械臂移动次数: {total_arm_moves} 次")
    print(f"平均每次移动距离: {total_move/max(1, total_arm_moves):.2f} 格")
    print(f"⭐ 最大单次移动距离: {max_single_move} 格 (已应用严格平方惩罚)")
    print(f"⭐ 移臂前短音符数量: {short_notes_before_move} (应为0，已强制避免)")
    
    # 显示移臂距离分布
    if arm_move_distances:
        print(f"\n📊 移臂距离分布：")
        from collections import Counter
        distance_counter = Counter(arm_move_distances)
        for dist in sorted(distance_counter.keys()):
            count = distance_counter[dist]
            percentage = (count / len(arm_move_distances)) * 100
            bar = "█" * int(percentage / 5)  # 每5%一个方块
            print(f"   {dist:2d}格: {count:3d}次 ({percentage:5.1f}%) {bar}")
    
    # 显示结果
    print(f"\n机械臂指法分配:")
    print("-" * 160)
    print("序号\t音符\t白键索引\t机械臂位置\t手指\t小拇指键\t开始时间\t持续时间\t结束时间\t强度\t手\t黑键区域")
    for i, res in enumerate(result):
        region_str = ""
        if res.get('is_black_key', False):
            region = res.get('black_key_region', 0)
            if region == 1:
                region_str = "1区"
            elif region == 2:
                region_str = "2区"
        else:
            region_str = "白键"
        
        # 显示小拇指键类型
        pinky_str = ""
        if res['finger'] == 5:
            pinky_type = res.get('pinky_key_type', 'normal')
            pinky_str = "扩展" if pinky_type == 'extended' else "基础"
        else:
            pinky_str = "-"
        
        print(f"{i+1}\t{res['note']}\t{res['white_key_index']}\t{res['arm_position']}\t{res['finger']}\t{pinky_str}\t{res['start_time']:.2f}s\t{res['duration']:.2f}s\t{res['end_time']:.2f}s\t{res['velocity']}\t{res['hand']}\t{region_str}")
    
    # 保存结果到文件
    output_dir = f"midi_output/{song_name}"
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/{song_name}_arm_fingering_results.txt"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"{song_name}机械臂指法分析结果\n")
            f.write("=" * 120 + "\n")
            f.write(f"总音符数: {len(notes)}\n")
            f.write(f"有效音符数: {len(result)}\n")
            f.write(f"过滤音符数: {filtered_count} ({filter_rate:.1f}%)\n")
            f.write(f"总移动距离: {total_move:.2f} 格\n")
            f.write(f"机械臂移动次数: {total_arm_moves} 次\n")
            f.write(f"平均每次移动距离: {total_move/max(1, total_arm_moves):.2f} 格\n")
            f.write(f"⭐ 最大单次移动距离: {max_single_move} 格 (已应用严格平方惩罚)\n")
            f.write(f"⭐ 移臂前短音符数量: {short_notes_before_move} (应为0，已强制避免)\n")
            
            # 写入移臂距离分布
            if arm_move_distances:
                f.write(f"\n📊 移臂距离分布：\n")
                from collections import Counter
                distance_counter = Counter(arm_move_distances)
                for dist in sorted(distance_counter.keys()):
                    count = distance_counter[dist]
                    percentage = (count / len(arm_move_distances)) * 100
                    bar = "█" * int(percentage / 5)
                    f.write(f"   {dist:2d}格: {count:3d}次 ({percentage:5.1f}%) {bar}\n")
            
            f.write(f"\n手部类型: {hand_type}\n")
            f.write(f"硬件限制:\n{get_hand_range_description(hand_type)}\n")
            f.write(f"黑键区域: 1区(C#/D#), 2区(F#/G#/A#)\n")
            f.write(f"标准指法: 1=大拇指, 2=食指, 3=中指, 4=无名指, 5=小拇指\n")
            f.write(f"优化策略: \n")
            f.write(f"  1. 单次移臂距离平方惩罚（系数={50.0}）\n")
            f.write(f"  2. 强制避免在短音符后移臂（duration≤0.25s，包括十六分和三十二分音符）\n")
            f.write("\n")
            
            # 保存机械臂指法结果
            f.write("机械臂指法分配:\n")
            f.write("-" * 160 + "\n")
            f.write("序号\t音符\t白键索引\t机械臂位置\t手指\t小拇指键\t开始时间\t持续时间\t结束时间\t强度\t手\t黑键区域\n")
            for i, res in enumerate(result):
                region_str = ""
                if res.get('is_black_key', False):
                    region = res.get('black_key_region', 0)
                    if region == 1:
                        region_str = "1区"
                    elif region == 2:
                        region_str = "2区"
                else:
                    region_str = "白键"
                
                # 显示小拇指键类型
                pinky_str = ""
                if res['finger'] == 5:
                    pinky_type = res.get('pinky_key_type', 'normal')
                    pinky_str = "扩展" if pinky_type == 'extended' else "基础"
                else:
                    pinky_str = "-"
                
                f.write(f"{i+1}\t{res['note']}\t{res['white_key_index']}\t{res['arm_position']}\t{res['finger']}\t{pinky_str}\t{res['start_time']:.2f}s\t{res['duration']:.2f}s\t{res['end_time']:.2f}s\t{res['velocity']}\t{res['hand']}\t{region_str}\n")
        
        print(f"\n结果已保存到: {output_file}")
    except Exception as e:
        print(f"保存文件时出错: {e}")