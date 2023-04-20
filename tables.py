
import datajoint as dj
import numpy as np
import pandas as pd

from utils.load_data import import_labels_to_table, load_pose, get_bodyparts


dj.config['database.host'] = '127.0.0.1'
dj.config['database.user'] = 'root'
dj.config['database.password'] = 'simple'
dj.conn()
# fail-safe user name retrieval
username = dj.conn().conn_info['user']
schema = dj.schema('{}_pipeline'.format(username))


"""Manual entry tables"""

@schema
class Mouse(dj.Manual):
    definition = """
    # Experimental animals
    mouse_id             : int                          # Unique animal ID
    ---
    dob=null             : date                         # date of birth
    sex="unknown"        : enum('M','F','unknown')      # sex
    genotype             : varchar(255)                 # genotype of animal #TODO: should be restricted to Lookup table
    """


@schema
class Session(dj.Manual):
    definition = """
    #Session
    -> Mouse
    session_id           : int                         # id of experiment
    ---
    session_time         : datetime                       # time of experiment #todo: change to datetime
    experimenter_id      : int              # id of experimenter, linking to experimenter table
    video_path           : varchar(255)                 # path to video file
    video_fps            : int                          # fps of recorded video file
    pose_path            : varchar(255)                 # path to pose file
    pose_model_id        : int                          # unique id linking pose file to model
    annotation_path      : varchar(255)                 # path to annotation file
    annotation_origin    : varchar(255)        # origin of annotation files (e.g. BORIS)
    """

@schema
class Experimenter(dj.Lookup):
        definition = """
    # Experimenter
    experimenter_id      : int                          # Unique experimenter ID
    ---
    name=null            : varchar(255)                 # name of experimenter
    sex="unknown"        : enum('M','F','unknown')      # sex
    """

"""Lookup tables"""

@schema
class Model(dj.Lookup):
            definition = """
    # Model info
    model_id      : int                        # Unique model ID
    ---
    name           : varchar(255)              # name of model
    type           : varchar(255)              # model architecture
    origin         : varchar(255)              # origin of model (e.g. SLEAP)
    training_date  : date                      # date the model was trained
    description    : varchar(255)              # description of the model (optional)
    """


"""Imported tables"""

@schema
class Annotation(dj.Imported):
    definition = """
    -> Session
    -> Experimenter
    ---
    annotations = null       : longblob                # behavior file
    unique_labels = null      : varchar(255)            # unique behavior labels seperated by comma
    """

    class Stats(dj.Part):
        definition = """
        -> master
        behavior_id : varchar(255) #unique behavior id
        ---
        total_frames : int # total number of frames per behavior
        total_perc: float # perc. compared to total length of session
        total_time: float # total time in seconds  
        
        """
    def make(self, key):
        behavior_file = (Session & key).fetch1("annotation_path")
        annotation_origin = (Session & key).fetch1("annotation_origin")
        fps = (Session & key).fetch1("video_fps")

        annotations, unique_labels = import_labels_to_table(behavior_file, annotation_origin, fps)

        #translate list of str into str joined by ","
        unique_labels_str = ", ".join(unique_labels)
        self.insert1(dict(key, annotations= annotations.values, unique_labels= unique_labels_str))

        """Calculate some statistics"""

        fps = (Session & key).fetch1("video_fps")

        desc_df = pd.DataFrame(annotations.value_counts(), columns=["total_frames"])
        desc_df["total_perc"] = desc_df[desc_df.columns[0]] / annotations.shape[0]
        desc_df["total_time"] = desc_df[desc_df.columns[0]] / fps

        # convert to dict so it can be directly inserted
        insert_dict = desc_df.to_dict("index")

        for behavior_key, stats in insert_dict.items():
            self.Stats.insert1(dict(key, behavior_id = behavior_key
                               , **stats))

@schema
class Pose(dj.Imported):
    definition = """
    -> Session
    -> Experimenter
    -> Model
    ---
    keypoints          : varchar(255)            # keypoints seperated by comma
    pose               : longblob                # pose file as numpy array in style x,y,score per bodypart
    """
    def make(self, key):
        pose_file, model_id = (Session & key).fetch1("pose_path", "pose_model_id")
        pose_origin = (Model & f"model_id = {model_id}").fetch1("origin")


        pose = load_pose(pose_file, pose_origin)
        keypoints= get_bodyparts(pose)

        #translate list of str into str joined by ","
        keypoints_str = ", ".join(keypoints)

        self.insert1(dict(key, pose=pose.values, keypoints = keypoints_str))



# add dummy entry to lookup tables
Experimenter.insert1((0, "JensBlack", "M"), skip_duplicates = True)
Model.insert1((0, "TestModelName", "SingleInstance","SLEAP", "2022-10-20", "Test entry for model description. Date is fake."), skip_duplicates = True)




