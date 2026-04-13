import json
import csv
import time
from datetime import datetime, timedelta
from collections import Counter
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import altair as alt


def render(t):
    st.subheader(t["analysis_title"])
    st.caption(t["analysis_yolo_caption"])

    log_path = "/home/amr/Desktop/robot_code/ui_status/yolo_full_log.json"

    try:
        with open(log_path, "r") as f:
            data = json.load(f)

        save_time_str = None
        for entry in reversed(data):
            if "save_time" in entry:
                save_time_str = entry["save_time"]
                break

        if save_time_str:
            from datetime import datetime, timedelta

            save_time = datetime.strptime(save_time_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            diff = now - save_time

            if diff > timedelta(minutes=10):
                st.warning(t["analysis_yolo_time_expired"].format(time=save_time_str))
            else:
                all_objects = []
                for entry in data:
                    if "yolo_detection_result" in entry:
                        for obj in entry["yolo_detection_result"]:
                            obj_name = obj.get("object")
                            if obj_name:
                                all_objects.append(obj_name)

                count = Counter(all_objects)
                df = pd.DataFrame({
                    "object": list(count.keys()),
                    "count": list(count.values())
                })

                color_chart = alt.Chart(df).mark_bar().encode(
                    x=alt.X("object:N", sort='-y'),
                    y="count:Q",
                    color="object:N",
                    tooltip=["object", "count"]
                ).properties(
                    width=600,
                    height=500,
                )

                st.altair_chart(color_chart, use_container_width=True)
        else:
            st.warning(t["analysis_yolo_no_time"])

    except Exception as e:
        st.error(t["analysis_yolo_error"].format(error=str(e)))

    st.caption(t["analysis_path_caption"])
    csv_path = "/home/amr/Desktop/robot_code/picture_record/path_data_for_streamlit.csv"
    show_path_chart = True

    try:
        if not os.path.exists(csv_path):
            st.warning(t["analysis_path_no_csv"])
        else:
            df = pd.read_csv(csv_path)
        
            if len(df) > 0 and df.iloc[-1]['Real_X'] == "GeneratedTime":
                try:
                    from datetime import datetime, timedelta
                    last_save_time = df.iloc[-1]['Real_Y']
                    save_time = datetime.strptime(str(last_save_time), "%Y-%m-%d %H:%M:%S")
                    now = datetime.now()
                    time_diff = now - save_time

                    if time_diff > timedelta(minutes=10):
                        st.warning(t["analysis_path_time_expired"].format(time=last_save_time))
                        # st.stop()
                        show_path_chart = False
                
                    df = df.iloc[:-1]

                except Exception as e:
                    st.warning(f"⚠️ Time format error, skipping time comparison: {e}")
            
            if show_path_chart:

                path_df = df
            
                real_data = path_df[['Real_X', 'Real_Y']].dropna()
                plan_data = path_df[['Plan_X', 'Plan_Y']].dropna()
            
                if not plan_data.empty and 'start_pose' in st.session_state and st.session_state.start_pose:
                    start_x = st.session_state.start_pose['x']
                    start_y = st.session_state.start_pose['y']
                
                    start_point = pd.DataFrame({'Plan_X': [start_x], 'Plan_Y': [start_y]})
                    plan_data = pd.concat([start_point, plan_data], ignore_index=True)
            
                if real_data.empty and plan_data.empty:
                    st.warning(t["analysis_path_empty"])
                else:
                    fig = go.Figure()
                    if not real_data.empty:
                        fig.add_trace(go.Scatter(
                            x=real_data['Real_X'],
                            y=real_data['Real_Y'],
                            mode='lines+markers',
                            line=dict(color='green'),
                            marker=dict(symbol='circle', size=6),
                            name='Real Route'
                        ))
                    if not plan_data.empty:
                        fig.add_trace(go.Scatter(
                            x=plan_data['Plan_X'],
                            y=plan_data['Plan_Y'],
                            mode='lines+markers',
                            line=dict(color='#FFA500', dash='dash'),
                            marker=dict(symbol='x', size=8),
                            name='Plan Route'
                        ))
                    fig.update_layout(
                        title='Robot Navigation Path',
                        xaxis_title='X',
                        yaxis_title='Y',
                        showlegend=True,
                        xaxis=dict(showgrid=True),
                        yaxis=dict(showgrid=True, scaleanchor="x", scaleratio=1),
                        width=800,
                        height=600
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
    except Exception as e:
        st.error(t["analysis_time_error"].format(error=str(e)))

    st.caption(t["analysis_object_caption"])
    try:
        with open(log_path, "r") as f:
            data = json.load(f)

        save_time_str = None
        for entry in reversed(data):
            if "save_time" in entry:
                save_time_str = entry["save_time"]
                break

        if save_time_str:
            from datetime import datetime, timedelta
            save_time = datetime.strptime(save_time_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            diff = now - save_time

            if diff > timedelta(minutes=10):
                st.warning(t["analysis_object_time_expired"].format(time=save_time_str))
            else:

                records = []
                for entry in data:
                    if "yolo_detection_result" in entry:
                        for obj in entry["yolo_detection_result"]:
                            if "x" in obj and "y" in obj:
                                records.append({
                                    "object": obj["object"],
                                    "x": obj["x"],
                                    "y": obj["y"],
                                    "confidence": obj.get("confidence", 0.5)
                                })

                df = pd.DataFrame(records)
            
                if df.empty:
                    st.warning(t["analysis_object_no_data"])
                else:
                    df["original_confidence"] = df["confidence"] 
                    df["confidence_normalized"] = df["original_confidence"].clip(0.01, 1.0)
                    conf_min = df["confidence_normalized"].min()
                    conf_max = df["confidence_normalized"].max()
                
                    if conf_max != conf_min:
                        df["confidence_normalized"] = (df["confidence_normalized"] - conf_min) / (conf_max - conf_min) ** 10
                    else:
                        df["confidence_normalized"] = 1.0
                
                    df["size_for_plot"] = df["confidence_normalized"] * 150
                    fig = px.scatter(
                        df,
                        x="x",
                        y="y",
                        color="object",
                        size="size_for_plot",
                        hover_data=["object", "x", "y", "original_confidence"],  
                        size_max=15,
                        opacity=0.6,
                        title=t["analysis_object_title"]
                    )
                    fig.update_layout(
                        yaxis=dict(scaleanchor="x", scaleratio=1),  
                        width=800,
                        height=600
                    )
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(t["analysis_yolo_no_time"])

    except Exception as e:
        st.error(t["analysis_yolo_error"].format(error=str(e)))

