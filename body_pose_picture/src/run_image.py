import os
import cv2
import argparse
from utils.model_processor import ModelProcessor

PROJECT_PATH = r"C:\Users\Vika.VITUHA\Desktop\edge\EDGE_AI_2025_REPO-vituha\body_pose_picture"

MODEL_PATH = os.path.join(PROJECT_PATH, "model", "pose_heatmap.onnx")
print("MODEL_PATH:", MODEL_PATH)
DATA_PATH = os.path.join(PROJECT_PATH, "data", "test.jpg")
print("MODEL_PATH:", DATA_PATH)
Output_PATH = os.path.join(PROJECT_PATH, "output")
print("MODEL_PATH:", Output_PATH)


def main(model_path, frames_input_src, output_dir):
    """main"""

    ## Prepare Model ##
    # parameters for model path and model inputs
    model_parameters = {
        'model_dir': model_path,
        'width': 368, # model input width
        'height': 368, # model input height
    }
    # perpare model instance: init (loading model from file to memory)
    # model_processor: preprocessing + model inference + postprocessing
    model_processor = ModelProcessor(model_parameters)

    ## Get Input ##
    # Read the image input using OpenCV
    img_original = cv2.imread(frames_input_src)
    if img_original is None:
        print("Cannot read input file")
    ## Model Prediction ##
    # model_processor.predict: processing + model inference + postprocessing
    # canvas: the picture overlayed with human body joints and limbs
    canvas = model_processor.predict(img_original)

    # Save the detected results
    # cv2.imwrite(os.path.join(output_dir, "test_output.jpg"), canvas)
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "test_output.jpg")
    print("Saving to: ", out_path)

    ok = cv2.imwrite(out_path, canvas)
    print("cv2.imwrite returned: ", ok)


if __name__ == '__main__':
    description = 'Load a model for human pose estimation'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--model', type=str, default=MODEL_PATH)
    parser.add_argument('--frames_input_src', type=str, default=DATA_PATH, help="Directory path for image")
    parser.add_argument('--output_dir', type=str, default=Output_PATH, help="Output Path")

    args = parser.parse_args()
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    main(args.model, args.frames_input_src, args.output_dir)

