import os
import re
import struct
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from .models import GeoPhysDataModel


def clean_curve_name(name: str, default_prefix: str = "曲线", index: int = 0) -> str:
    """清理曲线名称"""
    if not name or not name.strip():
        return f"{default_prefix}{index+1}"
    name = name.strip()
    name = re.sub(r'[^\w\u4e00-\u9fff\-]', '', name)
    return name if name else f"{default_prefix}{index+1}"


def clean_unit(unit: str) -> str:
    """清理单位字符串"""
    if not unit:
        return ''
    unit = unit.strip()
    unit = re.sub(r'[^\w/\-\u4e00-\u9fff]', '', unit)
    return unit


class LASDecoder:
    """LAS格式解编器"""
    
    def decode(self, file_path: str) -> Tuple[Dict[str, Any], List[str], pd.DataFrame, str]:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        version_info = self._parse_version(content)
        well_info = self._parse_well(content)
        curve_info, curve_names = self._parse_curve(content)
        data = self._parse_data(content, curve_names)
        
        metadata = {
            'version_info': version_info,
            'well_info': well_info,
            'curve_info': curve_info
        }
        
        depth_curve = 'DEPT' if 'DEPT' in curve_names else curve_names[0] if curve_names else ''
        return metadata, curve_names, data, depth_curve
    
    def detect_format(self, file_path: str) -> bool:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline()
                return first_line.strip().startswith('~VERSION') or first_line.strip().startswith('~VERS')
        except:
            return False
    
    def _parse_version(self, content: str) -> Dict[str, Any]:
        version_info = {}
        null_value = -99999.0
        version_match = re.search(r'~VERSION(.*?)~|~VERS(.*?)~', content, re.DOTALL | re.IGNORECASE)
        if version_match:
            version_content = version_match.group(1) if version_match.group(1) else version_match.group(2)
            lines = version_content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key_part = parts[0].strip()
                    value = parts[1].strip()
                    key_parts = key_part.split('.')
                    key = key_parts[0].strip()
                    try:
                        numeric_value = float(value)
                        version_info[key] = numeric_value
                    except ValueError:
                        version_info[key] = value
                    if key.upper() == 'NULL':
                        try:
                            null_value = float(value)
                        except:
                            pass
        version_info['NULL'] = null_value
        return version_info
    
    def _parse_well(self, content: str) -> Dict[str, Any]:
        well_info = {}
        well_match = re.search(r'~WELL(.*?)~', content, re.DOTALL | re.IGNORECASE)
        if well_match:
            well_content = well_match.group(1)
            lines = well_content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key_part = parts[0].strip()
                    value = parts[1].strip()
                    key_parts = key_part.split('.')
                    key = key_parts[0].strip()
                    try:
                        numeric_value = float(value)
                        well_info[key] = numeric_value
                    except ValueError:
                        well_info[key] = value
        return well_info
    
    def _parse_curve(self, content: str) -> Tuple[List[Dict[str, str]], List[str]]:
        curve_info = []
        curve_names = []
        curve_match = re.search(r'~CURVE(.*?)(~A|$)', content, re.DOTALL | re.IGNORECASE)
        if curve_match:
            curve_content = curve_match.group(1)
            lines = curve_content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#') or line.upper() == 'INFORMATION':
                    continue
                parts = line.split()
                if parts and '.' in parts[0]:
                    mnemonic_parts = parts[0].split('.')
                    mnemonic = mnemonic_parts[0].strip()
                    unit = mnemonic_parts[1].strip() if len(mnemonic_parts) > 1 else ''
                    api_code = ''
                    description = ''
                    if len(parts) > 1:
                        desc_start = 1
                        for i, part in enumerate(parts[1:], 1):
                            if ':' in part:
                                desc_start = i
                                break
                        api_code = parts[1] if desc_start > 1 else ''
                        description = ' '.join(parts[desc_start:])
                        if description.startswith(':'):
                            description = description[1:].strip()
                    curve_dict = {
                        'mnemonic': mnemonic,
                        'unit': unit,
                        'api_code': api_code,
                        'description': description
                    }
                    curve_info.append(curve_dict)
                    curve_names.append(mnemonic)
        return curve_info, curve_names
    
    def _parse_data(self, content: str, curve_names: List[str]) -> pd.DataFrame:
        data_lines = []
        data_match = re.search(r'~A(.*?)$', content, re.DOTALL | re.IGNORECASE)
        if data_match:
            data_content = data_match.group(1)
            lines = data_content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                try:
                    parts = list(map(float, line.split()))
                    if len(parts) == len(curve_names):
                        data_lines.append(parts)
                except ValueError:
                    continue
        data = pd.DataFrame(data_lines, columns=curve_names)
        return data


class FLDDecoder:
    """FLD格式解编器"""
    
    def decode(self, file_path: str) -> Tuple[Dict[str, Any], List[str], pd.DataFrame, str]:
        metadata = {}
        curve_names = []
        data_lines = []
        
        try:
            with open(file_path, 'r', encoding='gbk', errors='ignore') as f:
                all_lines = f.readlines()
                header_lines = [line.strip() for line in all_lines[:3204]]
                
                metadata['version'] = header_lines[0] if len(header_lines) > 0 else ''
                metadata['probe_model'] = header_lines[5] if len(header_lines) > 5 else ''
                metadata['file_path'] = header_lines[2] if len(header_lines) > 2 else ''
                metadata['file_name'] = header_lines[3] if len(header_lines) > 3 else ''
                metadata['logging_location'] = header_lines[4] if len(header_lines) > 4 else ''
                metadata['hole_number'] = header_lines[5] if len(header_lines) > 5 else ''
                
                try:
                    metadata['hole_diameter'] = float(header_lines[6]) if len(header_lines) > 6 else 0.0
                    metadata['hole_depth'] = float(header_lines[7]) if len(header_lines) > 7 else 0.0
                    metadata['casing_length'] = float(header_lines[8]) if len(header_lines) > 8 else 0.0
                except:
                    pass
                
                metadata['time'] = header_lines[9] if len(header_lines) > 9 else ''
                
                try:
                    metadata['field_temperature'] = float(header_lines[10]) if len(header_lines) > 10 else 0.0
                    metadata['altitude'] = float(header_lines[11]) if len(header_lines) > 11 else 0.0
                    metadata['water_level'] = float(header_lines[12]) if len(header_lines) > 12 else 0.0
                except:
                    pass
                
                metadata['logging_unit'] = header_lines[13] if len(header_lines) > 13 else ''
                metadata['responsible_person'] = header_lines[14] if len(header_lines) > 14 else ''
                metadata['operator'] = header_lines[15] if len(header_lines) > 15 else ''
                
                try:
                    metadata['sample_points'] = int(header_lines[51]) if len(header_lines) > 51 and header_lines[51].isdigit() else 0
                    metadata['start_depth'] = float(header_lines[53]) if len(header_lines) > 53 else 0.0
                    metadata['end_depth'] = float(header_lines[54]) if len(header_lines) > 54 else 0.0
                    metadata['sample_interval'] = float(header_lines[55]) if len(header_lines) > 55 else 0.0
                    metadata['logging_speed'] = float(header_lines[56]) if len(header_lines) > 56 else 0.0
                except:
                    pass
                
                probe_model = metadata.get('probe_model', '')
                probe_model = clean_curve_name(probe_model)
                
                data_started = False
                data_start_index = 0
                
                for i in range(len(all_lines) - 1, -1, -1):
                    line = all_lines[i].strip()
                    if not line:
                        continue
                    try:
                        parts = list(map(float, line.split()))
                        if len(parts) >= 2:
                            data_start_index = i
                            data_started = True
                            break
                    except ValueError:
                        continue
                
                if data_started:
                    temp_data = []
                    for i in range(data_start_index, -1, -1):
                        line = all_lines[i].strip()
                        if not line:
                            continue
                        try:
                            parts = list(map(float, line.split()))
                            if len(parts) >= 2:
                                temp_data.append(parts)
                            else:
                                break
                        except ValueError:
                            break
                    data_lines = temp_data[::-1]
        except Exception as e:
            metadata['error'] = str(e)
        
        if data_lines:
            actual_channel_count = len(data_lines[0])
            metadata['channel_count'] = actual_channel_count
            
            if '密度' in probe_model:
                default_curves = ['深度', '密度', '参数2', '参数3', '参数4', '参数5', '参数6']
            elif '磁化率' in probe_model:
                default_curves = ['深度', '磁化率', '参数2', '参数3', '参数4', '参数5', '参数6']
            elif '三分量' in probe_model:
                default_curves = ['深度', 'X分量', 'Y分量', 'Z分量', '参数4', '参数5', '参数6', '参数7', '参数8']
            else:
                default_curves = ['深度'] + [f'参数{i}' for i in range(1, actual_channel_count)]
            
            curve_names = default_curves[:actual_channel_count]
            for i in range(len(curve_names)):
                curve_names[i] = clean_curve_name(curve_names[i], default_prefix="通道", index=i)
        else:
            curve_names = ['深度', '数据']
        
        data = pd.DataFrame(data_lines, columns=curve_names[:len(data_lines[0])] if data_lines else curve_names)
        depth_curve = curve_names[0] if curve_names else ''
        
        return metadata, curve_names, data, depth_curve
    
    def detect_format(self, file_path: str) -> bool:
        try:
            with open(file_path, 'r', encoding='gbk', errors='ignore') as f:
                first_line = f.readline()
            return first_line.strip().startswith('RJF-2.ver1.0')
        except Exception:
            return False


class WDTDecoder:
    """WDT格式解编器"""
    
    def decode(self, file_path: str, channel_count: Optional[int] = None) -> Tuple[Dict[str, Any], List[str], pd.DataFrame, str]:
        metadata = {}
        data_lines = []
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        data_start = 0
        while data_start < len(content) and content[data_start] == 32:
            data_start += 1
        
        data_content = content[data_start:]
        data_length = len(data_content)
        
        file_name = os.path.basename(file_path).lower()
        default_channel_count = 2
        
        if '三分量' in file_name or 'threecomponent' in file_name:
            default_channel_count = 8
        elif '密度' in file_name or 'density' in file_name:
            default_channel_count = 8
        elif '磁化率' in file_name or 'susceptibility' in file_name:
            default_channel_count = 1
        
        if channel_count is not None:
            possible_channel_counts = [channel_count]
        else:
            possible_channel_counts = [default_channel_count]
        
        channel_results = []
        
        for ch_count in possible_channel_counts:
            temp_data = []
            frame_size = ch_count * 2 + 4
            header_size = 20 * frame_size
            
            if data_length <= header_size:
                continue
            
            for i in range(header_size, data_length, frame_size):
                frame_data = data_content[i:i+frame_size]
                if len(frame_data) < frame_size:
                    continue
                
                try:
                    meter_high_bytes = frame_data[0:2]
                    meter_high = (meter_high_bytes[1] << 8) | meter_high_bytes[0]
                    meter_low_bytes = frame_data[2:4]
                    meter_low = (meter_low_bytes[1] << 8) | meter_low_bytes[0]
                    actual_depth = meter_high + meter_low * 0.01
                    
                    if not (0.20 <= actual_depth <= 199.50):
                        continue
                    if meter_low > 99:
                        continue
                    
                    channels_data = []
                    for ch in range(ch_count):
                        ch_start = 4 + ch * 2
                        ch_end = ch_start + 2
                        ch_bytes = frame_data[ch_start:ch_end]
                        ch_value = (ch_bytes[1] << 8) | ch_bytes[0]
                        channels_data.append(ch_value)
                    
                    temp_data.append([actual_depth] + channels_data)
                except Exception:
                    continue
            
            min_data_count = 50 if channel_count is not None else 100
            if len(temp_data) > min_data_count:
                channel_results.append((ch_count, temp_data, len(temp_data)))
        
        if channel_results:
            best_channel_count, best_data, _ = channel_results[0]
        else:
            best_channel_count = default_channel_count
            best_data = []
        
        curve_names = ["井深"] + [f"通道{i+1}" for i in range(best_channel_count)]
        for i in range(len(curve_names)):
            curve_names[i] = clean_curve_name(curve_names[i], default_prefix="通道", index=i)
        
        metadata['num_channels'] = best_channel_count
        metadata['record_count'] = len(best_data)
        
        data = pd.DataFrame(best_data, columns=curve_names[:len(best_data[0])] if best_data else curve_names)
        depth_curve = curve_names[0] if curve_names else ''
        
        if depth_curve in data.columns and not data.empty:
            data = data.sort_values(by=depth_curve, ascending=True)
            data = data.drop_duplicates(subset=[depth_curve], keep='first')
            data = data.reset_index(drop=True)
        
        return metadata, curve_names, data, depth_curve
    
    def detect_format(self, file_path: str) -> bool:
        return file_path.lower().endswith('.wdt')


class TXTDecoder:
    """TXT格式解编器"""
    
    def decode(self, file_path: str) -> Tuple[Dict[str, Any], List[str], pd.DataFrame, str]:
        metadata = {}
        curve_names = []
        data_lines = []
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline().strip()
            
            try:
                list(map(float, first_line.split()))
                data_lines.append(list(map(float, first_line.split())))
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        parts = list(map(float, line.split()))
                        data_lines.append(parts)
                    except ValueError:
                        continue
            except ValueError:
                curve_names = first_line.split()
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        parts = list(map(float, line.split()))
                        data_lines.append(parts)
                    except ValueError:
                        continue
        
        if not curve_names and data_lines:
            curve_count = len(data_lines[0])
            curve_names = [f'Column_{i+1}' for i in range(curve_count)]
        
        data = pd.DataFrame(data_lines, columns=curve_names[:len(data_lines[0])] if data_lines else curve_names)
        depth_curve = curve_names[0] if curve_names else ''
        
        return metadata, curve_names, data, depth_curve
    
    def detect_format(self, file_path: str) -> bool:
        return file_path.lower().endswith('.txt')


class WISDecoder:
    """WIS格式解编器"""
    
    DATA_TYPES = {
        1: ('b', 1), 2: ('h', 2), 3: ('l', 4), 4: ('f', 4),
        5: ('d', 8), 6: ('B', 1), 7: ('H', 2), 8: ('L', 4)
    }
    
    def decode(self, file_path: str) -> Tuple[Dict[str, Any], List[str], pd.DataFrame, str]:
        metadata = {}
        
        try:
            with open(file_path, 'rb') as f:
                file_id = f.read(10)
                if file_id.strip() != b'WIS 1.0':
                    raise ValueError(f"不是有效的WIS文件")
                metadata['version'] = file_id.decode('ascii').strip()
                
                head_data = f.read(46)
                machine_type, max_obj_num, obj_num, block_len, entry_offset, data_offset, file_size, time_create = struct.unpack('<HHHHLLLL', head_data[:24])
                
                metadata['machine_type'] = machine_type
                metadata['object_number'] = obj_num
                metadata['block_len'] = block_len
                
                f.seek(entry_offset)
                objects = []
                for i in range(obj_num):
                    entry_data = f.read(72)
                    if len(entry_data) < 72:
                        break
                    name = entry_data[:16].decode('utf-8', errors='ignore').split('\x00')[0].strip()
                    name = clean_curve_name(name)
                    status = struct.unpack('<l', entry_data[16:20])[0]
                    attribute = struct.unpack('<H', entry_data[20:22])[0]
                    position = struct.unpack('<L', entry_data[24:28])[0]
                    objects.append({'name': name, 'status': status, 'attribute': attribute, 'position': position})
                
                channel_objects = [obj for obj in objects if obj['attribute'] == 1 and obj['status'] == 0]
                if not channel_objects:
                    raise ValueError("WIS文件中没有找到有效的通道对象")
                
                channel_obj = channel_objects[0]
                f.seek(channel_obj['position'])
                
                channel_basic = f.read(56)
                if len(channel_basic) < 56:
                    raise ValueError("通道基本信息不足")
                
                unit = channel_basic[:8].decode('utf-8', errors='ignore').split('\x00')[0].strip()
                rep_code, code_len, min_val, max_val, reserved, num_dim = struct.unpack('<HHffHH', channel_basic[40:56])
                
                metadata['curve_unit'] = unit
                metadata['rep_code'] = rep_code
                
                dim_info = []
                for i in range(num_dim):
                    dim_data = f.read(56)
                    if len(dim_data) < 56:
                        continue
                    dim_name = dim_data[:8].decode('utf-8', errors='ignore').split('\x00')[0].strip()
                    dim_name = clean_curve_name(dim_name)
                    start_val, delta, samples = struct.unpack('<ffL', dim_data[32:44])
                    dim_info.append({'name': dim_name, 'start_val': start_val, 'delta': delta, 'samples': samples})
                
                metadata['dimension_info'] = dim_info
                
                if dim_info:
                    depth_dim = dim_info[0]
                    data_type = self.DATA_TYPES.get(rep_code, ('f', 4))
                    
                    depths = []
                    curve_values = []
                    
                    if depth_dim['delta'] == 0:
                        for _ in range(depth_dim['samples']):
                            depth_data = f.read(4)
                            if len(depth_data) < 4:
                                continue
                            depth = struct.unpack('<f', depth_data)[0]
                            depths.append(depth)
                    else:
                        for i in range(depth_dim['samples']):
                            depth = depth_dim['start_val'] + i * depth_dim['delta']
                            depths.append(depth)
                    
                    for _ in range(depth_dim['samples']):
                        curve_data = f.read(code_len)
                        if len(curve_data) < code_len:
                            continue
                        curve_value = struct.unpack(f'<{data_type[0]}', curve_data)[0]
                        curve_values.append(curve_value)
                    
                    curve_name = channel_obj['name'] or '曲线值'
                    curve_names = ['深度', curve_name]
                    data = pd.DataFrame({'深度': depths, curve_name: curve_values})
                    data['深度'] = data['深度'].round(4)
                    
                    return metadata, curve_names, data, '深度'
        
        except Exception as e:
            metadata['error'] = str(e)
        
        return metadata, [], pd.DataFrame(), ''
    
    def detect_format(self, file_path: str) -> bool:
        if not file_path.lower().endswith('.wis'):
            return False
        try:
            with open(file_path, 'rb') as f:
                file_id = f.read(10)
                return file_id.strip().startswith(b'WIS')
        except:
            return False


class SEGYDecoder:
    """SEGY格式解编器 - 地震勘探数据标准格式"""
    
    SAMPLE_FORMATS = {
        1: ('IBM 32-bit float', 4),
        2: ('32-bit integer', 4),
        3: ('16-bit integer', 2),
        4: ('Fixed-point + gain', 4),
        5: ('IEEE 32-bit float', 4),
        6: ('IEEE 64-bit float', 8),
        8: ('8-bit integer', 1),
    }
    
    def decode(self, file_path: str, max_traces: int = 100) -> Tuple[Dict[str, Any], List[str], pd.DataFrame, str]:
        metadata = {}
        curve_names = []
        
        filesize = os.path.getsize(file_path)
        metadata['file_size'] = filesize
        
        with open(file_path, 'rb') as f:
            text_header = self._read_text_header(f)
            metadata['text_header'] = text_header[:500]
            metadata['text_encoding'] = self.text_encoding
            
            binary_header = self._read_binary_header(f)
            metadata['binary_header'] = binary_header
            
            endian = self.endian
            format_code = self.format_code
            n_samples = self.n_samples
            
            if n_samples <= 0:
                raise ValueError(f"SEGY 文件解析失败: 无效的采样点数 (n_samples={n_samples}), "
                               f"format_code={format_code}, endian={'big' if endian == '>' else 'little'}. "
                               f"文件可能不是有效的 SEG-Y 格式或已损坏")
            
            bps = self.SAMPLE_FORMATS.get(format_code, ('', 2))[1]
            trace_bytes = 240 + n_samples * bps
            n_traces = (filesize - 3600) // trace_bytes
            
            actual_traces = min(n_traces, max_traces)
            
            traces = []
            trace_headers = []
            
            f.seek(3600)
            
            for i in range(actual_traces):
                raw_hdr = f.read(240)
                if len(raw_hdr) < 240:
                    break
                
                hdr = self._parse_trace_header(raw_hdr, endian)
                trace_headers.append(hdr)
                
                raw_data = f.read(n_samples * bps)
                if len(raw_data) < n_samples * bps:
                    break
                
                trace = self._decode_trace_data(raw_data, format_code, n_samples, endian)
                traces.append(trace)
            
            if not traces:
                raise ValueError("SEGY 文件解析失败: 无法读取任何道数据，文件可能已损坏或格式不正确")
                
                data_matrix = np.column_stack(traces)
                
                si = abs(binary_header.get('sample_interval_us', 0))
                if si == 0:
                    si = 4000
                
                total = si * n_samples
                if 5 <= total <= 10000:
                    dt_ns = float(si)
                elif 5000 < total <= 10_000_000:
                    dt_ns = si / 1000.0
                elif 0 < total < 5:
                    dt_ns = si * 1000.0
                else:
                    dt_ns = 4.0
                
                time_axis = np.arange(n_samples) * dt_ns
                
                metadata['n_traces'] = len(traces)
                metadata['n_samples'] = n_samples
                metadata['dt_ns'] = dt_ns
                metadata['time_window_ns'] = dt_ns * n_samples
                metadata['format_code'] = format_code
                metadata['endian'] = 'big' if endian == '>' else 'little'
                
                curve_names = ['时间'] + [f'道{i+1}' for i in range(len(traces))]
                
                data_dict = {'时间': time_axis}
                for i, trace in enumerate(traces):
                    data_dict[f'道{i+1}'] = trace
                
                data = pd.DataFrame(data_dict)
                
                return metadata, curve_names, data, '时间'
    
    def _read_text_header(self, f) -> str:
        raw = f.read(3200)
        if len(raw) < 3200:
            raise ValueError("文件太小，不是有效的 SEG-Y 文件")
        
        ascii_score = sum(32 <= b <= 126 for b in raw)
        try:
            ebc = raw.decode('cp500')
            ebc_score = sum(32 <= ord(c) <= 126 for c in ebc)
        except:
            ebc, ebc_score = '', 0
        
        if ascii_score >= ebc_score:
            text_header = raw.decode('ascii', errors='replace')
            self.text_encoding = 'ASCII'
        else:
            text_header = ebc
            self.text_encoding = 'EBCDIC (cp500)'
        
        text_header = '\n'.join(
            text_header[i*80:(i+1)*80].rstrip() 
            for i in range(40) 
            if text_header[i*80:(i+1)*80].strip()
        )
        
        return text_header
    
    def _read_binary_header(self, f) -> Dict[str, Any]:
        raw = f.read(400)
        if len(raw) < 400:
            raise ValueError(f"SEGY 二进制头不完整: 仅读取到 {len(raw)} 字节，需要 400 字节")
        
        # 尝试检测字节序
        detected_endian = None
        detected_fc = None
        detected_ns = None
        
        for endian in ('<', '>'):
            try:
                fc = struct.unpack(f'{endian}h', raw[24:26])[0]
                ns = struct.unpack(f'{endian}h', raw[20:22])[0]
                detected_fc = fc
                detected_ns = ns
                if 1 <= fc <= 8 and 0 < ns < 65535:
                    detected_endian = endian
                    break
            except struct.error:
                continue
        
        if detected_endian is None:
            # 记录原始字节用于调试
            raw_hex = raw[20:26].hex()
            raise ValueError(f"无法识别 SEG-Y 字节序: format_code={detected_fc}, n_samples={detected_ns}, "
                           f"原始字节[20:26]={raw_hex}. 文件可能不是有效的 SEG-Y 格式")
        
        self.endian = detected_endian
        
        bo = self.endian
        
        binary_header = {
            'job_id': struct.unpack(f'{bo}i', raw[0:4])[0],
            'line_number': struct.unpack(f'{bo}i', raw[4:8])[0],
            'reel_number': struct.unpack(f'{bo}i', raw[8:12])[0],
            'n_data_traces': struct.unpack(f'{bo}h', raw[12:14])[0],
            'n_aux_traces': struct.unpack(f'{bo}h', raw[14:16])[0],
            'sample_interval_us': struct.unpack(f'{bo}h', raw[16:18])[0],
            'sample_interval_orig': struct.unpack(f'{bo}h', raw[18:20])[0],
            'n_samples': struct.unpack(f'{bo}h', raw[20:22])[0],
            'n_samples_orig': struct.unpack(f'{bo}h', raw[22:24])[0],
            'format_code': struct.unpack(f'{bo}h', raw[24:26])[0],
            'ensemble_fold': struct.unpack(f'{bo}h', raw[26:28])[0],
            'trace_sorting': struct.unpack(f'{bo}h', raw[28:30])[0],
            'segy_revision': struct.unpack(f'{bo}h', raw[300:302])[0],
        }
        
        self.format_code = binary_header['format_code']
        self.n_samples = binary_header['n_samples']
        
        if self.format_code not in self.SAMPLE_FORMATS:
            self.format_code = 3
        
        return binary_header
    
    def _parse_trace_header(self, raw: bytes, endian: str) -> Dict[str, Any]:
        bo = endian
        return {
            'trace_seq_line': struct.unpack(f'{bo}i', raw[0:4])[0],
            'trace_seq_file': struct.unpack(f'{bo}i', raw[4:8])[0],
            'field_record': struct.unpack(f'{bo}i', raw[8:12])[0],
            'trace_in_record': struct.unpack(f'{bo}i', raw[12:16])[0],
            'cdp': struct.unpack(f'{bo}i', raw[20:24])[0],
            'trace_id': struct.unpack(f'{bo}h', raw[28:30])[0],
            'n_samples': struct.unpack(f'{bo}h', raw[114:116])[0],
            'sample_interval': struct.unpack(f'{bo}h', raw[116:118])[0],
        }
    
    def _decode_trace_data(self, raw: bytes, format_code: int, n_samples: int, endian: str) -> np.ndarray:
        bo = endian
        
        if format_code == 1:
            return self._ibm2ieee(raw, n_samples)
        elif format_code == 2:
            return np.frombuffer(raw, dtype=np.dtype(f'{bo}i4'), count=n_samples).astype(np.float32)
        elif format_code == 3:
            return np.frombuffer(raw, dtype=np.dtype(f'{bo}i2'), count=n_samples).astype(np.float32)
        elif format_code == 5:
            return np.frombuffer(raw, dtype=np.dtype(f'{bo}f4'), count=n_samples).astype(np.float32)
        elif format_code == 8:
            return np.frombuffer(raw, dtype=np.int8, count=n_samples).astype(np.float32)
        else:
            return np.frombuffer(raw, dtype=np.dtype(f'{bo}i2'), count=n_samples).astype(np.float32)
    
    @staticmethod
    def _ibm2ieee(raw: bytes, n: int) -> np.ndarray:
        u = np.frombuffer(raw, dtype='>u4', count=n)
        sign = (u >> 31).astype(np.float64)
        exp = ((u >> 24) & 0x7F).astype(np.int32) - 64
        frac = (u & 0x00FFFFFF).astype(np.float64) / 2**24
        return ((-1.0)**sign * frac * np.power(16.0, exp)).astype(np.float32)
    
    def detect_format(self, file_path: str) -> bool:
        ext = file_path.lower().split('.')[-1]
        if ext in ['sgy', 'segy']:
            return True
        try:
            with open(file_path, 'rb') as f:
                f.seek(3200)
                raw = f.read(400)
                if len(raw) >= 400:
                    for endian in ('<', '>'):
                        try:
                            fc = struct.unpack(f'{endian}h', raw[24:26])[0]
                            ns = struct.unpack(f'{endian}h', raw[20:22])[0]
                            if 1 <= fc <= 8 and 0 < ns < 65535:
                                return True
                        except:
                            continue
        except:
            pass
        return False


class MultiFormatParser:
    """多格式解析器"""
    
    def __init__(self):
        self.decoders = {
            'las': LASDecoder(),
            'fld': FLDDecoder(),
            'wdt': WDTDecoder(),
            'txt': TXTDecoder(),
            'wis': WISDecoder(),
            'sgy': SEGYDecoder(),
            'segy': SEGYDecoder()
        }
    
    def get_supported_formats(self) -> List[str]:
        return list(self.decoders.keys())
    
    def auto_detect_format(self, file_path: str) -> Optional[str]:
        ext = os.path.splitext(file_path)[1].lower()[1:]
        if ext in self.decoders:
            decoder = self.decoders[ext]
            if decoder.detect_format(file_path):
                return ext
        
        for fmt, decoder in self.decoders.items():
            if decoder.detect_format(file_path):
                return fmt
        
        return None
    
    def parse(self, file_path: str, format: Optional[str] = None) -> GeoPhysDataModel:
        if format is not None:
            # 验证传入的格式是否匹配
            if format in self.decoders:
                decoder = self.decoders[format]
                if not decoder.detect_format(file_path):
                    # 尝试自动检测实际格式
                    detected = self.auto_detect_format(file_path)
                    if detected:
                        format = detected
                    else:
                        raise ValueError(f"文件格式与指定格式 '{format}' 不匹配，且无法自动识别: {file_path}")
            else:
                # 指定的格式不支持，尝试自动检测
                format = self.auto_detect_format(file_path)
        else:
            format = self.auto_detect_format(file_path)
        
        if format is None or format not in self.decoders:
            raise ValueError(f"无法识别文件格式: {file_path}")
        
        decoder = self.decoders[format]
        metadata, curve_names, data, depth_curve = decoder.decode(file_path)
        
        if data.empty:
            raise ValueError(f"文件解析失败或数据为空: {file_path}")
        
        depth_array = data[depth_curve].values if depth_curve in data.columns else np.array([])
        curves = {col: data[col].values for col in data.columns if col != depth_curve}
        
        well_name = metadata.get('well_info', {}).get('WELL', '') or metadata.get('file_name', 'Unknown')
        
        return GeoPhysDataModel(
            well_name=well_name,
            depth=depth_array,
            curves=curves
        )
