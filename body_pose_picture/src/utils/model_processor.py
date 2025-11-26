import os
import cv2
import numpy as np
import onnxruntime as ort
from utils.pose_decode import decode_pose

heatmap_width = 92
heatmap_height = 92


class ModelProcessor(object):
    """CPU model wrapper"""
    def __init__(self, params):
        self.params = params
        self._model_width = params['width']
        self._model_height = params['height']

        assert 'model_dir' in params and params['model_dir'] is not None, 'Review your param: model_dir'
        assert os.path.exists(params['model_dir']), "Model directory doesn't exist {}".format(params['model_dir'])

        self.session = ort.InferenceSession(params['model_dir'])

        self.input_name = self.session.get_inputs()[0].name

        self.output_names = [o.name for o in self.session.get_outputs()]


    def preprocess(self, img_original):
        scaled_img_data = cv2.resize(img_original, (self._model_width, self._model_height))
        preprocessed_img = np.asarray(scaled_img_data, dtype=np.float32) / 255.
        preprocessed_img = np.expand_dims(preprocessed_img, axis=0)
        
        return preprocessed_img
    

    def predict(self, img_original):
        """run predict"""
        model_input = self.preprocess(img_original)
        outputs = self.session.run(self.output_names, {self.input_name: model_input})
        result = outputs[0]

        print("result shape = ", result.shape)

        # heatmaps = result[0]
        heatmaps = np.transpose(result[0], (2, 0, 1))
        # calculate the scale of original image over heatmap, Note: image_original.shape[0] is height
        scale = np.array([img_original.shape[1] / heatmap_width, img_original.shape[0]/ heatmap_height])

        canvas = decode_pose(heatmaps, scale, img_original)

        return canvas
    
    

    
