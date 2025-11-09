import os
import json
import argparse
from collections import defaultdict

import mido

from utils import MIDI_INSTRUMENTS

# 定义MIDI控制器常量
SUSTAIN_PEDAL = 64        # 延音踏板
SOSTENUTO_PEDAL = 66      # 中间踏板
SOFT_PEDAL = 67           # 柔音踏板(Una Corda)
VOLUME_CONTROL = 7        # 音量控制
EXPRESSION_CONTROL = 11   # 表情控制
PAN_CONTROL = 10          # 声像(左右平衡)
MODULATION = 1            # 颤音控制

def get_note_name(note_number):
    """
    Convert MIDI note number to note name.
    
    Args:
        note_number: MIDI note number (0-127)
        
    Returns:
        Note name string (e.g., 'C4', 'D#5')
    """
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = note_number // 12 - 1
    note = notes[note_number % 12]
    return f"{note}{octave}"

def get_solfege_name(note_number):
    """
    Convert MIDI note number to solfège name.
    
    Args:
        note_number: MIDI note number (0-127)
        
    Returns:
        Solfège name string (e.g., 'do', 're', 'mi')
    """
    solfege = ['do', 'do#', 're', 're#', 'mi', 'fa', 'fa#', 'sol', 'sol#', 'la', 'la#', 'si']
    note = solfege[note_number % 12]
    return note

def get_tempo_from_midi(mid):
    """
    Extract tempo information from MIDI file.
    
    Args:
        mid: A mido.MidiFile object
        
    Returns:
        Default BPM (120) if no tempo message found, otherwise the first tempo in BPM
    """
    default_tempo = 120  # Default BPM if no tempo information found
    
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                # Convert microseconds per beat to BPM
                tempo_in_bpm = 60000000 / msg.tempo
                return tempo_in_bpm
    
    return default_tempo

def midi_to_notes(midi_file):
    """
    Extract notes from a MIDI file.
    
    Args:
        midi_file: Path to the MIDI file.
        
    Returns:
        A list of note events with their properties.
    """
    mid = mido.MidiFile(midi_file)
    
    # Track all notes across all tracks
    notes = []
    
    # Track active notes (for finding note end times)
    active_notes = defaultdict(list)
    
    # Track different types of controller events
    sustain_events = []
    sostenuto_events = []
    soft_pedal_events = []
    volume_events = []
    expression_events = []
    pan_events = []
    modulation_events = []
    pitch_bend_events = []
    
    # Track tempo changes
    tempo_changes = []
    current_tempo_bpm = None
    
    # Track time signature changes
    time_signature_changes = []
    
    # Get initial tempo information
    tempo_bpm = get_tempo_from_midi(mid)
    ticks_per_beat = mid.ticks_per_beat
    
    # Calculate seconds per tick for timing conversion
    seconds_per_beat = 60.0 / tempo_bpm
    seconds_per_tick = seconds_per_beat / ticks_per_beat
    
    # Get channel information
    channels_used = set()
    instruments_by_channel = {}
    track_channels = {}  # Track which channels are used in each track
    
    for track_idx, track in enumerate(mid.tracks):
        # Current absolute time in ticks
        current_time = 0
        track_channels[track_idx] = set()  # Initialize set for this track
        
        for msg in track:
            # Update current time
            current_time += msg.time
            
            # Track channels used
            if hasattr(msg, 'channel'):
                channels_used.add(msg.channel)
                track_channels[track_idx].add(msg.channel)
            
            # Program Change (Instrument selection)
            if msg.type == 'program_change':
                # Channel 9 is the percussion channel in MIDI
                if msg.channel == 9:
                    # For channel 9, we use bank 128 (percussion bank) and program 0
                    instruments_by_channel[msg.channel] = 128  # Use 128 to indicate percussion bank
                    print(f"Track {track_idx}, Channel {msg.channel} set to percussion bank")
                else:
                    instruments_by_channel[msg.channel] = msg.program
                    print(f"Track {track_idx}, Channel {msg.channel} set to instrument {msg.program} ({MIDI_INSTRUMENTS[msg.program] if msg.program < len(MIDI_INSTRUMENTS) else 'Unknown'})")
            
            # Time Signature
            elif msg.type == 'time_signature':
                time_signature_changes.append({
                    'track': track_idx,
                    'time': current_time,
                    'time_sec': current_time * seconds_per_tick,
                    'numerator': msg.numerator,
                    'denominator': msg.denominator
                })
            
            # Tempo Change
            elif msg.type == 'set_tempo':
                # Convert microseconds per beat to BPM
                current_tempo_bpm = 60000000 / msg.tempo
                tempo_changes.append({
                    'track': track_idx,
                    'time': current_time,
                    'time_sec': current_time * seconds_per_tick,
                    'tempo': msg.tempo,
                    'tempo_bpm': current_tempo_bpm
                })
                # Note: we don't update seconds_per_tick here because it would
                # complicate time calculations. Advanced implementations should
                # handle tempo changes differently.
            
            # Note on with velocity > 0 means note start
            elif msg.type == 'note_on' and msg.velocity > 0:
                # Store note start info in active_notes
                note_data = {
                    'track': track_idx,
                    'channel': msg.channel,
                    'note': msg.note,
                    'start_time': current_time,
                    'start_time_sec': current_time * seconds_per_tick,
                    'velocity': msg.velocity
                }
                active_notes[(msg.note, msg.channel)].append(note_data)
                
            # Note off or note on with velocity 0 means note end
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                # Find matching note_on events
                key = (msg.note, msg.channel)
                if key in active_notes and active_notes[key]:
                    # Get the earliest started note of this pitch
                    note_data = active_notes[key].pop(0)
                    
                    # Calculate duration in ticks and seconds
                    duration_ticks = current_time - note_data['start_time']
                    duration_sec = duration_ticks * seconds_per_tick
                    
                    # Only record notes with positive duration
                    if duration_ticks > 0:
                        notes.append({
                            'track': note_data['track'],
                            'channel': note_data['channel'],
                            'note': msg.note,
                            'note_name': get_note_name(msg.note),
                            'solfege': get_solfege_name(msg.note),
                            'start_time': note_data['start_time'],
                            'start_time_sec': note_data['start_time_sec'],
                            'end_time': current_time,
                            'end_time_sec': current_time * seconds_per_tick,
                            'duration': duration_ticks,
                            'duration_sec': duration_sec,
                            'velocity': note_data['velocity']
                        })
            
            # Control Change events
            elif msg.type == 'control_change':
                if msg.control == SUSTAIN_PEDAL:
                    # Standard threshold for sustain pedal: values >= 64 are ON
                    sustain_state = "on" if msg.value >= 64 else "off"
                    sustain_events.append({
                        'track': track_idx,
                        'channel': msg.channel,
                        'time': current_time,
                        'time_sec': current_time * seconds_per_tick,
                        'value': msg.value,
                        'state': sustain_state
                    })
                elif msg.control == SOSTENUTO_PEDAL:
                    # Middle pedal (sostenuto)
                    sostenuto_state = "on" if msg.value >= 64 else "off"
                    sostenuto_events.append({
                        'track': track_idx,
                        'channel': msg.channel,
                        'time': current_time,
                        'time_sec': current_time * seconds_per_tick,
                        'value': msg.value,
                        'state': sostenuto_state
                    })
                elif msg.control == SOFT_PEDAL:
                    # Soft pedal (una corda)
                    soft_state = "on" if msg.value >= 64 else "off"
                    soft_pedal_events.append({
                        'track': track_idx,
                        'channel': msg.channel,
                        'time': current_time,
                        'time_sec': current_time * seconds_per_tick,
                        'value': msg.value,
                        'state': soft_state
                    })
                elif msg.control == VOLUME_CONTROL:
                    # Volume control
                    volume_events.append({
                        'track': track_idx,
                        'channel': msg.channel,
                        'time': current_time,
                        'time_sec': current_time * seconds_per_tick,
                        'value': msg.value
                    })
                elif msg.control == EXPRESSION_CONTROL:
                    # Expression control
                    expression_events.append({
                        'track': track_idx,
                        'channel': msg.channel,
                        'time': current_time,
                        'time_sec': current_time * seconds_per_tick,
                        'value': msg.value
                    })
                elif msg.control == PAN_CONTROL:
                    # Pan control (left/right balance)
                    pan_events.append({
                        'track': track_idx,
                        'channel': msg.channel,
                        'time': current_time,
                        'time_sec': current_time * seconds_per_tick,
                        'value': msg.value
                    })
                elif msg.control == MODULATION:
                    # Modulation wheel
                    modulation_events.append({
                        'track': track_idx,
                        'channel': msg.channel,
                        'time': current_time,
                        'time_sec': current_time * seconds_per_tick,
                        'value': msg.value
                    })
            
            # Pitch Bend events
            elif msg.type == 'pitchwheel':
                pitch_bend_events.append({
                    'track': track_idx,
                    'channel': msg.channel,
                    'time': current_time,
                    'time_sec': current_time * seconds_per_tick,
                    'value': msg.pitch,
                    # MIDI pitch bend range is -8192 to 8191
                    'normalized_value': msg.pitch / 8192.0
                })
    
    # Sort all events by time
    notes.sort(key=lambda x: x['start_time'])
    sustain_events.sort(key=lambda x: x['time'])
    sostenuto_events.sort(key=lambda x: x['time'])
    soft_pedal_events.sort(key=lambda x: x['time'])
    volume_events.sort(key=lambda x: x['time'])
    expression_events.sort(key=lambda x: x['time'])
    pan_events.sort(key=lambda x: x['time'])
    modulation_events.sort(key=lambda x: x['time'])
    pitch_bend_events.sort(key=lambda x: x['time'])
    tempo_changes.sort(key=lambda x: x['time'])
    time_signature_changes.sort(key=lambda x: x['time'])
    
    # Collect all controllers and midi events
    control_events = {
        'sustain': sustain_events,
        'sostenuto': sostenuto_events,
        'soft': soft_pedal_events,
        'volume': volume_events,
        'expression': expression_events,
        'pan': pan_events,
        'modulation': modulation_events,
        'pitch_bend': pitch_bend_events,
        'tempo_changes': tempo_changes,
        'time_signature_changes': time_signature_changes
    }
    
    # Create timing info with all necessary information
    timing_info = {
        'tempo_bpm': tempo_bpm,
        'ticks_per_beat': ticks_per_beat,
        'seconds_per_tick': seconds_per_tick,
        'channels_used': sorted(list(channels_used)),
        'instruments_by_channel': instruments_by_channel,
        'track_channels': {str(k): sorted(list(v)) for k, v in track_channels.items()},  # Convert sets to lists for JSON
        'sample_rate': 44100,  # Standard sample rate for MIDI playback
        'has_multiple_tempos': len(tempo_changes) > 1,
        'tempo_changes_count': len(tempo_changes),
        'track_count': len(mid.tracks)
    }
    
    # Add timing info to the first note record for reference
    if notes:
        notes[0]['_timing_info'] = timing_info
    
    return notes, control_events, timing_info

def get_midi_info(midi_file):
    """Get general information about the MIDI file."""
    mid = mido.MidiFile(midi_file)
    
    # Get tempo information
    tempo_bpm = get_tempo_from_midi(mid)
    
    # Collect information about channels
    channels_used = set()
    instruments_by_channel = {}
    
    for track_idx, track in enumerate(mid.tracks):
        for msg in track:
            if hasattr(msg, 'channel'):
                channels_used.add(msg.channel)
                
                # Track program changes (instrument assignments)
                if msg.type == 'program_change':
                    instruments_by_channel[msg.channel] = msg.program
    
    info = {
        'filename': os.path.basename(midi_file),
        'format': mid.type,
        'ticks_per_beat': mid.ticks_per_beat,
        'tempo_bpm': tempo_bpm,
        'seconds_per_beat': 60.0 / tempo_bpm,
        'seconds_per_tick': (60.0 / tempo_bpm) / mid.ticks_per_beat,
        'track_count': len(mid.tracks),
        'track_names': [],
        'channels_used': sorted(list(channels_used)),
        'instruments_by_channel': instruments_by_channel,
        'sample_rate': 44100  # Standard sample rate for MIDI playback
    }
    
    # Extract track names if available
    for i, track in enumerate(mid.tracks):
        track_name = f"Track {i}"
        for msg in track:
            if msg.type == 'track_name':
                track_name = msg.name
                break
        info['track_names'].append(track_name)
    
    return info

def save_notes_to_file(notes, output_file, format='json'):
    """Save notes to a file in the specified format."""
    if format == 'json':
        with open(output_file, 'w') as f:
            json.dump(notes, f, indent=2)
    elif format == 'txt':
        with open(output_file, 'w') as f:
            for note in notes:
                f.write(f"Note: {note['note_name']} ({note['solfege']}), "
                        f"Start: {note['start_time_sec']:.2f}s, "
                        f"Duration: {note['duration_sec']:.2f}s, "
                        f"Velocity: {note['velocity']}, "
                        f"Channel: {note['channel']}\n")
    elif format == 'solfege':
        with open(output_file, 'w') as f:
            for note in notes:
                f.write(f"{note['solfege']} ")

def save_control_events_to_file(control_events, output_file, format='json'):
    """Save controller events to a file."""
    if format == 'json':
        with open(output_file, 'w') as f:
            json.dump(control_events, f, indent=2)
    elif format == 'txt':
        with open(output_file, 'w') as f:
            # Process sustain events
            if control_events['sustain']:
                f.write("SUSTAIN PEDAL EVENTS:\n")
                for event in control_events['sustain']:
                    f.write(f"  {event['time_sec']:.2f}s: {event['state']} (value: {event['value']}, channel: {event['channel']})\n")
                f.write("\n")
            
            # Process sostenuto events
            if control_events['sostenuto']:
                f.write("SOSTENUTO (MIDDLE) PEDAL EVENTS:\n")
                for event in control_events['sostenuto']:
                    f.write(f"  {event['time_sec']:.2f}s: {event['state']} (value: {event['value']}, channel: {event['channel']})\n")
                f.write("\n")
            
            # Process soft pedal events
            if control_events['soft']:
                f.write("SOFT PEDAL (UNA CORDA) EVENTS:\n")
                for event in control_events['soft']:
                    f.write(f"  {event['time_sec']:.2f}s: {event['state']} (value: {event['value']}, channel: {event['channel']})\n")
                f.write("\n")
            
            # Process volume events
            if control_events['volume']:
                f.write("VOLUME CONTROL EVENTS:\n")
                for event in control_events['volume']:
                    f.write(f"  {event['time_sec']:.2f}s: {event['value']} (channel: {event['channel']})\n")
                f.write("\n")
            
            # Process expression events
            if control_events['expression']:
                f.write("EXPRESSION CONTROL EVENTS:\n")
                for event in control_events['expression']:
                    f.write(f"  {event['time_sec']:.2f}s: {event['value']} (channel: {event['channel']})\n")
                f.write("\n")
            
            # Process pitch bend events
            if control_events['pitch_bend']:
                f.write("PITCH BEND EVENTS:\n")
                for event in control_events['pitch_bend']:
                    f.write(f"  {event['time_sec']:.2f}s: {event['value']} (normalized: {event['normalized_value']:.2f}, channel: {event['channel']})\n")
                f.write("\n")
            
            # Process tempo changes
            if control_events['tempo_changes']:
                f.write("TEMPO CHANGES:\n")
                for event in control_events['tempo_changes']:
                    f.write(f"  {event['time_sec']:.2f}s: {event['tempo_bpm']:.2f} BPM\n")
                f.write("\n")
            
            # Process time signature changes
            if control_events['time_signature_changes']:
                f.write("TIME SIGNATURE CHANGES:\n")
                for event in control_events['time_signature_changes']:
                    f.write(f"  {event['time_sec']:.2f}s: {event['numerator']}/{event['denominator']}\n")
                f.write("\n")

def create_sequential_notation(notes, output_file):
    """
    Create a sequential notation of the melody.
    """
    # Group notes by start time to handle chords
    notes_by_time = defaultdict(list)
    for note in notes:
        notes_by_time[note['start_time']].append(note)
    
    # Sort by start time
    times = sorted(notes_by_time.keys())
    
    with open(output_file, 'w') as f:
        f.write("Sequential Notation:\n\n")
        
        for time in times:
            chord_notes = notes_by_time[time]
            # Sort by pitch for consistent output
            chord_notes.sort(key=lambda x: x['note'])
            
            if len(chord_notes) == 1:
                # Single note
                note = chord_notes[0]
                f.write(f"{note['solfege']} ")
            else:
                # Chord - group with parentheses
                chord = "(" + " ".join(note['solfege'] for note in chord_notes) + ")"
                f.write(f"{chord} ")
            
            # Add line breaks periodically for readability
            if times.index(time) % 10 == 9:
                f.write("\n")
        
        f.write("\n")

def analyze_chords(notes, output_file):
    """
    Analyze chords in the MIDI file (basic implementation).
    """
    # Group notes by start time
    notes_by_time = defaultdict(list)
    for note in notes:
        # Only consider notes that are long enough to be part of a chord
        if note['duration_sec'] > 0.1:
            notes_by_time[note['start_time']].append(note)
    
    chord_analysis = []
    
    # Process each time point with multiple notes
    for time, chord_notes in sorted(notes_by_time.items()):
        if len(chord_notes) >= 3:  # Consider as a chord if 3+ notes
            # Extract note numbers (0-11) for chord analysis
            note_numbers = sorted([note['note'] % 12 for note in chord_notes])
            
            # Simple chord recognition (very basic)
            chord_type = "unknown"
            root_note = note_numbers[0]
            root_name = get_note_name(root_note)
            
            # Check for common chord types (very simplified)
            if len(note_numbers) == 3:
                # Check for major chord (root, major third, perfect fifth)
                if (note_numbers[1] - note_numbers[0]) % 12 == 4 and (note_numbers[2] - note_numbers[0]) % 12 == 7:
                    chord_type = "major"
                # Check for minor chord (root, minor third, perfect fifth)
                elif (note_numbers[1] - note_numbers[0]) % 12 == 3 and (note_numbers[2] - note_numbers[0]) % 12 == 7:
                    chord_type = "minor"
            
            chord_analysis.append({
                'time': time,
                'time_sec': chord_notes[0]['start_time_sec'],
                'notes': [note['note_name'] for note in chord_notes],
                'root': root_name,
                'type': chord_type
            })
    
    # Write results to file
    with open(output_file, 'w') as f:
        f.write("Chord Analysis:\n\n")
        
        for chord in chord_analysis:
            f.write(f"Time: {chord['time_sec']:.2f}s\n")
            f.write(f"Notes: {', '.join(chord['notes'])}\n")
            if chord['type'] != "unknown":
                f.write(f"Possible chord: {chord['root']} {chord['type']}\n")
            f.write("\n")

def main():
    parser = argparse.ArgumentParser(description='Convert MIDI files to musical notation.')
    parser.add_argument('midi_file', nargs='?', default=r"sound_to_midi\output\弹钢琴的楠楠 - 江南 (钢琴版).mid", help='Path to the MIDI file')
    parser.add_argument('--output_dir', default='midi_output', help='Directory to save output files')
    parser.add_argument('--analyze_chords', action='store_true', help='Perform basic chord analysis')
    
    args = parser.parse_args()
    
    # Set paths
    midi_file = args.midi_file
    output_dir = args.output_dir
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    output_dir = os.path.join(output_dir, os.path.split(midi_file)[-1].rsplit('.', 1)[0])
    os.makedirs(output_dir, exist_ok=True)
    
    # Get MIDI file info
    midi_info = get_midi_info(midi_file)
    print(f"Processing MIDI file: {midi_info['filename']}")
    print(f"Format: {midi_info['format']}, Tracks: {midi_info['track_count']}")
    print(f"Track names: {midi_info['track_names']}")
    print(f"Tempo: {midi_info['tempo_bpm']:.2f} BPM, {midi_info['seconds_per_beat']:.4f} seconds per beat")
    print(f"Channels Used: {midi_info['channels_used']}")
    print(f"Sample Rate: {midi_info['sample_rate']} Hz")
    
    if midi_info['instruments_by_channel']:
        print("Instruments by Channel:")
        for channel, program in midi_info['instruments_by_channel'].items():
            print(f"  Channel {channel}: Program {program}")
    
    # Extract notes and control events
    notes, control_events, timing_info = midi_to_notes(midi_file)
    print(f"Extracted {len(notes)} notes from the MIDI file.")
    
    # Report on controller events
    controller_counts = {k: len(v) for k, v in control_events.items() if isinstance(v, list)}
    print("Control events found:")
    for controller, count in controller_counts.items():
        if count > 0:
            print(f"  - {controller}: {count} events")
    
    # Add timing info to the first note record for reference
    if notes:
        notes[0]['_timing_info'] = timing_info

    # Define output file paths
    base_name = os.path.splitext(os.path.basename(midi_file))[0]
    json_output = os.path.join(output_dir, f"{base_name}_notes.json")
    txt_output = os.path.join(output_dir, f"{base_name}_notes.txt")
    solfege_output = os.path.join(output_dir, f"{base_name}_solfege.txt")
    sequential_output = os.path.join(output_dir, f"{base_name}_sequential.txt")
    controls_json_output = os.path.join(output_dir, f"{base_name}_controls.json")
    controls_txt_output = os.path.join(output_dir, f"{base_name}_controls.txt")
    
    # Save note information
    save_notes_to_file(notes, json_output, format='json')
    save_notes_to_file(notes, txt_output, format='txt')
    save_notes_to_file(notes, solfege_output, format='solfege')
    create_sequential_notation(notes, sequential_output)
    
    # Save control events (all types)
    save_control_events_to_file(control_events, controls_json_output, format='json')
    save_control_events_to_file(control_events, controls_txt_output, format='txt')
    
    # For backward compatibility, save sustain separately
    if control_events['sustain']:
        sustain_json_output = os.path.join(output_dir, f"{base_name}_sustain.json")
        save_notes_to_file(control_events['sustain'], sustain_json_output, format='json')
        print(f"  - {sustain_json_output} (Sustain JSON)")
    
    # Perform chord analysis if requested
    if args.analyze_chords:
        chord_analysis_output = os.path.join(output_dir, f"{base_name}_chords.txt")
        analyze_chords(notes, chord_analysis_output)
        print(f"  - {chord_analysis_output} (Chord Analysis)")
    
    print(f"Saved note data to:")
    print(f"  - {json_output} (JSON)")
    print(f"  - {txt_output} (Text)")
    print(f"  - {solfege_output} (Solfège)")
    print(f"  - {sequential_output} (Sequential Notation)")
    print(f"Saved control events to:")
    print(f"  - {controls_json_output} (JSON)")
    print(f"  - {controls_txt_output} (Text)")

if __name__ == "__main__":
    main() 