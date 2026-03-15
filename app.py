import streamlit as st
import tempfile
import os
import numpy as np
import pandas as pd
from src.models import GeoPhysDataModel
from src.parsers import LASParser
from src.plugin_manager import PluginManager
from src.visualization import WellPlotter
from src.multi_format_parser import MultiFormatParser
from typing import Dict, Any, Optional
import io


st.set_page_config(page_title="GeoPhysHub", page_icon="⛏️", layout="wide")


@st.cache_resource
def get_plugin_manager() -> PluginManager:
    return PluginManager()


@st.cache_resource
def get_multi_format_parser() -> MultiFormatParser:
    return MultiFormatParser()


@st.cache_resource
def parse_file(file_path: str, file_ext: str) -> GeoPhysDataModel:
    parser = get_multi_format_parser()
    return parser.parse(file_path, format=file_ext)


def generate_dynamic_params(param_ui: Dict[str, Any]) -> Dict[str, Any]:
    params = {}
    if not param_ui:
        return params
    
    for param_name, param_config in param_ui.items():
        param_type = param_config.get('type', 'slider')
        label = param_config.get('label', param_name)
        min_val = param_config.get('min', 0)
        max_val = param_config.get('max', 100)
        default_val = param_config.get('default', min_val)
        step = param_config.get('step', 1)
        
        if param_type == 'slider':
            params[param_name] = st.slider(
                label=label,
                min_value=min_val,
                max_value=max_val,
                value=default_val,
                step=step
            )
        elif param_type == 'number' or param_type == 'int' or param_type == 'float':
            params[param_name] = st.number_input(
                label=label,
                min_value=min_val,
                max_value=max_val,
                value=default_val,
                step=step
            )
        else:
            st.warning(f"Unknown parameter type: {param_type}")
    
    return params


def export_to_csv(data: GeoPhysDataModel) -> str:
    df = pd.DataFrame(data.curves)
    df.insert(0, 'DEPTH', data.depth)
    return df.to_csv(index=False)


def export_to_json(data: GeoPhysDataModel) -> str:
    import json
    export_data = {
        'well_name': data.well_name,
        'depth': data.depth.tolist(),
        'curves': {k: v.tolist() for k, v in data.curves.items()}
    }
    return json.dumps(export_data, indent=2)


def export_to_las(data: GeoPhysDataModel) -> str:
    lines = []
    lines.append('~VERSION INFORMATION')
    lines.append('VERS.               2.0                 :CWLS LOG ASCII STANDARD -VERSION 2.0')
    lines.append('WRAP.               NO                  :ONE LINE PER DEPTH STEP')
    lines.append('')
    lines.append('~WELL INFORMATION BLOCK')
    lines.append(f'WELL.               {data.well_name:<20} :WELL NAME')
    lines.append(f'STRT.METER          {min(data.depth):<20.4f} :START DEPTH')
    lines.append(f'STOP.METER          {max(data.depth):<20.4f} :STOP DEPTH')
    lines.append(f'STEP.METER          {(data.depth[1]-data.depth[0]) if len(data.depth) > 1 else 0:<20.4f} :STEP')
    lines.append('NULL.               -99999.0000         :NULL VALUE')
    lines.append('')
    lines.append('~CURVE INFORMATION')
    lines.append('DEPT.METER                               :DEPTH')
    for curve_name in data.curves.keys():
        lines.append(f'{curve_name:<20}                    :{curve_name}')
    lines.append('')
    lines.append('~A')
    
    for i in range(len(data.depth)):
        row = [f'{data.depth[i]:<20.4f}']
        for curve_name in data.curves.keys():
            row.append(f'{data.curves[curve_name][i]:<20.4f}')
        lines.append(''.join(row))
    
    return '\n'.join(lines)


def main():
    st.title("⛏️ GeoPhysHub - 地球物理测井数据处理平台")
    
    if 'data' not in st.session_state:
        st.session_state.data = None
    if 'processed_curves' not in st.session_state:
        st.session_state.processed_curves = {}
    if 'selected_algo_name' not in st.session_state:
        st.session_state.selected_algo_name = None
    
    plugin_manager = get_plugin_manager()
    parser = get_multi_format_parser()
    supported_formats = parser.get_supported_formats()
    
    with st.sidebar:
        st.header("数据加载")
        uploaded_file = st.file_uploader(
            "上传测井数据文件", 
            type=['las', 'LAS', 'fld', 'FLD', 'wdt', 'WDT', 'wis', 'WIS', 'txt', 'TXT', 'sgy', 'SGY', 'segy', 'SEGY']
        )
        
        if uploaded_file is not None:
            current_file_name = uploaded_file.name
            if 'last_uploaded_file' not in st.session_state or st.session_state.last_uploaded_file != current_file_name:
                st.session_state.last_uploaded_file = current_file_name
                try:
                    file_ext = os.path.splitext(uploaded_file.name)[1].lower()[1:]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_file_path = tmp_file.name
                    
                    data = parse_file(tmp_file_path, file_ext)
                    st.session_state.data = data
                    st.session_state.processed_curves = {}
                    st.success(f"✅ 成功加载井: {data.well_name}")
                    st.info(f"📁 格式: {file_ext.upper()}")
                    
                    os.unlink(tmp_file_path)
                except Exception as e:
                    st.error(f"文件加载失败: {str(e)}")
                    import traceback
                    with st.expander("查看详细错误"):
                        st.code(traceback.format_exc())
        
        st.divider()
        
        if st.session_state.data is not None:
            data = st.session_state.data
            
            st.header("曲线选择")
            curve_names = list(data.curves.keys())
            if 'selected_curves' not in st.session_state or st.session_state.selected_curves is None:
                st.session_state.selected_curves = curve_names
            
            # 确保默认值都在选项中
            valid_defaults = [c for c in st.session_state.selected_curves if c in curve_names]
            if not valid_defaults:
                valid_defaults = curve_names
            
            selected_curves = st.multiselect("选择要显示的曲线", curve_names, default=valid_defaults)
            st.session_state.selected_curves = selected_curves
            
            st.divider()
            
            st.header("算法插件")
            algorithms = plugin_manager.get_all_algorithms()
            
            if algorithms:
                algo_names = [algo['name'] for algo in algorithms]
                default_index = 0
                if st.session_state.selected_algo_name and st.session_state.selected_algo_name in algo_names:
                    default_index = algo_names.index(st.session_state.selected_algo_name)
                
                selected_algo_name = st.selectbox(
                    "选择处理算法",
                    options=algo_names,
                    index=default_index
                )
                st.session_state.selected_algo_name = selected_algo_name
                
                selected_algo = None
                for algo in algorithms:
                    if algo['name'] == selected_algo_name:
                        selected_algo = algo
                        break
                
                if selected_algo:
                    st.subheader("算法参数")
                    params = generate_dynamic_params(selected_algo.get('param_ui', {}))
                    
                    target_curve = st.selectbox("选择要处理的曲线", selected_curves)
                    
                    if st.button("运行处理", type="primary"):
                        with st.spinner("正在处理..."):
                            try:
                                plugin = plugin_manager.get_plugin_info(selected_algo['plugin'])
                                plugin_module = plugin['module']
                                
                                original_data = data.curves[target_curve]
                                processed_data = plugin_module.run_algorithm(data=original_data, params=params)
                                
                                processed_key = f"{target_curve}_processed"
                                st.session_state.processed_curves[processed_key] = processed_data
                                
                                st.success(f"✅ 处理完成: {selected_algo['name']}")
                            except Exception as e:
                                st.error(f"处理失败: {str(e)}")
                                import traceback
                                st.code(traceback.format_exc())
            else:
                st.info("未找到插件，请在 plugins 目录添加插件")
            
            st.divider()
            
            st.header("数据导出")
            export_format = st.selectbox("选择导出格式", ["CSV", "JSON", "LAS"])
            
            if st.button("导出数据"):
                try:
                    if export_format == "CSV":
                        csv_data = export_to_csv(data)
                        st.download_button(
                            label="下载 CSV 文件",
                            data=csv_data,
                            file_name=f"{data.well_name}.csv",
                            mime="text/csv"
                        )
                    elif export_format == "JSON":
                        json_data = export_to_json(data)
                        st.download_button(
                            label="下载 JSON 文件",
                            data=json_data,
                            file_name=f"{data.well_name}.json",
                            mime="application/json"
                        )
                    elif export_format == "LAS":
                        las_data = export_to_las(data)
                        st.download_button(
                            label="下载 LAS 文件",
                            data=las_data,
                            file_name=f"{data.well_name}.las",
                            mime="text/plain"
                        )
                except Exception as e:
                    st.error(f"导出失败: {str(e)}")
    
    if st.session_state.data is not None:
        data = st.session_state.data
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"井数据: {data.well_name}")
            st.write(f"深度范围: {min(data.depth):.2f} - {max(data.depth):.2f}")
            st.write(f"曲线数量: {len(data.curves)}")
        
        with col2:
            plot_type = st.radio("显示模式", ["单曲线", "多曲线"])
        
        if st.session_state.processed_curves:
            st.info(f"📊 已处理 {len(st.session_state.processed_curves)} 条曲线")
        
        try:
            plotter = WellPlotter(data.depth, data.curves)
            
            selected_curves = st.session_state.get('selected_curves', list(data.curves.keys()))
            
            if selected_curves:
                if plot_type == "单曲线":
                    curve_to_plot = st.selectbox("选择曲线", selected_curves, key="main_curve_select")
                    
                    processed_options = ["无"]
                    processed_key = f"{curve_to_plot}_processed"
                    if processed_key in st.session_state.processed_curves:
                        processed_options.append("显示处理结果")
                    
                    selected_processed = st.selectbox("选择处理结果", processed_options, key="processed_select")
                    
                    processed_curve = None
                    if selected_processed == "显示处理结果":
                        processed_curve = st.session_state.processed_curves[processed_key]
                    
                    fig = plotter.plot_single_curve(curve_to_plot, processed_curve)
                    st.pyplot(fig)
                else:
                    processed_curves_dict = {}
                    for key, value in st.session_state.processed_curves.items():
                        if key.endswith('_processed'):
                            curve_name = key[:-10]
                            if curve_name in selected_curves:
                                processed_curves_dict[curve_name] = value
                    
                    fig = plotter.plot_multiple_curves(selected_curves, processed_curves_dict)
                    st.pyplot(fig)
            else:
                st.info("请在侧边栏选择要显示的曲线")
        except Exception as e:
            st.error(f"绘图失败: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
    else:
        st.info("请先上传测井数据文件 (支持 LAS, FLD, WDT, WIS, TXT 格式)")


if __name__ == "__main__":
    main()
