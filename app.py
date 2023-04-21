import pandas as pd
import streamlit as st
import os
import glob
import datetime

def setup_layout():
    st.set_page_config(
        page_title="DataJoint Import App",
        #page_icon=logo_im_,
        layout="wide",
        # initial_sidebar_state="expanded",
        menu_items={
        }
    )
    hide_streamlit_style = """
                    <style>
                    footer {visibility: hidden;}
                    </style>
                    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    st.set_option('deprecation.showPyplotGlobalUse', False)
    header_container = st.container()

    with header_container:
        st.header("DataJoint Import App")



def main():
    today = datetime.datetime.today().strftime("%Y-%m-%d")
    #start with main layout
    setup_layout()

    file_input_clmn, project_clmn = st.columns([1, 1])

    with file_input_clmn:
        main_container_file = st.container()
        info_box_file = st.container()
        # add data to the database
        pose_origin = main_container_file.selectbox("Select Pose origin", ["SLEAP", "DLC"])
        if pose_origin == "SLEAP":
            info_box_file.info("SLEAP pose files are currently only supported in .h5 format")
        elif pose_origin == "DLC":
            info_box_file.info("DLC pose files are currently only supported in .csv format")

        label_origin = main_container_file.selectbox("Select Label origin", ["BORIS", "A-SOiD"])
        if main_container_file.checkbox("Folder Import"):
            #get directory path
            label_files = main_container_file.text_input("Input directory to pose files")
            pose_files = main_container_file.text_input("Input directory to label files")

            label_files = glob.glob(os.path.join(label_files, "*.csv"))

            if pose_origin == "SLEAP":
                pose_files = glob.glob(os.path.join(pose_files, "*.h5"))
            elif pose_origin == "DLC":
                pose_files = glob.glob(os.path.join(pose_files, "*.csv"))

        else:
            info_box_file.warning("Please upload files in the correct order. Otherwise they will not be associated correctly.")
            label_files = main_container_file.file_uploader("Upload label files", type="csv", accept_multiple_files=True)
            if pose_origin == "SLEAP":
                pose_files = main_container_file.file_uploader("Upload pose files", type="h5", accept_multiple_files=True)
            elif pose_origin == "DLC":
                pose_files = main_container_file.file_uploader("Upload pose files", type="csv", accept_multiple_files=True)

        with project_clmn:
            main_container_project = st.container()
            info_box_project = st.container()
            framerate = main_container_project.number_input("Enter framerate of video", min_value=1, max_value=1000, value=30, step=1)
            experimenter_name = st.text_input("Enter experimenter name", value="TestExperimenter")

            # prepare dataframes for datajoint
            st.subheader("Editable Dataframes")
            st.write("Please edit the dataframes below if necessary. You can add new rows by clicking the + button."
                     "This feature is only available for the mouse dataframe. Make sure to add all details before continuing.")

            st.write("Pose model info:")
            model_dict = {"model_id": [0]
                , "name": ["TestModelName"]
                , "type": ["SingleInstance"]
                , "origin": [pose_origin]
                , "training_date": [today]
                , "description": ["Test entry for model description. Date is fake."]}
            model_info = st.experimental_data_editor(pd.DataFrame(model_dict).set_index(["model_id"]),
                                                     num_rows=1)

            mouse_list = []
            session_list = []
            if label_files is not None:
                for num, f in enumerate(label_files):
                    #fetch mouse and session date
                    filename = f.name
                    filename = os.path.basename(filename).split("_")[0]
                    mouse, session_date = filename.split("-")[0], ("-").join(filename.split("-")[1:])
                    # remove the T
                    mouse = mouse[1:]
                    # add to Mouse table
                    mouse_list.append(mouse)
                    # transform the date into a datetime object
                    session_date = datetime.datetime.strptime(session_date, "%d%m%Y-%H%M%S")
                    # convert to table standard datetime format
                    session_date = session_date.strftime("%Y-%m-%d-%H:%M:%S")
                    session_list.append(session_date)

                df_clmn1, df_clmn2 = st.columns([1, 1])

                with df_clmn1:
                    unique_mice = list(set(mouse_list))


                    df_mice = pd.DataFrame({"mouse_id": unique_mice, "dob": [today]*len(unique_mice)
                                               , "genotype": ["C57BL/6J"]*len(unique_mice)
                                               , "sex": ["M"]*len(unique_mice)})
                    #user can edit the dataframes
                    st.write("Mouse Dataframe")
                    df_mice_ed= st.experimental_data_editor(df_mice, num_rows="dynamic")
                with df_clmn2:
                    exp_dict = {"experimenter_id": 0
                                , "experimenter_name": experimenter_name
                                , "sex": ["unknown"]}
                    #user can edit the dataframes
                    st.write("Experimenter info")
                    df_exp_ed= st.experimental_data_editor(pd.DataFrame(exp_dict).set_index("experimenter_id"), num_rows=1)

                #session dataframe
                st.write("Session Dataframe (autopopulates with imported data)")
                mice_ed = df_mice_ed["mouse_id"].tolist()
                if set(mice_ed) != set(mouse_list):
                    info_box_project.error("Please make sure that all mice in the session dataframe are also in the mouse dataframe")

                df_session = pd.DataFrame({"mouse_id": mouse_list, "session_time": session_list

                                            ,"video_path": [None]*len(mouse_list)
                                            ,"video_fps": [framerate] * len(mouse_list)
                                            ,"pose_path": [f.name for f in pose_files] if pose_files else [None]*len(mouse_list)
                                            , "pose_origin": [pose_origin] * len(mouse_list)
                                            ,"annotation_path": [f.name for f in label_files] if label_files else [None]*len(mouse_list)
                                            ,"annotation_origin": [label_origin]*len(mouse_list)

                                           })

                df_session_ed = st.experimental_data_editor(df_session)

    #add button to insert dataframes into datajoint
    if st.button("Insert data into datajoint"):
        st.balloons()
        st.success("You reached the end of the demo. To be continued...")

    #add footer
    with st.container() as bottom_cont:
        IMPRESS_TEXT = "This is a test app to import data into datajoint pipelines using streamlit. Developed by JensBlack"
        st.markdown("""---""")
        st.write('')
        st.write('')
        st.markdown('<span style="color:grey">{}</span>'.format(IMPRESS_TEXT), unsafe_allow_html=True)


if __name__ == '__main__':
    main()